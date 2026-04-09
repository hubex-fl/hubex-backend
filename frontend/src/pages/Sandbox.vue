<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { useToastStore } from "../stores/toast";
import {
  listSimulators,
  createSimulator,
  updateSimulator,
  deleteSimulator,
  startSimulator,
  stopSimulator,
  generatePreview,
  PATTERN_OPTIONS,
  BUILTIN_TEMPLATES,
  type SimulatorConfig,
  type SimulatorCreate,
  type SimulatorTemplate,
  type VariablePattern,
} from "../lib/simulator";
import UCard from "../components/ui/UCard.vue";
import UBadge from "../components/ui/UBadge.vue";
import UButton from "../components/ui/UButton.vue";
import UInput from "../components/ui/UInput.vue";
import USelect from "../components/ui/USelect.vue";
import UEmpty from "../components/ui/UEmpty.vue";
import UModal from "../components/ui/UModal.vue";
import UToggle from "../components/ui/UToggle.vue";
import UInfoTooltip from "../components/ui/UInfoTooltip.vue";
import USkeleton from "../components/ui/USkeleton.vue";
import VizSparkline from "../components/viz/VizSparkline.vue";

const { t } = useI18n();
const router = useRouter();
const toast = useToastStore();

// ── State ────────────────────────────────────────────────────────────────────
const simulators = ref<SimulatorConfig[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// ── Detail view ──────────────────────────────────────────────────────────────
const detailSim = ref<SimulatorConfig | null>(null);

// ── Create/Edit modal ────────────────────────────────────────────────────────
const modalOpen = ref(false);
const modalMode = ref<"create" | "edit">("create");
const modalStep = ref(1);
const saving = ref(false);
const editId = ref<number | null>(null);

// Step 1 — Template
const selectedTemplate = ref<string | null>(null);

// Step 2 — Variables
const formVariables = ref<VariablePattern[]>([]);
const expandedVarIdx = ref<number | null>(0);

// Step 3 — Settings
const formName = ref("");
const formDescription = ref("");
const formInterval = ref(15);
const formSpeed = ref(1);
const formVirtualDevice = ref(true);
const formAutoStart = ref(false);
const formDeviceUid = ref("");

// ── Delete confirm ───────────────────────────────────────────────────────────
const deleteConfirmOpen = ref(false);
const deleteTarget = ref<SimulatorConfig | null>(null);
const deleting = ref(false);

// ── Polling ──────────────────────────────────────────────────────────────────
let pollTimer: ReturnType<typeof setInterval> | null = null;

// ── Computed ─────────────────────────────────────────────────────────────────
const templates = computed<SimulatorTemplate[]>(() => BUILTIN_TEMPLATES);

const templateIcons: Record<string, string> = {
  thermometer: "\uD83C\uDF21\uFE0F",
  bolt: "\u26A1",
  "map-pin": "\uD83D\uDCCD",
  activity: "\uD83D\uDD32",
  "cloud-sun": "\uD83C\uDF24\uFE0F",
  wrench: "\uD83D\uDD27",
};

function templateEmoji(icon: string): string {
  return templateIcons[icon] || "\uD83E\uDDEA";
}

const patternSelectOptions = computed(() =>
  PATTERN_OPTIONS.map((p) => ({ value: p.value, label: p.label })),
);

const canProceedStep1 = computed(() => selectedTemplate.value !== null);
const canProceedStep2 = computed(
  () =>
    formVariables.value.length > 0 &&
    formVariables.value.every((v) => v.variable_key.trim() !== ""),
);
const canCreate = computed(() => formName.value.trim() !== "");

// ── Time helpers ─────────────────────────────────────────────────────────────
function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "-";
  const diff = Date.now() - new Date(dateStr).getTime();
  if (diff < 5_000) return t("sandbox.justNow");
  if (diff < 60_000) return `${Math.floor(diff / 1000)}s ${t("sandbox.ago")}`;
  if (diff < 3_600_000) return `${Math.floor(diff / 60000)}m ${t("sandbox.ago")}`;
  return `${Math.floor(diff / 3600000)}h ${t("sandbox.ago")}`;
}

function formatNumber(n: number): string {
  return n.toLocaleString();
}

// ── Load ─────────────────────────────────────────────────────────────────────
async function load() {
  loading.value = true;
  error.value = null;
  try {
    simulators.value = await listSimulators();
  } catch (e: unknown) {
    // Distinguish real errors from empty state: if the API returns 404
    // because the table doesn't exist yet, treat as empty list
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.includes("404") || msg.includes("Not Found")) {
      simulators.value = [];
    } else {
      error.value = t("sandbox.loadError");
    }
  } finally {
    loading.value = false;
  }
}

async function poll() {
  try {
    simulators.value = await listSimulators();
    // Update detail view if open
    if (detailSim.value) {
      const updated = simulators.value.find((s) => s.id === detailSim.value!.id);
      if (updated) detailSim.value = updated;
    }
  } catch {
    // Silent poll failure
  }
}

