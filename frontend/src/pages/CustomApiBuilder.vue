<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useToastStore } from "../stores/toast";
import {
  listEndpoints,
  createEndpoint,
  updateEndpoint,
  deleteEndpoint,
  previewEndpoint,
  testEndpoint,
  regenerateKey,
  type CustomEndpoint,
  type EndpointCreate,
  type EndpointUpdate,
} from "../lib/custom-api";
import UModal from "../components/ui/UModal.vue";
import UButton from "../components/ui/UButton.vue";
import UBadge from "../components/ui/UBadge.vue";
import UEmpty from "../components/ui/UEmpty.vue";
import UCard from "../components/ui/UCard.vue";
import UToggle from "../components/ui/UToggle.vue";
import UInput from "../components/ui/UInput.vue";
import UInfoTooltip from "../components/ui/UInfoTooltip.vue";
import UEntitySelect from "../components/ui/UEntitySelect.vue";

const { t, tm, rt } = useI18n();
const toast = useToastStore();

// ── State ────────────────────────────────────────────────────────────────────
const endpoints = ref<CustomEndpoint[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const viewMode = ref<"cards" | "table">("cards");

// ── Detail panel ─────────────────────────────────────────────────────────────
const detailEndpoint = ref<CustomEndpoint | null>(null);
const detailOpen = ref(false);
const detailTesting = ref(false);
const detailTestResult = ref<string | null>(null);
const detailKeyRegenLoading = ref(false);
const codeTab = ref<"curl" | "python" | "javascript">("curl");

// ── Create/Edit modal ────────────────────────────────────────────────────────
const modalOpen = ref(false);
const modalMode = ref<"create" | "edit">("create");
const modalStep = ref(1);
const saving = ref(false);

// Step 1 — Basics
const formName = ref("");
const formPath = ref("");
const formMethod = ref<"GET" | "POST">("GET");
const formDescription = ref("");

// Step 2 — Data Source (GET)
const formSourceType = ref<"variables" | "devices" | "entities" | "alerts" | "events" | "status_snapshot">("variables");
const formVariableKeys = ref("");
const formDeviceFilter = ref("");
const formAggregation = ref<"none" | "avg" | "min" | "max" | "sum">("none");
const formTimeRange = ref<"raw" | "1h" | "24h" | "7d" | "30d">("raw");
const formGroupBy = ref<"none" | "hour" | "day" | "month">("none");
const formFormat = ref<"json" | "csv">("json");

// Step 2 — Data Source (POST)
const formWriteEnabled = ref(false);
const formTargetType = ref("set_variable");
const formAllowedKeys = ref("");
const formDeviceScope = ref("");

// Step 3 — Security
const formAuthType = ref<"api_key" | "bearer" | "none">("api_key");
const formRateLimit = ref(100);

// Step 4 — Preview
const previewData = ref<string | null>(null);
const previewLoading = ref(false);
const editId = ref<number | null>(null);

// ── Path validation ─────────────────────────────────────────────────────────
const PATH_CHARS_RE = /^[a-zA-Z0-9\-_/\.]+$/;

const pathError = computed((): string | null => {
  const raw = formPath.value.trim();
  if (!raw) return null; // empty is handled by canProceedStep1
  // Prepend / if user didn't type it
  const p = raw.startsWith("/") ? raw : "/" + raw;
  if (p.length < 2) return t("customApi.pathErrors.tooShort");
  if (p.length > 200) return t("customApi.pathErrors.tooLong");
  if (p.endsWith("/") && p.length > 1) return t("customApi.pathErrors.trailingSlash");
  if (p.includes("//")) return t("customApi.pathErrors.doubleSlash");
  if (p.includes("..")) return t("customApi.pathErrors.traversal");
  const body = p.slice(1);
  if (body && !PATH_CHARS_RE.test(body)) return t("customApi.pathErrors.invalidChars");
  return null;
});

// ── Category helpers ────────────────────────────────────────────────────────
function getCategory(path: string): string {
  // /api1/temperature → "api1", /test → "(root)"
  const clean = path.startsWith("/") ? path.slice(1) : path;
  const slashIdx = clean.indexOf("/");
  if (slashIdx === -1) return "(root)";
  return clean.substring(0, slashIdx);
}

const categoryFilter = ref<string>("__all__");

const availableCategories = computed(() => {
  const cats = new Set<string>();
  for (const ep of endpoints.value) {
    cats.add(getCategory(ep.path));
  }
  return Array.from(cats).sort();
});

const filteredEndpoints = computed(() => {
  if (categoryFilter.value === "__all__") return endpoints.value;
  return endpoints.value.filter(ep => getCategory(ep.path) === categoryFilter.value);
});

const groupedEndpoints = computed(() => {
  const groups: Record<string, typeof endpoints.value> = {};
  for (const ep of filteredEndpoints.value) {
    const cat = getCategory(ep.path);
    if (!groups[cat]) groups[cat] = [];
    groups[cat].push(ep);
  }
  // Sort group keys
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b));
});

// ── Computed ─────────────────────────────────────────────────────────────────
const totalSteps = computed(() => 4);

const pathPrefix = "/api/v1/custom-api/call/";
const fullPath = computed(() => pathPrefix + formPath.value);

const canProceedStep1 = computed(() => formName.value.trim() && formPath.value.trim() && !pathError.value);

