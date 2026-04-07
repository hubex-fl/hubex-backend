<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";
import UModal from "../components/ui/UModal.vue";
import UBadge from "../components/ui/UBadge.vue";
import UEmpty from "../components/ui/UEmpty.vue";

const toast = useToastStore();
const { t } = useI18n();

type Endpoint = {
  id: number;
  name: string;
  route_path: string;
  method: string;
  description: string | null;
  response_mapping: Record<string, unknown>;
  params_schema: Record<string, unknown> | null;
  rate_limit_per_minute: number;
  required_scope: string | null;
  enabled: boolean;
  request_count: number;
  last_called_at: string | null;
  created_at: string;
};

const endpoints = ref<Endpoint[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// Create/Edit
const modalOpen = ref(false);
const modalMode = ref<"create" | "edit">("create");
const editId = ref<number | null>(null);
const formName = ref("");
const formRoute = ref("/custom/");
const formMethod = ref("GET");
const formDescription = ref("");
const formMapping = ref("{}");
const formRateLimit = ref(60);
const formScope = ref("");
const saving = ref(false);

async function load() {
  loading.value = true;
  error.value = null;
  try {
    endpoints.value = await apiFetch<Endpoint[]>("/api/v1/custom-endpoints");
  } catch {
    error.value = "Failed to load endpoints";
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  modalMode.value = "create";
  editId.value = null;
  formName.value = "";
  formRoute.value = "/custom/";
  formMethod.value = "GET";
  formDescription.value = "";
  formMapping.value = '{\n  "source": "variables",\n  "filter": {"variable_key": "temperature"}\n}';
  formRateLimit.value = 60;
  formScope.value = "";
  modalOpen.value = true;
}

function openEdit(ep: Endpoint) {
  modalMode.value = "edit";
  editId.value = ep.id;
  formName.value = ep.name;
  formRoute.value = ep.route_path;
  formMethod.value = ep.method;
  formDescription.value = ep.description || "";
  formMapping.value = JSON.stringify(ep.response_mapping, null, 2);
  formRateLimit.value = ep.rate_limit_per_minute;
  formScope.value = ep.required_scope || "";
  modalOpen.value = true;
}

async function handleSave() {
  saving.value = true;
  try {
    let mapping: Record<string, unknown> = {};
    try { mapping = JSON.parse(formMapping.value); } catch { /* keep empty */ }

    if (modalMode.value === "create") {
      await apiFetch("/api/v1/custom-endpoints", {
        method: "POST",
        body: JSON.stringify({
          name: formName.value.trim(),
          route_path: formRoute.value.trim(),
          method: formMethod.value,
          description: formDescription.value || null,
          response_mapping: mapping,
          rate_limit_per_minute: formRateLimit.value,
          required_scope: formScope.value || null,
        }),
      });
      toast.addToast(t('toast.created', { item: 'Endpoint' }), "success");
    } else {
      await apiFetch(`/api/v1/custom-endpoints/${editId.value}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: formName.value.trim(),
          description: formDescription.value || null,
          response_mapping: mapping,
          rate_limit_per_minute: formRateLimit.value,
          required_scope: formScope.value || null,
        }),
      });
      toast.addToast("Endpoint updated", "success");
    }
    modalOpen.value = false;
    await load();
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : "Save failed", "error");
  } finally {
    saving.value = false;
  }
}

async function handleDelete(id: number) {
  if (!confirm("Delete this custom endpoint?")) return;
  try {
    await apiFetch(`/api/v1/custom-endpoints/${id}`, { method: "DELETE" });
    toast.addToast("Endpoint deleted", "success");
    await load();
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : "Delete failed", "error");
  }
}

async function toggleEnabled(ep: Endpoint) {
  try {
    await apiFetch(`/api/v1/custom-endpoints/${ep.id}`, {
      method: "PATCH",
      body: JSON.stringify({ enabled: !ep.enabled }),
    });
    ep.enabled = !ep.enabled;
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : "Toggle failed", "error");
  }
}

onMounted(load);
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-xl font-semibold text-[var(--text-primary)]">{{ t('pages.customApi.title') }}</h1>
        <p class="text-xs text-[var(--text-muted)] mt-0.5">
          {{ t('pages.customApi.subtitle') }}.
          <router-link to="/developer" class="text-[var(--primary)] hover:underline ml-1">API Docs</router-link> ·
          <router-link to="/variables" class="text-[var(--primary)] hover:underline">Variables</router-link>
        </p>
      </div>
      <button
        class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black hover:bg-[var(--primary-hover)]"
        @click="openCreate"
      >+ New Endpoint</button>
    </div>

    <div v-if="loading" class="text-xs text-[var(--text-muted)]">Loading...</div>

    <div v-else-if="error" class="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-400">
      <p>{{ error }}</p>
      <button class="mt-2 px-2.5 py-1 rounded text-xs font-medium border border-red-500/30 hover:bg-red-500/10" @click="load">Retry</button>
    </div>

    <UEmpty v-else-if="!endpoints.length"
      title="No custom endpoints"
      description="Build custom API endpoints that serve HUBEX data in your own format. Great for dashboards, integrations, and reporting."
      icon="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5"
    >
      <button class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black" @click="openCreate">Create Endpoint</button>
    </UEmpty>

    <div v-else class="space-y-3">
      <div v-for="ep in endpoints" :key="ep.id" class="border border-[var(--border)] rounded-xl bg-[var(--bg-surface)] px-5 py-4">
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-[10px] px-1.5 py-0.5 rounded font-mono font-bold"
                :class="ep.method === 'GET' ? 'bg-green-500/20 text-green-400' : 'bg-blue-500/20 text-blue-400'">
                {{ ep.method }}
              </span>
              <span class="text-sm font-medium text-[var(--text-primary)]">{{ ep.name }}</span>
              <UBadge :status="ep.enabled ? 'ok' : 'neutral'" size="sm">{{ ep.enabled ? 'active' : 'disabled' }}</UBadge>
            </div>
            <p class="text-xs font-mono text-[var(--text-secondary)]">{{ ep.route_path }}</p>
            <p v-if="ep.description" class="text-[10px] text-[var(--text-muted)] mt-1">{{ ep.description }}</p>
            <div class="flex items-center gap-4 mt-2 text-[10px] text-[var(--text-muted)]">
              <span>{{ ep.request_count }} requests</span>
              <span>{{ ep.rate_limit_per_minute }} req/min</span>
              <span v-if="ep.required_scope">scope: {{ ep.required_scope }}</span>
            </div>
          </div>
          <div class="flex items-center gap-1.5 shrink-0">
            <button class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]" title="Edit" @click="openEdit(ep)">
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z" /></svg>
            </button>
            <button
              :class="['relative w-9 h-5 rounded-full transition-colors', ep.enabled ? 'bg-[var(--status-ok)]' : 'bg-[var(--bg-overlay)]']"
              @click="toggleEnabled(ep)"
            >
              <span :class="['absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform', ep.enabled ? 'translate-x-4' : 'translate-x-0.5']" />
            </button>
            <button class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-red-400 hover:bg-red-500/10" title="Delete" @click="handleDelete(ep.id)">
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" /></svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <UModal :open="modalOpen" :title="modalMode === 'create' ? 'New Custom Endpoint' : 'Edit Endpoint'" size="lg" @close="modalOpen = false">
      <div class="space-y-3">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-[10px] font-medium text-[var(--text-muted)]">Name *</label>
            <input v-model="formName" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs" placeholder="Temperature Summary" />
          </div>
          <div>
            <label class="text-[10px] font-medium text-[var(--text-muted)]">Method</label>
            <select v-model="formMethod" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)]">
              <option value="GET">GET</option>
              <option value="POST">POST</option>
            </select>
          </div>
        </div>
        <div>
          <label class="text-[10px] font-medium text-[var(--text-muted)]">Route Path *</label>
          <input v-model="formRoute" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs font-mono" placeholder="/custom/my-data" />
        </div>
        <div>
          <label class="text-[10px] font-medium text-[var(--text-muted)]">Description</label>
          <input v-model="formDescription" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs" placeholder="Returns current temperature readings" />
        </div>
        <details class="border border-[var(--border)] rounded-lg p-3">
          <summary class="text-[10px] font-medium text-[var(--text-muted)] cursor-pointer hover:text-[var(--text-primary)]">
            Response Mapping (JSON) — {{ formMapping.length > 5 ? 'configured' : 'not set' }}
          </summary>
          <textarea v-model="formMapping" rows="5" class="mt-2 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs font-mono text-[var(--text-primary)]" placeholder='{"source": "variables", "filter": {"variable_key": "temperature"}}' />
        </details>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-[10px] font-medium text-[var(--text-muted)]">Rate Limit (req/min)</label>
            <input v-model.number="formRateLimit" type="number" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs" />
          </div>
          <div>
            <label class="text-[10px] font-medium text-[var(--text-muted)]">Access Scope (leave empty for public)</label>
            <input v-model="formScope" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs font-mono" placeholder="e.g. custom.read" />
          </div>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <button class="px-3 py-2 rounded-lg text-xs text-[var(--text-muted)]" @click="modalOpen = false">Cancel</button>
          <button :disabled="saving || !formName.trim()" class="px-3 py-2 rounded-lg text-xs font-medium bg-[var(--primary)] text-black disabled:opacity-50" @click="handleSave">
            {{ saving ? 'Saving...' : modalMode === 'create' ? 'Create' : 'Save' }}
          </button>
        </div>
      </template>
    </UModal>
  </div>
</template>