// ── Template selection ───────────────────────────────────────────────────────
function selectTemplate(tmpl: SimulatorTemplate) {
  selectedTemplate.value = tmpl.id;
  formVariables.value = JSON.parse(JSON.stringify(tmpl.variable_patterns));
  formName.value = tmpl.id === "custom" ? "" : tmpl.name;
  formDescription.value = tmpl.id === "custom" ? "" : tmpl.description;
}

// ── Variable management ──────────────────────────────────────────────────────
function addVariable() {
  formVariables.value.push({
    variable_key: "",
    pattern: "sine",
    config: { min: 0, max: 100, period: 60 },
  });
  expandedVarIdx.value = formVariables.value.length - 1;
}

function removeVariable(idx: number) {
  formVariables.value.splice(idx, 1);
  if (expandedVarIdx.value === idx) expandedVarIdx.value = null;
  else if (expandedVarIdx.value !== null && expandedVarIdx.value > idx)
    expandedVarIdx.value--;
}

function toggleVarExpand(idx: number) {
  expandedVarIdx.value = expandedVarIdx.value === idx ? null : idx;
}

function moveVariable(idx: number, dir: -1 | 1) {
  const target = idx + dir;
  if (target < 0 || target >= formVariables.value.length) return;
  const arr = [...formVariables.value];
  [arr[idx], arr[target]] = [arr[target], arr[idx]];
  formVariables.value = arr;
  if (expandedVarIdx.value === idx) expandedVarIdx.value = target;
  else if (expandedVarIdx.value === target) expandedVarIdx.value = idx;
}

/** Get default config for a given pattern */
function defaultConfigFor(pattern: VariablePattern["pattern"]): Record<string, unknown> {
  switch (pattern) {
    case "sine":
      return { min: 0, max: 100, period: 60, phase_offset: 0 };
    case "random_walk":
      return { center: 50, volatility: 5, min_bound: 0, max_bound: 100 };
    case "step":
      return { values: "0,50,100", interval: 5 };
    case "ramp":
      return { start: 0, end: 100, duration: 30, loop: true };
    case "counter":
      return { start: 0, increment: 1, reset_at: 1000 };
    case "gps_track":
      return { waypoints: "48.2082,16.3738;48.2100,16.3800" };
    case "noise":
      return { center: 50, amplitude: 10 };
    case "formula":
      return { expression: "50 + 30 * sin(t / 10)" };
    case "csv_replay":
      return { loop: true };
    case "manual":
      return { initial_value: 0 };
    default:
      return {};
  }
}

function onPatternChange(idx: number, newPattern: string) {
  formVariables.value[idx].pattern = newPattern as VariablePattern["pattern"];
  formVariables.value[idx].config = defaultConfigFor(newPattern as VariablePattern["pattern"]);
}

/** Generate sparkline preview data for a variable */
function previewPoints(vp: VariablePattern): { t: number; v: number }[] {
  return generatePreview(vp.pattern, vp.config, 60);
}

// ── Open create modal ────────────────────────────────────────────────────────
function openCreate() {
  modalMode.value = "create";
  editId.value = null;
  modalStep.value = 1;
  selectedTemplate.value = null;
  formVariables.value = [];
  formName.value = "";
  formDescription.value = "";
  formInterval.value = 15;
  formSpeed.value = 1;
  formVirtualDevice.value = true;
  formAutoStart.value = false;
  formDeviceUid.value = "";
  expandedVarIdx.value = 0;
  modalOpen.value = true;
}

// ── Open edit modal ──────────────────────────────────────────────────────────
function openEdit(sim: SimulatorConfig) {
  modalMode.value = "edit";
  editId.value = sim.id;
  modalStep.value = 2; // Skip template step for edit
  selectedTemplate.value = sim.template;
  formVariables.value = JSON.parse(JSON.stringify(sim.variable_patterns));
  formName.value = sim.name;
  formDescription.value = sim.description ?? "";
  formInterval.value = sim.interval_seconds;
  formSpeed.value = sim.speed_multiplier;
  formVirtualDevice.value = sim.is_virtual_device;
  formAutoStart.value = false;
  formDeviceUid.value = sim.device_uid ?? "";
  expandedVarIdx.value = 0;
  modalOpen.value = true;
}

// ── Save ─────────────────────────────────────────────────────────────────────
async function handleSave() {
  saving.value = true;
  try {
    if (modalMode.value === "create") {
      const data: SimulatorCreate = {
        name: formName.value.trim(),
        description: formDescription.value.trim() || null,
        template: selectedTemplate.value,
        variable_patterns: formVariables.value,
        interval_seconds: formInterval.value,
        speed_multiplier: formSpeed.value,
        is_virtual_device: formVirtualDevice.value,
        auto_start: formAutoStart.value,
      };
      if (!formVirtualDevice.value && formDeviceUid.value) {
        data.device_uid = formDeviceUid.value;
      }
      const created = await createSimulator(data);
      simulators.value.push(created);
      toast.addToast(t("sandbox.created"), "success");
    } else if (editId.value !== null) {
      const updated = await updateSimulator(editId.value, {
        name: formName.value.trim(),
        description: formDescription.value.trim() || null,
        variable_patterns: formVariables.value,
        interval_seconds: formInterval.value,
        speed_multiplier: formSpeed.value,
      });
      const idx = simulators.value.findIndex((s) => s.id === editId.value);
      if (idx >= 0) simulators.value[idx] = updated;
      if (detailSim.value?.id === editId.value) detailSim.value = updated;
      toast.addToast(t("sandbox.updated"), "success");
    }
    modalOpen.value = false;
  } catch {
    toast.addToast(t("sandbox.saveError"), "error");
  } finally {
    saving.value = false;
  }
}