const sourceConfig = computed(() => {
  if (formMethod.value === "GET") {
    return {
      type: formSourceType.value,
      variable_keys: formVariableKeys.value ? formVariableKeys.value.split(",").map(s => s.trim()).filter(Boolean) : [],
      device_filter: formDeviceFilter.value || null,
      aggregation: formAggregation.value !== "none" ? formAggregation.value : null,
      time_range: formTimeRange.value !== "raw" ? formTimeRange.value : null,
      group_by: formGroupBy.value !== "none" ? formGroupBy.value : null,
      format: formFormat.value,
    };
  }
  return {
    type: "set_variable",
    allowed_variable_keys: formAllowedKeys.value ? formAllowedKeys.value.split(",").map(s => s.trim()).filter(Boolean) : [],
    device_uid: formDeviceScope.value || null,
  };
});

// ── Load ─────────────────────────────────────────────────────────────────────
async function load() {
  loading.value = true;
  error.value = null;
  try {
    endpoints.value = await listEndpoints();
  } catch (e: unknown) {
    // Distinguish real errors from empty state: if the API returns 404
    // because the table doesn't exist yet, treat as empty list
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.includes("404") || msg.includes("Not Found")) {
      endpoints.value = [];
    } else {
      error.value = t("customApi.loadError");
    }
  } finally {
    loading.value = false;
  }
}

// ── Create/Edit ──────────────────────────────────────────────────────────────
function openCreate() {
  modalMode.value = "create";
  editId.value = null;
  modalStep.value = 1;
  formName.value = "";
  formPath.value = "";
  formMethod.value = "GET";
  formDescription.value = "";
  formSourceType.value = "variables";
  formVariableKeys.value = "";
  formDeviceFilter.value = "";
  formAggregation.value = "none";
  formTimeRange.value = "raw";
  formGroupBy.value = "none";
  formFormat.value = "json";
  formWriteEnabled.value = false;
  formTargetType.value = "set_variable";
  formAllowedKeys.value = "";
  formDeviceScope.value = "";
  formAuthType.value = "api_key";
  formRateLimit.value = 100;
  previewData.value = null;
  modalOpen.value = true;
}

function openEdit(ep: CustomEndpoint) {
  modalMode.value = "edit";
  editId.value = ep.id;
  modalStep.value = 1;
  formName.value = ep.name;
  formPath.value = ep.path;
  formMethod.value = ep.method;
  formDescription.value = ep.description || "";

  const cfg = ep.source_config || {};
  if (ep.method === "GET") {
    formSourceType.value = (cfg.type as string || "variables") as typeof formSourceType.value;
    formVariableKeys.value = Array.isArray(cfg.variable_keys) ? (cfg.variable_keys as string[]).join(", ") : "";
    formDeviceFilter.value = (cfg.device_filter as string) || "";
    formAggregation.value = (cfg.aggregation as string || "none") as typeof formAggregation.value;
    formTimeRange.value = (cfg.time_range as string || "raw") as typeof formTimeRange.value;
    formGroupBy.value = (cfg.group_by as string || "none") as typeof formGroupBy.value;
    formFormat.value = (cfg.format as string || "json") as typeof formFormat.value;
  } else {
    formWriteEnabled.value = ep.write_enabled;
    formTargetType.value = (cfg.type as string) || "set_variable";
    formAllowedKeys.value = Array.isArray(cfg.allowed_variable_keys) ? (cfg.allowed_variable_keys as string[]).join(", ") : "";
    formDeviceScope.value = (cfg.device_uid as string) || "";
  }

  formAuthType.value = ep.auth_type;
  formRateLimit.value = ep.rate_limit;
  previewData.value = null;
  modalOpen.value = true;
}

async function handleSave() {
  saving.value = true;
  try {
    if (modalMode.value === "create") {
      let path = formPath.value.trim();
      if (!path.startsWith("/")) path = "/" + path;
      const data: EndpointCreate = {
        name: formName.value.trim(),
        path,
        method: formMethod.value,
        description: formDescription.value || null,
        source_config: sourceConfig.value,
        auth_type: formAuthType.value,
        rate_limit: formRateLimit.value,
        write_enabled: formMethod.value === "POST" ? formWriteEnabled.value : false,
      };
      await createEndpoint(data);
      toast.addToast(t("toast.created", { item: "Endpoint" }), "success");
    } else if (editId.value) {
      const data: EndpointUpdate = {
        name: formName.value.trim(),
        description: formDescription.value || null,
        source_config: sourceConfig.value,
        auth_type: formAuthType.value,
        rate_limit: formRateLimit.value,
        write_enabled: formMethod.value === "POST" ? formWriteEnabled.value : false,
      };
      await updateEndpoint(editId.value, data);
      toast.addToast(t("toast.updated", { item: "Endpoint" }), "success");
    }
    modalOpen.value = false;
    await load();
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : t("customApi.saveFailed"), "error");
  } finally {
    saving.value = false;
  }
}

// ── Delete ───────────────────────────────────────────────────────────────────
async function handleDelete(id: number) {
  if (!confirm(t("customApi.deleteConfirm"))) return;
  try {
    await deleteEndpoint(id);
    toast.addToast(t("toast.deleted", { item: "Endpoint" }), "success");
    if (detailEndpoint.value?.id === id) {
      detailOpen.value = false;
      detailEndpoint.value = null;
    }
    await load();
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : t("customApi.deleteFailed"), "error");
  }
}

// ── Toggle enable ────────────────────────────────────────────────────────────
async function toggleEnabled(ep: CustomEndpoint) {
  try {
    await updateEndpoint(ep.id, { enabled: !ep.enabled });
    ep.enabled = !ep.enabled;
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : t("customApi.toggleFailed"), "error");
  }
}

// ── Detail panel ─────────────────────────────────────────────────────────────
function openDetail(ep: CustomEndpoint) {
  detailEndpoint.value = ep;
  detailOpen.value = true;
  detailTestResult.value = null;
  codeTab.value = "curl";
}

async function handleTest() {
  if (!detailEndpoint.value) return;
  detailTesting.value = true;
  detailTestResult.value = null;
  try {
    const result = await testEndpoint(detailEndpoint.value.id);
    detailTestResult.value = JSON.stringify(result, null, 2);
  } catch (err: unknown) {
    detailTestResult.value = `Error: ${err instanceof Error ? err.message : "Test failed"}`;
  } finally {
    detailTesting.value = false;
  }
}

async function handleRegenKey() {
  if (!detailEndpoint.value) return;
  detailKeyRegenLoading.value = true;
  try {
    const res = await regenerateKey(detailEndpoint.value.id);
    detailEndpoint.value.api_key = res.api_key;
    toast.addToast(t("customApi.keyRegenerated"), "success");
  } catch {
    toast.addToast(t("customApi.keyRegenFailed"), "error");
  } finally {
    detailKeyRegenLoading.value = false;
  }
}

// ── Preview (step 4) ─────────────────────────────────────────────────────────
async function loadPreview() {
  if (!editId.value) {
    previewData.value = JSON.stringify({ info: t("customApi.previewAfterSave") }, null, 2);
    return;
  }
  previewLoading.value = true;
  try {
    const data = await previewEndpoint(editId.value);
    previewData.value = JSON.stringify(data, null, 2);
  } catch {
    previewData.value = JSON.stringify({ error: t("customApi.previewFailed") }, null, 2);
  } finally {
    previewLoading.value = false;
  }
}

watch(modalStep, (step) => {
  if (step === 4) loadPreview();
});

// ── Helpers ──────────────────────────────────────────────────────────────────
function relativeTime(ts: string | null): string {
  if (!ts) return t("customApi.neverCalled");
  const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function getEndpointUrl(ep: CustomEndpoint): string {
  return `${window.location.origin}/api/v1/custom-api/call/${ep.path}`;
}

function getCurlExample(ep: CustomEndpoint): string {
  const url = getEndpointUrl(ep);
  const authHeader = ep.auth_type === "api_key"
    ? ` \\\n  -H "X-API-Key: ${ep.api_key || "<YOUR_API_KEY>"}"`
    : ep.auth_type === "bearer"
    ? ` \\\n  -H "Authorization: Bearer ${ep.api_key || "<YOUR_TOKEN>"}"`
    : "";
  if (ep.method === "POST") {
    return `curl -X POST "${url}"${authHeader} \\\n  -H "Content-Type: application/json" \\\n  -d '{"key": "temperature", "value": 22.5}'`;
  }
  return `curl "${url}"${authHeader}`;
}

function getPythonExample(ep: CustomEndpoint): string {
  const url = getEndpointUrl(ep);
  const headers = ep.auth_type === "api_key"
    ? `\n    "X-API-Key": "${ep.api_key || "<YOUR_API_KEY>"}",`
    : ep.auth_type === "bearer"
    ? `\n    "Authorization": "Bearer ${ep.api_key || "<YOUR_TOKEN>"}",`
    : "";
  if (ep.method === "POST") {
    return `import requests\n\nresponse = requests.post(\n    "${url}",\n    headers={${headers}\n        "Content-Type": "application/json",\n    },\n    json={"key": "temperature", "value": 22.5}\n)\nprint(response.json())`;
  }
  return `import requests\n\nresponse = requests.get(\n    "${url}",\n    headers={${headers}}\n)\nprint(response.json())`;
}

function getJsExample(ep: CustomEndpoint): string {
  const url = getEndpointUrl(ep);
  const headers = ep.auth_type === "api_key"
    ? `\n      "X-API-Key": "${ep.api_key || "<YOUR_API_KEY>"}",`
    : ep.auth_type === "bearer"
    ? `\n      "Authorization": "Bearer ${ep.api_key || "<YOUR_TOKEN>"}",`
    : "";
  if (ep.method === "POST") {
    return `const response = await fetch("${url}", {\n  method: "POST",\n  headers: {${headers}\n    "Content-Type": "application/json",\n  },\n  body: JSON.stringify({ key: "temperature", value: 22.5 }),\n});\nconst data = await response.json();\nconsole.log(data);`;
  }
  return `const response = await fetch("${url}", {\n  headers: {${headers}}\n});\nconst data = await response.json();\nconsole.log(data);`;
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text);
  toast.addToast(t("customApi.copied"), "success");
}

function getAuthLabel(type: string): string {
  if (type === "api_key") return t("customApi.authApiKey");
  if (type === "bearer") return t("customApi.authBearer");
  return t("customApi.noAuth");
}