// ── Start/Stop ───────────────────────────────────────────────────────────────
async function handleStart(sim: SimulatorConfig) {
  try {
    const updated = await startSimulator(sim.id);
    const idx = simulators.value.findIndex((s) => s.id === sim.id);
    if (idx >= 0) simulators.value[idx] = updated;
    if (detailSim.value?.id === sim.id) detailSim.value = updated;
    toast.addToast(t("sandbox.started"), "success");
  } catch {
    toast.addToast(t("sandbox.startError"), "error");
  }
}

async function handleStop(sim: SimulatorConfig) {
  try {
    const updated = await stopSimulator(sim.id);
    const idx = simulators.value.findIndex((s) => s.id === sim.id);
    if (idx >= 0) simulators.value[idx] = updated;
    if (detailSim.value?.id === sim.id) detailSim.value = updated;
    toast.addToast(t("sandbox.stopped"), "success");
  } catch {
    toast.addToast(t("sandbox.stopError"), "error");
  }
}

// ── Delete ───────────────────────────────────────────────────────────────────
function confirmDelete(sim: SimulatorConfig) {
  deleteTarget.value = sim;
  deleteConfirmOpen.value = true;
}

async function handleDelete() {
  if (!deleteTarget.value) return;
  deleting.value = true;
  try {
    await deleteSimulator(deleteTarget.value.id);
    simulators.value = simulators.value.filter((s) => s.id !== deleteTarget.value!.id);
    if (detailSim.value?.id === deleteTarget.value.id) detailSim.value = null;
    toast.addToast(t("sandbox.deleted"), "success");
    deleteConfirmOpen.value = false;
  } catch {
    toast.addToast(t("sandbox.deleteError"), "error");
  } finally {
    deleting.value = false;
  }
}

// ── Detail view ──────────────────────────────────────────────────────────────
function openDetail(sim: SimulatorConfig) {
  detailSim.value = sim;
}

function closeDetail() {
  detailSim.value = null;
}

// ── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(() => {
  load();
  pollTimer = setInterval(poll, 5000);
});

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
});
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-6 space-y-6">
    <!-- Header -->
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div>
        <div class="flex items-center gap-2">
          <h1 class="text-xl font-semibold text-[var(--text-primary)]">
            {{ t('sandbox.title') }}
          </h1>
          <UInfoTooltip
            :title="t('sandbox.infoTitle')"
            :items="[t('sandbox.infoItem1'), t('sandbox.infoItem2'), t('sandbox.infoItem3')]"
          />
        </div>
        <p class="text-sm text-[var(--text-muted)] mt-1">{{ t('sandbox.subtitle') }}</p>
      </div>
      <UButton variant="primary" size="sm" @click="openCreate">
        + {{ t('sandbox.newSimulator') }}
      </UButton>
    </div>

    <!-- Loading skeletons -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <USkeleton v-for="i in 3" :key="i" class="h-44 rounded-xl" />
    </div>

    <!-- Error -->
    <div
      v-else-if="error"
      class="rounded-xl border border-[var(--status-bad)]/30 bg-[var(--status-bad-bg)] p-4 text-sm text-[var(--status-bad)]"
    >
      {{ error }}
      <button class="underline ml-2" @click="load">{{ t('common.refresh') }}</button>
    </div>

    <!-- Empty -->
    <UEmpty
      v-else-if="!simulators.length && !detailSim"
      :title="t('sandbox.emptyTitle')"
      :description="t('sandbox.emptyDesc')"
    >
      <template #action>
        <UButton variant="primary" size="sm" @click="openCreate">
          + {{ t('sandbox.newSimulator') }}
        </UButton>
      </template>
    </UEmpty>

    <!-- Detail view -->
    <template v-else-if="detailSim">
      <div class="space-y-4">
        <!-- Back button -->
        <button
          class="flex items-center gap-1.5 text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
          @click="closeDetail"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
          </svg>
          {{ t('sandbox.backToList') }}
        </button>

        <!-- Status header card -->
        <UCard>
          <div class="flex items-center justify-between flex-wrap gap-3">
            <div class="flex items-center gap-3">
              <span class="text-2xl">{{ templateEmoji(detailSim.template ? templates.find(t => t.id === detailSim!.template)?.icon ?? 'wrench' : 'wrench') }}</span>
              <div>
                <h2 class="text-lg font-semibold text-[var(--text-primary)]">{{ detailSim.name }}</h2>
                <p v-if="detailSim.description" class="text-xs text-[var(--text-muted)]">{{ detailSim.description }}</p>
              </div>
              <UBadge :status="detailSim.is_active ? 'ok' : 'neutral'" :pulse="detailSim.is_active">
                {{ detailSim.is_active ? t('sandbox.running') : t('sandbox.stopped_status') }}
              </UBadge>
              <UBadge v-if="detailSim.speed_multiplier > 1" status="info">
                {{ detailSim.speed_multiplier }}x
              </UBadge>
              <UBadge status="info">{{ t('sandbox.simulated') }}</UBadge>
            </div>
            <div class="flex items-center gap-2">
              <UButton
                v-if="!detailSim.is_active"
                variant="primary"
                size="sm"
                @click="handleStart(detailSim)"
              >
                {{ t('sandbox.start') }}
              </UButton>
              <UButton
                v-else
                variant="ghost"
                size="sm"
                @click="handleStop(detailSim)"
              >
                {{ t('sandbox.stop') }}
              </UButton>
              <UButton variant="ghost" size="sm" @click="openEdit(detailSim)">
                {{ t('common.edit') }}
              </UButton>
              <UButton variant="ghost" size="sm" @click="confirmDelete(detailSim)">
                {{ t('common.delete') }}
              </UButton>
            </div>
          </div>
        </UCard>

        <!-- Stats row -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <UCard>
            <p class="text-xs text-[var(--text-muted)]">{{ t('sandbox.totalPoints') }}</p>
            <p class="text-lg font-mono font-semibold text-[var(--text-primary)]">
              {{ formatNumber(detailSim.total_points_sent) }}
            </p>
          </UCard>
          <UCard>
            <p class="text-xs text-[var(--text-muted)]">{{ t('sandbox.interval') }}</p>
            <p class="text-lg font-mono font-semibold text-[var(--text-primary)]">
              {{ detailSim.interval_seconds }}s
            </p>
          </UCard>
          <UCard>
            <p class="text-xs text-[var(--text-muted)]">{{ t('sandbox.lastValue') }}</p>
            <p class="text-lg font-mono font-semibold text-[var(--text-primary)]">
              {{ timeAgo(detailSim.last_value_at) }}
            </p>
          </UCard>
          <UCard>
            <p class="text-xs text-[var(--text-muted)]">{{ t('sandbox.speed') }}</p>
            <p class="text-lg font-mono font-semibold text-[var(--text-primary)]">
              {{ detailSim.speed_multiplier }}x
            </p>
          </UCard>
        </div>

        <!-- Variables -->
        <div class="space-y-3">
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('sandbox.variables') }}</h3>
          <div
            v-for="vp in detailSim.variable_patterns"
            :key="vp.variable_key"
            class="rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] p-4 flex items-center justify-between gap-4"
          >
            <div class="flex items-center gap-3 min-w-0">
              <div>
                <p class="text-sm font-mono font-medium text-[var(--text-primary)]">{{ vp.variable_key }}</p>
                <p class="text-xs text-[var(--text-muted)]">{{ vp.pattern }}</p>
              </div>
            </div>
            <VizSparkline
              :points="previewPoints(vp)"
              :label="vp.variable_key"
              :width="120"
              :height="32"
              color="var(--primary)"
            />
          </div>
        </div>

        <!-- View Device link -->
        <div v-if="detailSim.device_uid" class="pt-2">
          <router-link
            :to="`/devices`"
            class="text-sm text-[var(--primary)] hover:underline"
          >
            {{ t('sandbox.viewDevice') }} ({{ detailSim.device_uid }})
          </router-link>
        </div>
      </div>
    </template>

    <!-- Simulator cards list -->
    <template v-else>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="sim in simulators"
          :key="sim.id"
          class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 space-y-3 hover:border-[var(--primary)]/40 transition-colors cursor-pointer"
          @click="openDetail(sim)"
        >
          <!-- Header -->
          <div class="flex items-start justify-between gap-2">
            <div class="flex items-center gap-2 min-w-0">
              <span class="text-lg shrink-0">{{ templateEmoji(sim.template ? templates.find(t => t.id === sim.template)?.icon ?? 'wrench' : 'wrench') }}</span>
              <div class="min-w-0">
                <p class="text-sm font-semibold text-[var(--text-primary)] truncate">{{ sim.name }}</p>
              </div>
            </div>
            <div class="flex items-center gap-1.5 shrink-0">
              <UBadge :status="sim.is_active ? 'ok' : 'neutral'" :pulse="sim.is_active">
                {{ sim.is_active ? t('sandbox.running') : t('sandbox.stopped_status') }}
              </UBadge>
              <UBadge v-if="sim.speed_multiplier > 1" status="info">
                {{ sim.speed_multiplier }}x
              </UBadge>
            </div>
          </div>

          <!-- Stats -->
          <p class="text-xs text-[var(--text-muted)]">
            {{ formatNumber(sim.total_points_sent) }} {{ t('sandbox.pointsSent') }}
            <template v-if="sim.last_value_at">
              &middot; {{ t('sandbox.last') }}: {{ timeAgo(sim.last_value_at) }}
            </template>
          </p>

          <!-- Variable badges -->
          <div class="flex flex-wrap gap-1">
            <UBadge
              v-for="vp in sim.variable_patterns"
              :key="vp.variable_key"
              status="neutral"
            >
              {{ vp.variable_key }}: {{ vp.pattern }}
            </UBadge>
          </div>

          <!-- Simulated badge + controls -->
          <div class="flex items-center justify-between pt-1 border-t border-[var(--border)]">
            <UBadge status="info">{{ t('sandbox.simulated') }}</UBadge>
            <div class="flex items-center gap-1" @click.stop>
              <UButton
                v-if="!sim.is_active"
                variant="ghost"
                size="sm"
                @click="handleStart(sim)"
              >
                {{ t('sandbox.start') }}
              </UButton>
              <UButton
                v-else
                variant="ghost"
                size="sm"
                @click="handleStop(sim)"
              >
                {{ t('sandbox.stop') }}
              </UButton>
              <UButton variant="ghost" size="sm" @click="openEdit(sim)">
                {{ t('common.edit') }}
              </UButton>
              <UButton variant="ghost" size="sm" @click="confirmDelete(sim)">
                {{ t('common.delete') }}
              </UButton>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ───── Create / Edit Modal ───────────────────────────────────────── -->
    <UModal
      :open="modalOpen"
      size="lg"
      :title="modalMode === 'create' ? t('sandbox.createTitle') : t('sandbox.editTitle')"
      @close="modalOpen = false"
    >
      <div class="flex flex-col max-h-[70vh]">
        <!-- Step indicator -->
        <div class="flex items-center gap-2 px-1 pb-4 border-b border-[var(--border)] shrink-0">
          <button
            v-for="step in (modalMode === 'edit' ? [2, 3] : [1, 2, 3])"
            :key="step"
            :class="[
              'flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors',
              modalStep === step
                ? 'bg-[var(--primary)]/15 text-[var(--primary)]'
                : modalStep > step
                  ? 'text-[var(--text-muted)]'
                  : 'text-[var(--text-muted)]/50',
            ]"
            @click="modalStep = step"
          >
            <span class="w-5 h-5 rounded-full border flex items-center justify-center text-[10px] font-bold"
              :class="modalStep >= step ? 'border-[var(--primary)] text-[var(--primary)]' : 'border-[var(--border)]'"
            >
              {{ step }}
            </span>
            {{
              step === 1
                ? t('sandbox.stepTemplate')
                : step === 2
                  ? t('sandbox.stepVariables')
                  : t('sandbox.stepSettings')
            }}
          </button>
        </div>

        <!-- Scrollable body -->
        <div class="flex-1 overflow-y-auto py-4 space-y-4 min-h-0">

          <!-- STEP 1: Template selection -->
          <template v-if="modalStep === 1">
            <p class="text-sm text-[var(--text-muted)]">{{ t('sandbox.chooseTemplate') }}</p>
            <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
              <button
                v-for="tmpl in templates"
                :key="tmpl.id"
                :class="[
                  'text-left rounded-lg border p-4 transition-all',
                  selectedTemplate === tmpl.id
                    ? 'border-[var(--primary)] bg-[var(--primary)]/5'
                    : 'border-[var(--border)] bg-[var(--bg-surface)] hover:border-[var(--primary)]/40',
                ]"
                @click="selectTemplate(tmpl)"
              >
                <span class="text-2xl">{{ templateEmoji(tmpl.icon) }}</span>
                <p class="text-sm font-medium text-[var(--text-primary)] mt-2">{{ tmpl.name }}</p>
                <p class="text-xs text-[var(--text-muted)] mt-0.5">{{ tmpl.description }}</p>
                <p class="text-xs text-[var(--text-muted)] mt-1 opacity-60">
                  {{ tmpl.variable_patterns.length }} {{ t('sandbox.variablesCount') }}
                </p>
              </button>
            </div>
          </template>

          <!-- STEP 2: Configure Variables -->
          <template v-if="modalStep === 2">
            <div class="space-y-3">
              <div
                v-for="(vp, idx) in formVariables"
                :key="idx"
                class="rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] overflow-hidden"
              >
                <!-- Variable header (always visible) -->
                <button
                  class="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-[var(--bg-raised)] transition-colors"
                  @click="toggleVarExpand(idx)"
                >
                  <div class="flex items-center gap-2 min-w-0">
                    <span class="text-xs font-mono text-[var(--text-muted)]">#{{ idx + 1 }}</span>
                    <span class="text-sm font-medium text-[var(--text-primary)] truncate">
                      {{ vp.variable_key || t('sandbox.untitledVar') }}
                    </span>
                    <UBadge status="neutral">{{ vp.pattern }}</UBadge>
                  </div>
                  <div class="flex items-center gap-1">
                    <!-- Reorder buttons -->
                    <button
                      v-if="idx > 0"
                      class="p-1 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                      @click.stop="moveVariable(idx, -1)"
                      :title="t('sandbox.moveUp')"
                    >
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 15.75l7.5-7.5 7.5 7.5" /></svg>
                    </button>
                    <button
                      v-if="idx < formVariables.length - 1"
                      class="p-1 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                      @click.stop="moveVariable(idx, 1)"
                      :title="t('sandbox.moveDown')"
                    >
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" /></svg>
                    </button>
                    <button
                      class="p-1 text-[var(--status-bad)] hover:text-[var(--status-bad)]"
                      @click.stop="removeVariable(idx)"
                      :title="t('sandbox.removeVar')"
                    >
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                    <svg
                      :class="['w-4 h-4 text-[var(--text-muted)] transition-transform', expandedVarIdx === idx ? 'rotate-180' : '']"
                      fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"
                    ><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" /></svg>
                  </div>
                </button>

                <!-- Expanded config -->
                <div v-if="expandedVarIdx === idx" class="px-4 pb-4 space-y-3 border-t border-[var(--border)]">
                  <div class="grid grid-cols-2 gap-3 pt-3">
                    <UInput
                      :modelValue="vp.variable_key"
                      @update:modelValue="(v: string) => (vp.variable_key = v)"
                      :label="t('sandbox.variableKey')"
                      :placeholder="t('sandbox.variableKeyPlaceholder')"
                    />
                    <USelect
                      :modelValue="vp.pattern"
                      @update:modelValue="(v: string) => onPatternChange(idx, v)"
                      :label="t('sandbox.patternType')"
                      :options="patternSelectOptions"
                    />
                  </div>

                  <!-- Pattern-specific config -->
                  <div class="space-y-3">
                    <!-- Sine -->
                    <template v-if="vp.pattern === 'sine'">
                      <div class="grid grid-cols-2 gap-3">
                        <UInput :modelValue="String(vp.config.min ?? 0)" @update:modelValue="(v: string) => (vp.config.min = Number(v))" :label="t('sandbox.configMin')" type="number" />
                        <UInput :modelValue="String(vp.config.max ?? 100)" @update:modelValue="(v: string) => (vp.config.max = Number(v))" :label="t('sandbox.configMax')" type="number" />
                      </div>
                      <div class="space-y-1">
                        <label class="text-xs font-medium text-[var(--text-muted)]">{{ t('sandbox.configPeriod') }}: {{ vp.config.period ?? 60 }}s</label>
                        <input
                          type="range"
                          min="10"
                          max="86400"
                          :value="vp.config.period ?? 60"
                          @input="(e: Event) => (vp.config.period = Number((e.target as HTMLInputElement).value))"
                          class="w-full accent-[var(--primary)]"
                        />
                        <div class="flex justify-between text-[10px] text-[var(--text-muted)]">
                          <span>10s</span><span>24h</span>
                        </div>
                      </div>
                      <UInput :modelValue="String(vp.config.phase_offset ?? 0)" @update:modelValue="(v: string) => (vp.config.phase_offset = Number(v))" :label="t('sandbox.configPhaseOffset')" type="number" />
                    </template>

                    <!-- Random Walk -->
                    <template v-if="vp.pattern === 'random_walk'">
                      <div class="grid grid-cols-2 gap-3">
                        <UInput :modelValue="String(vp.config.center ?? 50)" @update:modelValue="(v: string) => (vp.config.center = Number(v))" :label="t('sandbox.configCenter')" type="number" />
                        <UInput :modelValue="String(vp.config.volatility ?? 5)" @update:modelValue="(v: string) => (vp.config.volatility = Number(v))" :label="t('sandbox.configVolatility')" type="number" />
                      </div>
                      <div class="grid grid-cols-2 gap-3">
                        <UInput :modelValue="String(vp.config.min_bound ?? 0)" @update:modelValue="(v: string) => (vp.config.min_bound = Number(v))" :label="t('sandbox.configMinBound')" type="number" />
                        <UInput :modelValue="String(vp.config.max_bound ?? 100)" @update:modelValue="(v: string) => (vp.config.max_bound = Number(v))" :label="t('sandbox.configMaxBound')" type="number" />
                      </div>
                    </template>

                    <!-- Step -->
                    <template v-if="vp.pattern === 'step'">
                      <UInput :modelValue="String(vp.config.values ?? '0,50,100')" @update:modelValue="(v: string) => (vp.config.values = v)" :label="t('sandbox.configValues')" :placeholder="t('sandbox.configValuesPlaceholder')" />
                      <UInput :modelValue="String(vp.config.interval ?? 5)" @update:modelValue="(v: string) => (vp.config.interval = Number(v))" :label="t('sandbox.configStepInterval')" type="number" />
                    </template>

                    <!-- Ramp -->
                    <template v-if="vp.pattern === 'ramp'">
                      <div class="grid grid-cols-2 gap-3">
                        <UInput :modelValue="String(vp.config.start ?? 0)" @update:modelValue="(v: string) => (vp.config.start = Number(v))" :label="t('sandbox.configStart')" type="number" />
                        <UInput :modelValue="String(vp.config.end ?? 100)" @update:modelValue="(v: string) => (vp.config.end = Number(v))" :label="t('sandbox.configEnd')" type="number" />
                      </div>
                      <UInput :modelValue="String(vp.config.duration ?? 30)" @update:modelValue="(v: string) => (vp.config.duration = Number(v))" :label="t('sandbox.configDuration')" type="number" />
                      <UToggle :modelValue="(vp.config.loop as boolean) ?? true" @update:modelValue="(v: boolean) => (vp.config.loop = v)" :label="t('sandbox.configLoop')" />
                    </template>

                    <!-- Counter -->
                    <template v-if="vp.pattern === 'counter'">
                      <div class="grid grid-cols-3 gap-3">
                        <UInput :modelValue="String(vp.config.start ?? 0)" @update:modelValue="(v: string) => (vp.config.start = Number(v))" :label="t('sandbox.configStart')" type="number" />
                        <UInput :modelValue="String(vp.config.increment ?? 1)" @update:modelValue="(v: string) => (vp.config.increment = Number(v))" :label="t('sandbox.configIncrement')" type="number" />
                        <UInput :modelValue="String(vp.config.reset_at ?? 1000)" @update:modelValue="(v: string) => (vp.config.reset_at = Number(v))" :label="t('sandbox.configResetAt')" type="number" />
                      </div>
                    </template>

                    <!-- GPS Track -->
                    <template v-if="vp.pattern === 'gps_track'">
                      <UInput :modelValue="String(vp.config.waypoints ?? '')" @update:modelValue="(v: string) => (vp.config.waypoints = v)" :label="t('sandbox.configWaypoints')" :placeholder="t('sandbox.configWaypointsPlaceholder')" />
                    </template>

                    <!-- Noise -->
                    <template v-if="vp.pattern === 'noise'">
                      <div class="grid grid-cols-2 gap-3">
                        <UInput :modelValue="String(vp.config.center ?? 50)" @update:modelValue="(v: string) => (vp.config.center = Number(v))" :label="t('sandbox.configCenter')" type="number" />
                        <UInput :modelValue="String(vp.config.amplitude ?? 10)" @update:modelValue="(v: string) => (vp.config.amplitude = Number(v))" :label="t('sandbox.configAmplitude')" type="number" />
                      </div>
                    </template>

                    <!-- Formula -->
                    <template v-if="vp.pattern === 'formula'">
                      <UInput :modelValue="String(vp.config.expression ?? '')" @update:modelValue="(v: string) => (vp.config.expression = v)" :label="t('sandbox.configExpression')" :placeholder="t('sandbox.configExpressionPlaceholder')" />
                      <p class="text-xs text-[var(--text-muted)]">{{ t('sandbox.formulaHelp') }}</p>
                    </template>

                    <!-- CSV Replay -->
                    <template v-if="vp.pattern === 'csv_replay'">
                      <p class="text-xs text-[var(--text-muted)]">{{ t('sandbox.csvHelp') }}</p>
                      <UToggle :modelValue="(vp.config.loop as boolean) ?? true" @update:modelValue="(v: boolean) => (vp.config.loop = v)" :label="t('sandbox.configLoop')" />
                    </template>

                    <!-- Manual -->
                    <template v-if="vp.pattern === 'manual'">
                      <UInput :modelValue="String(vp.config.initial_value ?? 0)" @update:modelValue="(v: string) => (vp.config.initial_value = Number(v))" :label="t('sandbox.configInitialValue')" type="number" />
                      <p class="text-xs text-[var(--text-muted)]">{{ t('sandbox.manualHelp') }}</p>
                    </template>
                  </div>

                  <!-- Live Preview sparkline -->
                  <div class="pt-2 border-t border-[var(--border)]">
                    <p class="text-xs text-[var(--text-muted)] mb-1">{{ t('sandbox.livePreview') }}</p>
                    <div class="bg-[var(--bg-base)] rounded-lg p-2">
                      <VizSparkline
                        :points="previewPoints(vp)"
                        :label="vp.variable_key || 'preview'"
                        :width="400"
                        :height="48"
                        color="var(--primary)"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <button
                class="w-full flex items-center justify-center gap-1.5 py-2.5 rounded-lg border border-dashed border-[var(--border)] text-sm text-[var(--text-muted)] hover:border-[var(--primary)] hover:text-[var(--primary)] transition-colors"
                @click="addVariable"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
                {{ t('sandbox.addVariable') }}
              </button>
            </div>
          </template>

          <!-- STEP 3: Settings -->
          <template v-if="modalStep === 3">
            <div class="space-y-4">
              <UInput
                :modelValue="formName"
                @update:modelValue="(v: string) => (formName = v)"
                :label="t('sandbox.name')"
                :placeholder="t('sandbox.namePlaceholder')"
              />
              <UInput
                :modelValue="formDescription"
                @update:modelValue="(v: string) => (formDescription = v)"
                :label="t('sandbox.description')"
                :placeholder="t('sandbox.descriptionPlaceholder')"
              />

              <!-- Interval slider -->
              <div class="space-y-1">
                <label class="text-xs font-medium text-[var(--text-muted)]">{{ t('sandbox.intervalLabel') }}: {{ formInterval }}s</label>
                <input
                  type="range"
                  min="1"
                  max="60"
                  :value="formInterval"
                  @input="(e: Event) => (formInterval = Number((e.target as HTMLInputElement).value))"
                  class="w-full accent-[var(--primary)]"
                />
                <div class="flex justify-between text-[10px] text-[var(--text-muted)]">
                  <span>1s</span><span>60s</span>
                </div>
              </div>

              <!-- Speed radio -->
              <div class="space-y-1">
                <label class="text-xs font-medium text-[var(--text-muted)]">{{ t('sandbox.speedLabel') }}</label>
                <div class="flex gap-2">
                  <button
                    v-for="sp in [1, 2, 10, 100]"
                    :key="sp"
                    :class="[
                      'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border',
                      formSpeed === sp
                        ? 'bg-[var(--primary)]/15 text-[var(--primary)] border-[var(--primary)]/30'
                        : 'bg-[var(--bg-surface)] text-[var(--text-muted)] border-[var(--border)] hover:border-[var(--primary)]/40',
                    ]"
                    @click="formSpeed = sp"
                  >
                    {{ sp }}x
                  </button>
                </div>
              </div>

              <!-- Virtual device toggle -->
              <UToggle
                :modelValue="formVirtualDevice"
                @update:modelValue="(v: boolean) => (formVirtualDevice = v)"
                :label="t('sandbox.virtualDevice')"
              />
              <p class="text-xs text-[var(--text-muted)] -mt-2">{{ t('sandbox.virtualDeviceHelp') }}</p>

              <template v-if="!formVirtualDevice">
                <UInput
                  :modelValue="formDeviceUid"
                  @update:modelValue="(v: string) => (formDeviceUid = v)"
                  :label="t('sandbox.existingDevice')"
                  :placeholder="t('sandbox.existingDevicePlaceholder')"
                />
              </template>

              <!-- Auto-start toggle (create only) -->
              <UToggle
                v-if="modalMode === 'create'"
                :modelValue="formAutoStart"
                @update:modelValue="(v: boolean) => (formAutoStart = v)"
                :label="t('sandbox.autoStart')"
              />
            </div>
          </template>
        </div>

        <!-- Sticky footer -->
        <div class="flex items-center justify-between pt-4 border-t border-[var(--border)] shrink-0">
          <div>
            <UButton
              v-if="modalStep > 1 && modalMode === 'create'"
              variant="ghost"
              size="sm"
              @click="modalStep--"
            >
              {{ t('sandbox.back') }}
            </UButton>
            <UButton
              v-if="modalStep > 2 && modalMode === 'edit'"
              variant="ghost"
              size="sm"
              @click="modalStep--"
            >
              {{ t('sandbox.back') }}
            </UButton>
          </div>
          <div class="flex items-center gap-2">
            <UButton variant="ghost" size="sm" @click="modalOpen = false">
              {{ t('common.cancel') }}
            </UButton>
            <UButton
              v-if="modalStep === 1"
              variant="primary"
              size="sm"
              :disabled="!canProceedStep1"
              @click="modalStep = 2"
            >
              {{ t('sandbox.next') }}
            </UButton>
            <UButton
              v-else-if="modalStep === 2"
              variant="primary"
              size="sm"
              :disabled="!canProceedStep2"
              @click="modalStep = 3"
            >
              {{ t('sandbox.next') }}
            </UButton>
            <UButton
              v-else
              variant="primary"
              size="sm"
              :loading="saving"
              :disabled="!canCreate"
              @click="handleSave"
            >
              {{ modalMode === 'create' ? t('sandbox.createBtn') : t('common.save') }}
            </UButton>
          </div>
        </div>
      </div>
    </UModal>

    <!-- Delete confirmation modal -->
    <UModal
      :open="deleteConfirmOpen"
      size="sm"
      :title="t('sandbox.deleteTitle')"
      @close="deleteConfirmOpen = false"
    >
      <p class="text-sm text-[var(--text-muted)] py-2">
        {{ t('sandbox.deleteConfirm', { name: deleteTarget?.name ?? '' }) }}
      </p>
      <div class="flex justify-end gap-2 pt-4 border-t border-[var(--border)]">
        <UButton variant="ghost" size="sm" @click="deleteConfirmOpen = false">
          {{ t('common.cancel') }}
        </UButton>
        <UButton variant="primary" size="sm" :loading="deleting" @click="handleDelete">
          {{ t('common.delete') }}
        </UButton>
      </div>
    </UModal>
  </div>
</template>