onMounted(load);
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-start justify-between gap-4">
      <div>
        <div class="flex items-center">
          <h1 class="text-xl font-semibold text-[var(--text-primary)]">{{ t('customApi.title') }}</h1>
          <UInfoTooltip :title="t('customApi.infoTitle')" :items="tm('customApi.infoItems').map((i: any) => rt(i))" />
        </div>
        <p class="text-xs text-[var(--text-muted)] mt-0.5">
          {{ t('customApi.subtitle') }}
          <router-link to="/developer" class="text-[var(--primary)] hover:underline ml-1">{{ t('customApi.apiDocsLink') }}</router-link> ·
          <router-link to="/variables" class="text-[var(--primary)] hover:underline">{{ t('customApi.variablesLink') }}</router-link>
        </p>
      </div>
      <div class="flex gap-2">
        <UButton size="sm" variant="secondary" @click="load">{{ t('common.refresh') }}</UButton>
        <UButton size="sm" @click="openCreate">+ {{ t('customApi.newEndpoint') }}</UButton>
      </div>
    </div>

    <!-- View toggle + Category filter -->
    <div v-if="endpoints.length" class="flex items-center gap-4 flex-wrap">
      <div class="flex gap-1 p-0.5 rounded-lg bg-[var(--bg-raised)] w-fit">
        <button
          :class="['px-2.5 py-1 text-xs rounded-md transition-colors', viewMode === 'cards' ? 'bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-sm' : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]']"
          @click="viewMode = 'cards'"
        >{{ t('customApi.cardView') }}</button>
        <button
          :class="['px-2.5 py-1 text-xs rounded-md transition-colors', viewMode === 'table' ? 'bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-sm' : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]']"
          @click="viewMode = 'table'"
        >{{ t('customApi.tableView') }}</button>
      </div>
      <div v-if="availableCategories.length > 1" class="flex items-center gap-2">
        <label class="text-[10px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ t('customApi.categoryLabel') }}</label>
        <select v-model="categoryFilter" class="input text-xs py-1 px-2 min-w-[120px]">
          <option value="__all__">{{ t('customApi.allCategories') }}</option>
          <option v-for="cat in availableCategories" :key="cat" :value="cat">
            {{ cat === '(root)' ? t('customApi.rootCategory') : cat }}
            ({{ endpoints.filter(ep => getCategory(ep.path) === cat).length }})
          </option>
        </select>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="h-20 rounded-xl bg-[var(--bg-surface)] animate-pulse" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-400">
      <p>{{ error }}</p>
      <UButton size="sm" variant="secondary" class="mt-2" @click="load">{{ t('common.refresh') }}</UButton>
    </div>

    <!-- Empty -->
    <UEmpty v-else-if="!endpoints.length"
      :title="t('customApi.emptyTitle')"
      :description="t('customApi.emptyDesc')"
      icon="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5"
    >
      <UButton size="sm" @click="openCreate">{{ t('customApi.createEndpoint') }}</UButton>
    </UEmpty>

    <!-- Card view (grouped by category) -->
    <div v-else-if="viewMode === 'cards'" class="space-y-6">
      <div v-for="[category, eps] in groupedEndpoints" :key="category">
        <!-- Category header -->
        <div class="flex items-center gap-2 mb-3">
          <svg class="h-4 w-4 text-[var(--text-muted)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" /></svg>
          <span class="text-xs font-semibold text-[var(--text-primary)]">{{ category === '(root)' ? t('customApi.rootCategory') : category }}</span>
          <span class="text-[10px] text-[var(--text-muted)]">{{ t('customApi.endpointCount', { count: eps.length }, eps.length) }}</span>
        </div>
        <!-- Endpoint cards in this category -->
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <div
            v-for="ep in eps"
            :key="ep.id"
            class="border border-[var(--border)] rounded-xl bg-[var(--bg-surface)] px-5 py-4 cursor-pointer transition-all hover:border-[var(--border-hover)] hover:shadow-[var(--shadow-glow-primary)]"
            @click="openDetail(ep)"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                  <span
                    class="text-[10px] px-1.5 py-0.5 rounded font-mono font-bold"
                    :class="ep.method === 'GET' ? 'bg-green-500/20 text-green-400' : 'bg-amber-500/20 text-amber-400'"
                  >{{ ep.method }}</span>
                  <span class="text-sm font-medium text-[var(--text-primary)] truncate">{{ ep.name }}</span>
                </div>
                <p class="text-xs font-mono text-[var(--text-secondary)] truncate">/api/v1/custom-api/call/{{ ep.path }}</p>
                <p v-if="ep.description" class="text-[10px] text-[var(--text-muted)] mt-1 line-clamp-2">{{ ep.description }}</p>
              </div>
              <div class="flex flex-col items-end gap-1.5 shrink-0" @click.stop>
                <UBadge :status="ep.enabled ? 'ok' : 'neutral'" size="sm">
                  {{ ep.enabled ? t('status.enabled') : t('status.disabled') }}
                </UBadge>
                <UBadge status="info" size="sm">{{ getAuthLabel(ep.auth_type) }}</UBadge>
              </div>
            </div>
            <div class="flex items-center justify-between mt-3 pt-2 border-t border-[var(--border)]">
              <div class="flex items-center gap-4 text-[10px] text-[var(--text-muted)]">
                <span>{{ ep.request_count }} {{ t('customApi.requests') }}</span>
                <span>{{ ep.rate_limit }} {{ t('customApi.reqPerHour') }}</span>
              </div>
              <span class="text-[10px] text-[var(--text-muted)]">{{ relativeTime(ep.last_called_at) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Table view -->
    <div v-else class="border border-[var(--border)] rounded-xl bg-[var(--bg-surface)] overflow-hidden">
      <table class="w-full text-xs">
        <thead>
          <tr class="border-b border-[var(--border)] bg-[var(--bg-raised)]">
            <th class="text-left px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">{{ t('customApi.colMethod') }}</th>
            <th class="text-left px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">{{ t('customApi.colPath') }}</th>
            <th class="text-left px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">{{ t('customApi.colCategory') }}</th>
            <th class="text-left px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">{{ t('customApi.colSource') }}</th>
            <th class="text-left px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">{{ t('customApi.colAuth') }}</th>
            <th class="text-left px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">{{ t('customApi.colRateLimit') }}</th>
            <th class="text-left px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">{{ t('common.status') }}</th>
            <th class="text-right px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">{{ t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="ep in filteredEndpoints"
            :key="ep.id"
            class="border-b border-[var(--border)] last:border-b-0 hover:bg-[var(--bg-raised)] cursor-pointer transition-colors"
            @click="openDetail(ep)"
          >
            <td class="px-4 py-2.5">
              <span
                class="text-[10px] px-1.5 py-0.5 rounded font-mono font-bold"
                :class="ep.method === 'GET' ? 'bg-green-500/20 text-green-400' : 'bg-amber-500/20 text-amber-400'"
              >{{ ep.method }}</span>
            </td>
            <td class="px-4 py-2.5 font-mono text-[var(--text-secondary)]">/{{ ep.path }}</td>
            <td class="px-4 py-2.5 text-[var(--text-muted)]">
              <span class="px-1.5 py-0.5 rounded bg-[var(--bg-raised)] text-[10px]">{{ getCategory(ep.path) === '(root)' ? t('customApi.rootCategory') : getCategory(ep.path) }}</span>
            </td>
            <td class="px-4 py-2.5 text-[var(--text-muted)]">{{ (ep.source_config?.type as string) || '-' }}</td>
            <td class="px-4 py-2.5">
              <UBadge status="info" size="sm">{{ getAuthLabel(ep.auth_type) }}</UBadge>
            </td>
            <td class="px-4 py-2.5 text-[var(--text-muted)]">{{ ep.rate_limit }}/h</td>
            <td class="px-4 py-2.5">
              <UBadge :status="ep.enabled ? 'ok' : 'neutral'" size="sm">
                {{ ep.enabled ? t('status.enabled') : t('status.disabled') }}
              </UBadge>
            </td>
            <td class="px-4 py-2.5 text-right" @click.stop>
              <div class="flex items-center justify-end gap-1">
                <UButton size="sm" variant="ghost" @click="openEdit(ep)">{{ t('common.edit') }}</UButton>
                <button
                  :class="['relative w-8 h-4 rounded-full transition-colors', ep.enabled ? 'bg-[var(--status-ok)]' : 'bg-[var(--bg-overlay)]']"
                  @click="toggleEnabled(ep)"
                >
                  <span :class="['absolute top-0.5 h-3 w-3 rounded-full bg-white shadow transition-transform', ep.enabled ? 'translate-x-4' : 'translate-x-0.5']" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ════════════════════════════════════════════════════════════════════════ -->
    <!-- Create/Edit Modal (Stepper)                                          -->
    <!-- ════════════════════════════════════════════════════════════════════════ -->
    <UModal
      :open="modalOpen"
      :title="modalMode === 'create' ? t('customApi.newEndpoint') : t('customApi.editEndpoint')"
      size="lg"
      @close="modalOpen = false"
    >
      <!-- Step indicator -->
      <div class="flex items-center gap-2 mb-5 pb-4 border-b border-[var(--border)]">
        <template v-for="step in totalSteps" :key="step">
          <div
            :class="[
              'flex items-center gap-1.5',
              modalStep === step ? 'text-[var(--primary)]' : modalStep > step ? 'text-[var(--status-ok)]' : 'text-[var(--text-muted)]'
            ]"
          >
            <span
              :class="[
                'w-6 h-6 rounded-full text-[10px] font-bold flex items-center justify-center border',
                modalStep === step ? 'border-[var(--primary)] bg-[var(--primary)]/10' : modalStep > step ? 'border-[var(--status-ok)] bg-[var(--status-ok)]/10' : 'border-[var(--border)] bg-[var(--bg-raised)]'
              ]"
            >
              <svg v-if="modalStep > step" class="h-3 w-3" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
              <span v-else>{{ step }}</span>
            </span>
            <span class="text-xs font-medium hidden sm:inline">
              {{ step === 1 ? t('customApi.stepBasics') : step === 2 ? t('customApi.stepDataSource') : step === 3 ? t('customApi.stepSecurity') : t('customApi.stepPreview') }}
            </span>
          </div>
          <div v-if="step < totalSteps" class="flex-1 h-px bg-[var(--border)]" />
        </template>
      </div>

      <!-- Step 1: Basics -->
      <div v-if="modalStep === 1" class="space-y-4">
        <UInput v-model="formName" :label="t('customApi.nameLabel')" :placeholder="t('customApi.namePlaceholder')" />
        <div class="flex flex-col gap-1">
          <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ t('customApi.pathLabel') }}</label>
          <div class="flex items-center gap-0">
            <span class="px-3 py-2 text-xs font-mono bg-[var(--bg-raised)] border border-r-0 border-[var(--border)] rounded-l-lg text-[var(--text-muted)] whitespace-nowrap">{{ pathPrefix }}</span>
            <input
              v-model="formPath"
              :class="['input w-full rounded-l-none', pathError ? 'border-red-500 focus:border-red-500' : '']"
              :placeholder="t('customApi.pathPlaceholder')"
            />
          </div>
          <p v-if="pathError" class="text-[10px] text-red-400 mt-1">{{ pathError }}</p>
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ t('customApi.methodLabel') }}</label>
          <div class="flex gap-1 p-0.5 rounded-lg bg-[var(--bg-raised)] w-fit">
            <button
              :class="['px-4 py-1.5 text-xs font-bold rounded-md transition-colors font-mono', formMethod === 'GET' ? 'bg-green-500/20 text-green-400 shadow-sm' : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]']"
              @click="formMethod = 'GET'"
            >GET</button>
            <button
              :class="['px-4 py-1.5 text-xs font-bold rounded-md transition-colors font-mono', formMethod === 'POST' ? 'bg-amber-500/20 text-amber-400 shadow-sm' : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]']"
              @click="formMethod = 'POST'"
            >POST</button>
          </div>
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ t('customApi.descriptionLabel') }}</label>
          <textarea
            v-model="formDescription"
            rows="2"
            class="input w-full resize-none"
            :placeholder="t('customApi.descriptionPlaceholder')"
          />
        </div>
      </div>

      <!-- Step 2: Data Source (GET) -->
      <div v-if="modalStep === 2 && formMethod === 'GET'" class="space-y-4">
        <div class="flex flex-col gap-1">
          <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ t('customApi.sourceTypeLabel') }}</label>
          <div class="grid grid-cols-3 gap-2">
            <button
              v-for="src in ['variables', 'devices', 'entities', 'alerts', 'events', 'status_snapshot'] as const"
              :key="src"
              :class="[
                'px-3 py-2 rounded-lg border text-xs font-medium transition-all text-center',
                formSourceType === src
                  ? 'border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)]'
                  : 'border-[var(--border)] bg-[var(--bg-base)] text-[var(--text-secondary)] hover:border-[var(--border-hover)]'
              ]"
              @click="formSourceType = src"
            >{{ t(`customApi.source.${src}`) }}</button>
          </div>
        </div>

        <!-- Variable-specific options -->
        <template v-if="formSourceType === 'variables'">
          <UEntitySelect
            v-model="formDeviceFilter"
            entity-type="device"
            :label="t('customApi.deviceFilterLabel')"
            :placeholder="t('customApi.deviceFilterPlaceholder')"
            optional
          />
          <UEntitySelect
            v-model="formVariableKeys"
            entity-type="variable"
            :label="t('customApi.variableKeysLabel')"
            :placeholder="t('customApi.variableKeysPlaceholder')"
            optional
          />
        </template>

        <!-- Device-specific options -->
        <template v-if="formSourceType === 'devices'">
          <UEntitySelect
            v-model="formDeviceFilter"
            entity-type="device"
            :label="t('customApi.selectDevices')"
            :placeholder="t('customApi.selectDevicesPlaceholder')"
            optional
          />
        </template>

        <!-- Entity-specific options -->
        <template v-if="formSourceType === 'entities'">
          <UEntitySelect
            v-model="formDeviceFilter"
            entity-type="entity"
            :label="t('customApi.selectEntities')"
            :placeholder="t('customApi.selectEntitiesPlaceholder')"
            optional
          />
        </template>

        <!-- Aggregation (variables only) -->
        <div v-if="formSourceType === 'variables'" class="grid grid-cols-3 gap-3">
          <div class="flex flex-col gap-1">
            <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ t('customApi.aggregation') }}</label>
            <select v-model="formAggregation" class="input w-full">
              <option value="none">{{ t('common.none') }}</option>
              <option value="avg">{{ t('customApi.aggAvg') }}</option>
              <option value="min">{{ t('customApi.aggMin') }}</option>
              <option value="max">{{ t('customApi.aggMax') }}</option>
              <option value="sum">{{ t('customApi.aggSum') }}</option>
            </select>
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ t('customApi.timeRange') }}</label>
            <select v-model="formTimeRange" class="input w-full">
              <option value="raw">{{ t('customApi.timeRaw') }}</option>
              <option value="1h">{{ t('customApi.time1h') }}</option>
              <option value="24h">{{ t('customApi.time24h') }}</option>
              <option value="7d">{{ t('customApi.time7d') }}</option>
              <option value="30d">{{ t('customApi.time30d') }}</option>
            </select>
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ t('customApi.groupBy') }}</label>
            <select v-model="formGroupBy" class="input w-full">
              <option value="none">{{ t('common.none') }}</option>
              <option value="hour">{{ t('customApi.groupHour') }}</option>
              <option value="day">{{ t('customApi.groupDay') }}</option>
              <option value="month">{{ t('customApi.groupMonth') }}</option>
            </select>
          </div>
        </div>

        <!-- Format toggle -->
        <div class="flex flex-col gap-1">
          <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ t('customApi.formatLabel') }}</label>
          <div class="flex gap-1 p-0.5 rounded-lg bg-[var(--bg-raised)] w-fit">
            <button
              :class="['px-3 py-1 text-xs font-medium rounded-md transition-colors', formFormat === 'json' ? 'bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-sm' : 'text-[var(--text-muted)]']"
              @click="formFormat = 'json'"
            >JSON</button>
            <button
              :class="['px-3 py-1 text-xs font-medium rounded-md transition-colors', formFormat === 'csv' ? 'bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-sm' : 'text-[var(--text-muted)]']"
              @click="formFormat = 'csv'"
            >CSV</button>
          </div>
        </div>
      </div>

      <!-- Step 2: Data Source (POST) -->
      <div v-if="modalStep === 2 && formMethod === 'POST'" class="space-y-4">
        <!-- Warning banner -->
        <div class="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-xs text-amber-300 flex items-start gap-2">
          <svg class="h-4 w-4 shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /></svg>
          <span>{{ t('customApi.writeWarning') }}</span>
        </div>

        <UToggle v-model="formWriteEnabled" :label="t('customApi.writeEnabledLabel')" />

        <div v-if="formWriteEnabled" class="space-y-4 pl-1 border-l-2 border-amber-500/30 ml-2">
          <div class="flex flex-col gap-1 pl-3">
            <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ t('customApi.targetType') }}</label>
            <select v-model="formTargetType" class="input w-full">
              <option value="set_variable">{{ t('customApi.targetSetVariable') }}</option>
            </select>
          </div>
          <div class="pl-3">
            <UEntitySelect
              v-model="formAllowedKeys"
              entity-type="variable"
              :label="t('customApi.allowedKeysLabel')"
              :placeholder="t('customApi.allowedKeysPlaceholder')"
              optional
            />
          </div>
          <div class="pl-3">
            <UEntitySelect
              v-model="formDeviceScope"
              entity-type="device"
              :label="t('customApi.deviceScopeLabel')"
              :placeholder="t('customApi.deviceScopePlaceholder')"
              optional
            />
          </div>
        </div>
      </div>

      <!-- Step 3: Security -->
      <div v-if="modalStep === 3" class="space-y-4">
        <div class="flex flex-col gap-1">
          <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ t('customApi.authTypeLabel') }}</label>
          <div class="grid grid-cols-3 gap-2">
            <button
              v-for="auth in ['api_key', 'bearer', 'none'] as const"
              :key="auth"
              :class="[
                'px-3 py-2.5 rounded-lg border text-xs font-medium transition-all text-center',
                formAuthType === auth
                  ? 'border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)]'
                  : 'border-[var(--border)] bg-[var(--bg-base)] text-[var(--text-secondary)] hover:border-[var(--border-hover)]'
              ]"
              @click="formAuthType = auth"
            >
              <span class="block font-semibold">{{ auth === 'api_key' ? t('customApi.authApiKey') : auth === 'bearer' ? t('customApi.authBearerToken') : t('customApi.publicNoAuth') }}<span v-if="auth === 'api_key'" class="ml-1 text-[10px] font-medium text-green-400">{{ t('customApi.authRecommended') }}</span></span>
              <span class="block text-[10px] mt-0.5 leading-snug" :class="auth === 'none' ? 'text-amber-400' : 'text-[var(--text-muted)]'">{{ t(`customApi.authHint.${auth}`) }}</span>
            </button>
          </div>
        </div>

        <div v-if="formAuthType === 'none'" class="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-xs text-amber-300 flex items-start gap-2">
          <svg class="h-4 w-4 shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /></svg>
          <span>{{ t('customApi.publicWarning') }}</span>
        </div>

        <div class="flex flex-col gap-1">
          <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ t('customApi.rateLimitLabel') }}</label>
          <div class="flex items-center gap-3">
            <input
              v-model.number="formRateLimit"
              type="range"
              min="10"
              max="10000"
              step="10"
              class="flex-1 h-1.5 accent-[var(--primary)]"
            />
            <div class="flex items-center gap-1">
              <input
                v-model.number="formRateLimit"
                type="number"
                min="10"
                max="10000"
                class="input w-20 text-center text-xs"
              />
              <span class="text-[10px] text-[var(--text-muted)]">{{ t('customApi.reqPerHour') }}</span>
            </div>
          </div>
        </div>

        <div v-if="modalMode === 'create'" class="rounded-lg border border-[var(--border)] bg-[var(--bg-raised)] px-4 py-3 text-xs text-[var(--text-muted)]">
          <svg class="h-4 w-4 inline-block mr-1 text-[var(--status-info)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" /></svg>
          {{ t('customApi.keyAutoGenerated') }}
        </div>
      </div>

      <!-- Step 4: Preview & Save -->
      <div v-if="modalStep === 4" class="space-y-4">
        <!-- Summary -->
        <div class="rounded-lg border border-[var(--border)] bg-[var(--bg-raised)] p-4 space-y-2">
          <div class="flex items-center gap-2">
            <span
              class="text-[10px] px-1.5 py-0.5 rounded font-mono font-bold"
              :class="formMethod === 'GET' ? 'bg-green-500/20 text-green-400' : 'bg-amber-500/20 text-amber-400'"
            >{{ formMethod }}</span>
            <span class="text-xs font-mono text-[var(--text-primary)]">{{ fullPath }}</span>
          </div>
          <div class="flex items-center gap-3 text-[10px] text-[var(--text-muted)]">
            <span>{{ t('customApi.colAuth') }}: {{ getAuthLabel(formAuthType) }}</span>
            <span>{{ t('customApi.colRateLimit') }}: {{ formRateLimit }}/h</span>
            <span v-if="formMethod === 'GET'">{{ t('customApi.colSource') }}: {{ formSourceType }}</span>
          </div>
        </div>

        <!-- Preview data -->
        <div class="flex flex-col gap-1">
          <div class="flex items-center justify-between">
            <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ t('customApi.previewTitle') }}</label>
            <UButton v-if="editId" size="sm" variant="ghost" @click="loadPreview">{{ t('common.refresh') }}</UButton>
          </div>
          <div class="relative">
            <pre class="rounded-lg border border-[var(--border)] bg-[var(--bg-base)] p-3 text-xs font-mono text-[var(--text-secondary)] overflow-x-auto max-h-40 overflow-y-auto">{{ previewLoading ? t('common.loading') : (previewData || t('customApi.previewAfterSave')) }}</pre>
            <button
              v-if="previewData"
              class="absolute top-2 right-2 p-1 rounded text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]"
              @click="copyToClipboard(previewData!)"
            >
              <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" /></svg>
            </button>
          </div>
        </div>

        <!-- cURL example -->
        <div class="flex flex-col gap-1">
          <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ t('customApi.curlExample') }}</label>
          <div class="relative">
            <pre class="rounded-lg border border-[var(--border)] bg-[var(--bg-base)] p-3 text-xs font-mono text-[var(--text-secondary)] overflow-x-auto">{{ getCurlExample({ method: formMethod, path: formPath, auth_type: formAuthType, api_key: null } as CustomEndpoint) }}</pre>
            <button
              class="absolute top-2 right-2 p-1 rounded text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]"
              @click="copyToClipboard(getCurlExample({ method: formMethod, path: formPath, auth_type: formAuthType, api_key: null } as CustomEndpoint))"
            >
              <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" /></svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Footer with navigation -->
      <template #footer>
        <div class="flex justify-between w-full">
          <div>
            <UButton v-if="modalStep > 1" variant="ghost" @click="modalStep--">
              {{ t('common.back') }}
            </UButton>
          </div>
          <div class="flex gap-2">
            <UButton variant="ghost" @click="modalOpen = false">{{ t('common.cancel') }}</UButton>
            <UButton v-if="modalStep < totalSteps" :disabled="modalStep === 1 && !canProceedStep1" @click="modalStep++">
              {{ t('common.next') }}
            </UButton>
            <UButton v-else :loading="saving" @click="handleSave">
              {{ saving ? t('customApi.saving') : modalMode === 'create' ? t('common.create') : t('common.save') }}
            </UButton>
          </div>
        </div>
      </template>
    </UModal>

    <!-- ════════════════════════════════════════════════════════════════════════ -->
    <!-- Detail Modal                                                          -->
    <!-- ════════════════════════════════════════════════════════════════════════ -->
    <UModal
      :open="detailOpen"
      :title="detailEndpoint?.name || ''"
      size="lg"
      @close="detailOpen = false"
    >
      <div v-if="detailEndpoint" class="space-y-5">
        <!-- Header info -->
        <div class="flex items-center gap-3">
          <span
            class="text-xs px-2 py-1 rounded font-mono font-bold"
            :class="detailEndpoint.method === 'GET' ? 'bg-green-500/20 text-green-400' : 'bg-amber-500/20 text-amber-400'"
          >{{ detailEndpoint.method }}</span>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-mono text-[var(--text-primary)] truncate">{{ getEndpointUrl(detailEndpoint) }}</p>
          </div>
          <button
            class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]"
            @click="copyToClipboard(getEndpointUrl(detailEndpoint))"
            :title="t('customApi.copyUrl')"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" /></svg>
          </button>
        </div>

        <!-- Stats row -->
        <div class="flex items-center gap-4 text-xs">
          <UBadge :status="detailEndpoint.enabled ? 'ok' : 'neutral'">
            {{ detailEndpoint.enabled ? t('status.enabled') : t('status.disabled') }}
          </UBadge>
          <UBadge status="info">{{ getAuthLabel(detailEndpoint.auth_type) }}</UBadge>
          <span class="text-[var(--text-muted)]">{{ detailEndpoint.request_count }} {{ t('customApi.requests') }}</span>
          <span class="text-[var(--text-muted)]">{{ t('customApi.lastCalled') }}: {{ relativeTime(detailEndpoint.last_called_at) }}</span>
        </div>

        <!-- Description -->
        <p v-if="detailEndpoint.description" class="text-xs text-[var(--text-secondary)]">{{ detailEndpoint.description }}</p>

        <!-- API Key (if applicable) -->
        <div v-if="detailEndpoint.auth_type !== 'none' && detailEndpoint.api_key" class="flex flex-col gap-1">
          <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ detailEndpoint.auth_type === 'api_key' ? t('customApi.authApiKey') : t('customApi.authBearerToken') }}</label>
          <div class="flex items-center gap-2">
            <code class="flex-1 px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs font-mono text-[var(--text-secondary)] truncate">{{ detailEndpoint.api_key }}</code>
            <UButton size="sm" variant="ghost" @click="copyToClipboard(detailEndpoint.api_key!)">{{ t('customApi.copy') }}</UButton>
            <UButton size="sm" variant="ghost" :loading="detailKeyRegenLoading" @click="handleRegenKey">{{ t('customApi.regenerate') }}</UButton>
          </div>
        </div>

        <!-- Code snippets -->
        <div class="flex flex-col gap-1">
          <div class="flex items-center justify-between">
            <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ t('customApi.codeSnippets') }}</label>
            <div class="flex gap-1 p-0.5 rounded-lg bg-[var(--bg-raised)]">
              <button
                v-for="tab in ['curl', 'python', 'javascript'] as const"
                :key="tab"
                :class="['px-2 py-0.5 text-[10px] font-medium rounded transition-colors', codeTab === tab ? 'bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-sm' : 'text-[var(--text-muted)]']"
                @click="codeTab = tab"
              >{{ tab === 'curl' ? 'cURL' : tab === 'python' ? 'Python' : 'JavaScript' }}</button>
            </div>
          </div>
          <div class="relative">
            <pre class="rounded-lg border border-[var(--border)] bg-[var(--bg-base)] p-3 text-xs font-mono text-[var(--text-secondary)] overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap">{{ codeTab === 'curl' ? getCurlExample(detailEndpoint) : codeTab === 'python' ? getPythonExample(detailEndpoint) : getJsExample(detailEndpoint) }}</pre>
            <button
              class="absolute top-2 right-2 p-1 rounded text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]"
              @click="copyToClipboard(codeTab === 'curl' ? getCurlExample(detailEndpoint) : codeTab === 'python' ? getPythonExample(detailEndpoint) : getJsExample(detailEndpoint))"
            >
              <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" /></svg>
            </button>
          </div>
        </div>

        <!-- Test endpoint -->
        <div class="flex flex-col gap-1">
          <div class="flex items-center justify-between">
            <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ t('customApi.testEndpoint') }}</label>
            <UButton size="sm" variant="secondary" :loading="detailTesting" @click="handleTest">
              {{ t('customApi.runTest') }}
            </UButton>
          </div>
          <pre v-if="detailTestResult" class="rounded-lg border border-[var(--border)] bg-[var(--bg-base)] p-3 text-xs font-mono text-[var(--text-secondary)] overflow-x-auto max-h-40 overflow-y-auto whitespace-pre-wrap">{{ detailTestResult }}</pre>
        </div>
      </div>

      <template #footer>
        <div class="flex justify-between w-full">
          <UButton variant="danger" size="sm" @click="detailEndpoint && handleDelete(detailEndpoint.id)">
            {{ t('common.delete') }}
          </UButton>
          <div class="flex gap-2">
            <UButton variant="ghost" @click="detailOpen = false">{{ t('common.close') }}</UButton>
            <UButton @click="detailEndpoint && openEdit(detailEndpoint); detailOpen = false">{{ t('common.edit') }}</UButton>
          </div>
        </div>
      </template>
    </UModal>
  </div>
</template>
