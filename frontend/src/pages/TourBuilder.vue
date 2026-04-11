<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../lib/api";
import { useTourStore } from "../stores/tour";
import type { TourStep, TourDefinition, TourAction, TooltipPosition } from "../lib/tour-engine";
import UButton from "../components/ui/UButton.vue";
import UModal from "../components/ui/UModal.vue";
import UEmpty from "../components/ui/UEmpty.vue";
import USkeleton from "../components/ui/USkeleton.vue";
import UBadge from "../components/ui/UBadge.vue";
import UToggle from "../components/ui/UToggle.vue";
import USelect from "../components/ui/USelect.vue";
import UInfoTooltip from "../components/ui/UInfoTooltip.vue";
import { useToastStore } from "../stores/toast";

const { t, tm, rt } = useI18n();
const tourStore = useTourStore();
const toastStore = useToastStore();

/* ---- Types ---- */
interface TourSummary {
  id: number;
  name: string;
  description: string | null;
  step_count: number;
  is_public: boolean;
  category: string;
  created_at: string;
  updated_at: string | null;
}

interface TourFull {
  id: number;
  org_id: number;
  owner_id: number;
  name: string;
  description: string | null;
  steps: StepForm[];
  is_public: boolean;
  public_token: string | null;
  category: string;
  created_at: string;
  updated_at: string | null;
}

interface StepForm {
  id: string;
  page: string;
  target: string;
  action: string;
  title: string;
  text: string;
  position: string;
  delay: number | null;
  duration: number | null;
}

/* ---- State ---- */
const loading = ref(true);
const tours = ref<TourSummary[]>([]);
const showEditor = ref(false);
const editingTourId = ref<number | null>(null);
const saving = ref(false);

// Editor form
const tourName = ref("");
const tourDescription = ref("");
const tourAutoplay = ref(true);
const tourAutoplayInterval = ref(5);
const steps = ref<StepForm[]>([]);

// Drag state
const dragIndex = ref<number | null>(null);

/* ---- Route options for step page selector ---- */
const routeOptions = [
  { value: "/", label: "Dashboard" },
  { value: "/devices", label: "Devices" },
  { value: "/dashboards", label: "Dashboards" },
  { value: "/variables", label: "Variables" },
  { value: "/entities", label: "Entities" },
  { value: "/automations", label: "Automations" },
  { value: "/alerts", label: "Alerts" },
  { value: "/events", label: "Events" },
  { value: "/effects", label: "Effects" },
  { value: "/webhooks", label: "Webhooks" },
  { value: "/flow-editor", label: "System Map" },
  { value: "/reports", label: "Reports" },
  { value: "/settings", label: "Settings" },
  { value: "/audit", label: "Audit Log" },
  { value: "/custom-api", label: "Custom API" },
  { value: "/hardware", label: "Hardware" },
  { value: "/plugins", label: "Plugins" },
  { value: "/observability", label: "Observability" },
  { value: "/trace-timeline", label: "Trace Timeline" },
  { value: "/system-health", label: "System Health" },
  { value: "/email-templates", label: "Email Templates" },
];

const actionOptions = [
  { value: "spotlight", label: "Spotlight" },
  { value: "spotlight+pulse", label: "Spotlight + Pulse" },
  { value: "zoom", label: "Zoom" },
  { value: "info", label: "Info (no target)" },
];

const positionOptions = [
  { value: "top", label: "Top" },
  { value: "bottom", label: "Bottom" },
  { value: "left", label: "Left" },
  { value: "right", label: "Right" },
  { value: "center", label: "Center" },
];

/* ---- Expanded steps tracking ---- */
const expandedSteps = ref<Set<number>>(new Set());

function toggleStep(index: number) {
  const next = new Set(expandedSteps.value);
  if (next.has(index)) next.delete(index);
  else next.add(index);
  expandedSteps.value = next;
}

/* ---- API ---- */
async function fetchTours() {
  loading.value = true;
  try {
    tours.value = await apiFetch<TourSummary[]>("/api/v1/tours");
  } catch (err: any) {
    console.error("[TourBuilder] fetchTours failed:", err);
    toastStore.addToast(t("tourBuilder.loadError"), "error");
  } finally {
    loading.value = false;
  }
}

async function loadTour(id: number) {
  try {
    const tour = await apiFetch<TourFull>(`/api/v1/tours/${id}`);
    editingTourId.value = id;
    tourName.value = tour.name;
    tourDescription.value = tour.description || "";
    tourAutoplay.value = true;
    tourAutoplayInterval.value = 5;
    steps.value = tour.steps.map((s) => ({
      id: s.id || generateStepId(),
      page: s.page || "/",
      target: s.target || "",
      action: s.action || "spotlight",
      title: s.title || "",
      text: s.text || "",
      position: s.position || "bottom",
      delay: s.delay ?? null,
      duration: s.duration ?? null,
    }));
    expandedSteps.value = new Set();
    showEditor.value = true;
  } catch {
    toastStore.addToast(t("tourBuilder.loadError"), "error");
  }
}

function newTour() {
  editingTourId.value = null;
  tourName.value = "";
  tourDescription.value = "";
  tourAutoplay.value = true;
  tourAutoplayInterval.value = 5;
  steps.value = [];
  expandedSteps.value = new Set();
  showEditor.value = true;
}

async function saveTour() {
  if (!tourName.value.trim()) {
    toastStore.addToast(t("tourBuilder.nameRequired"), "error");
    return;
  }

  saving.value = true;
  const body = {
    name: tourName.value.trim(),
    description: tourDescription.value.trim() || null,
    steps: steps.value.map((s) => ({
      id: s.id,
      page: s.page || null,
      target: s.target || null,
      action: s.action,
      title: s.title,
      text: s.text,
      position: s.position,
      delay: s.delay,
      duration: s.duration,
    })),
    is_public: false,
    category: "custom",
  };

  try {
    if (editingTourId.value) {
      await apiFetch(`/api/v1/tours/${editingTourId.value}`, {
        method: "PUT",
        body: JSON.stringify(body),
      });
      toastStore.addToast(t("tourBuilder.saved"), "success");
    } else {
      await apiFetch("/api/v1/tours", {
        method: "POST",
        body: JSON.stringify(body),
      });
      toastStore.addToast(t("tourBuilder.created"), "success");
    }
    showEditor.value = false;
    await fetchTours();
    syncCustomToursToStore();
  } catch (err: any) {
    console.error("[TourBuilder] saveTour failed:", err);
    toastStore.addToast(t("tourBuilder.saveError"), "error");
  } finally {
    saving.value = false;
  }
}

async function deleteTour(id: number) {
  try {
    await apiFetch(`/api/v1/tours/${id}`, { method: "DELETE" });
    toastStore.addToast(t("tourBuilder.deleted"), "success");
    await fetchTours();
    tourStore.unregisterTour(`custom-${id}`);
  } catch {
    toastStore.addToast(t("tourBuilder.deleteError"), "error");
  }
}

async function shareTour(id: number) {
  try {
    const res = await apiFetch<{ public_token: string; url: string }>(
      `/api/v1/tours/${id}/share`,
      { method: "POST" }
    );
    const fullUrl = `${window.location.origin}${res.url}`;
    await navigator.clipboard.writeText(fullUrl);
    toastStore.addToast(t("tourBuilder.linkCopied"), "success");
    await fetchTours();
  } catch {
    toastStore.addToast(t("tourBuilder.shareError"), "error");
  }
}

/* ---- Tour Store integration ---- */
async function syncCustomToursToStore() {
  try {
    const allTours = await apiFetch<TourFull[]>("/api/v1/tours");
    // We can't iterate full details from list, but we can register summaries
    for (const tour of allTours) {
      const full = await apiFetch<TourFull>(`/api/v1/tours/${tour.id}`);
      const def: TourDefinition = {
        id: `custom-${full.id}`,
        name: full.name,
        description: full.description || "",
        steps: full.steps.map((s) => ({
          id: s.id,
          page: s.page || undefined,
          target: s.target || undefined,
          action: (s.action || "spotlight") as TourAction,
          title: s.title,
          text: s.text,
          position: (s.position || "bottom") as TooltipPosition,
          delay: s.delay ?? undefined,
          duration: s.duration ?? undefined,
        })),
        category: "custom",
        autoplay: true,
        autoplayInterval: 5000,
      };
      tourStore.registerTour(def);
    }
  } catch {
    // Silent fail on sync
  }
}

/* ---- Preview tour ---- */
async function previewTour(id: number) {
  try {
    const full = await apiFetch<TourFull>(`/api/v1/tours/${id}`);
    const def: TourDefinition = {
      id: `custom-${full.id}`,
      name: full.name,
      description: full.description || "",
      steps: full.steps.map((s) => ({
        id: s.id,
        page: s.page || undefined,
        target: s.target || undefined,
        action: (s.action || "spotlight") as TourAction,
        title: s.title,
        text: s.text,
        position: (s.position || "bottom") as TooltipPosition,
        delay: s.delay ?? undefined,
        duration: s.duration ?? undefined,
      })),
      category: "custom",
      autoplay: true,
      autoplayInterval: 5000,
    };
    tourStore.registerTour(def);
    tourStore.start(def.id);
  } catch {
    toastStore.addToast(t("tourBuilder.loadError"), "error");
  }
}

function previewCurrentTour() {
  if (steps.value.length === 0) {
    toastStore.addToast(t("tourBuilder.noSteps"), "error");
    return;
  }
  const def: TourDefinition = {
    id: "preview-tour",
    name: tourName.value || "Preview",
    description: tourDescription.value || "",
    steps: steps.value.map((s) => ({
      id: s.id,
      page: s.page || undefined,
      target: s.target || undefined,
      action: (s.action || "spotlight") as TourAction,
      title: s.title,
      text: s.text,
      position: (s.position || "bottom") as TooltipPosition,
      delay: s.delay ?? undefined,
      duration: s.duration ?? undefined,
    })),
    category: "custom",
    autoplay: tourAutoplay.value,
    autoplayInterval: tourAutoplayInterval.value * 1000,
  };
  tourStore.registerTour(def);
  showEditor.value = false;
  tourStore.start(def.id);
}

/* ---- Step management ---- */
function generateStepId(): string {
  return `step-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
}

function addStep() {
  const newStep: StepForm = {
    id: generateStepId(),
    page: "/",
    target: "",
    action: "spotlight",
    title: "",
    text: "",
    position: "bottom",
    delay: null,
    duration: null,
  };
  steps.value.push(newStep);
  expandedSteps.value = new Set([...expandedSteps.value, steps.value.length - 1]);
}

function duplicateStep(index: number) {
  const copy = { ...steps.value[index], id: generateStepId() };
  steps.value.splice(index + 1, 0, copy);
}

function removeStep(index: number) {
  steps.value.splice(index, 1);
  expandedSteps.value.delete(index);
}

function moveStep(index: number, direction: -1 | 1) {
  const newIndex = index + direction;
  if (newIndex < 0 || newIndex >= steps.value.length) return;
  const temp = steps.value[index];
  steps.value[index] = steps.value[newIndex];
  steps.value[newIndex] = temp;
}

/* ---- Drag and drop ---- */
function onDragStart(index: number, event: DragEvent) {
  dragIndex.value = index;
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = "move";
  }
}

function onDragOver(index: number, event: DragEvent) {
  event.preventDefault();
  if (dragIndex.value === null || dragIndex.value === index) return;
  const item = steps.value.splice(dragIndex.value, 1)[0];
  steps.value.splice(index, 0, item);
  dragIndex.value = index;
}

function onDragEnd() {
  dragIndex.value = null;
}

/* ---- Helpers ---- */
function relativeTime(dateStr: string | null): string {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return t("tourBuilder.justNow");
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

/* ---- Confirm delete ---- */
const confirmDeleteId = ref<number | null>(null);

function confirmDelete(id: number) {
  confirmDeleteId.value = id;
}

async function executeDelete() {
  if (confirmDeleteId.value !== null) {
    await deleteTour(confirmDeleteId.value);
    confirmDeleteId.value = null;
  }
}

/* ---- Init ---- */
onMounted(() => {
  fetchTours();
  syncCustomToursToStore();
});
</script>

<template>
  <div class="tour-builder-page">

    <!-- Header -->
    <div class="page-header">
      <div>
        <div class="flex items-center">
          <h1 class="page-title">{{ t('nav.tourBuilder') }}</h1>
          <UInfoTooltip
            :title="t('tourBuilder.infoTitle')"
            :items="[t('tourBuilder.infoItem1'), t('tourBuilder.infoItem2'), t('tourBuilder.infoItem3')]"
          />
        </div>
        <p class="page-sub">{{ t('tourBuilder.subtitle') }}</p>
      </div>
      <UButton
        icon="M12 4.5v15m7.5-7.5h-15"
        @click="newTour"
      >
        {{ t('tourBuilder.newTour') }}
      </UButton>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <USkeleton v-for="i in 3" :key="i" class="h-36" />
    </div>

    <!-- Empty state -->
    <UEmpty
      v-else-if="!tours.length"
      :title="t('tourBuilder.emptyTitle')"
      :description="t('tourBuilder.emptyDescription')"
      icon="M4.26 10.147a60.438 60.438 0 00-.491 6.347A48.62 48.62 0 0112 20.904a48.62 48.62 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.636 50.636 0 00-2.658-.813A59.906 59.906 0 0112 3.493a59.903 59.903 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5"
    >
      <UButton @click="newTour">{{ t('tourBuilder.createFirst') }}</UButton>
    </UEmpty>

    <!-- Tour list -->
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="tour in tours"
        :key="tour.id"
        class="tour-card"
      >
        <div class="tour-card-header">
          <div class="tour-card-icon">
            <svg class="h-5 w-5 text-[var(--primary)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4.26 10.147a60.438 60.438 0 00-.491 6.347A48.62 48.62 0 0112 20.904a48.62 48.62 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.636 50.636 0 00-2.658-.813A59.906 59.906 0 0112 3.493a59.903 59.903 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0112 13.489a50.702 50.702 0 017.74-3.342" />
            </svg>
          </div>
          <div class="tour-card-badges">
            <UBadge v-if="tour.is_public" color="green" size="xs">{{ t('tourBuilder.public') }}</UBadge>
            <UBadge v-else color="neutral" size="xs">{{ t('tourBuilder.private') }}</UBadge>
            <UBadge color="amber" size="xs">{{ tour.step_count }} {{ t('tourBuilder.steps') }}</UBadge>
          </div>
        </div>
        <h3 class="tour-card-name">{{ tour.name }}</h3>
        <p v-if="tour.description" class="tour-card-desc">{{ tour.description }}</p>
        <div class="tour-card-footer">
          <span class="tour-time">{{ relativeTime(tour.created_at) }}</span>
        </div>
        <div class="tour-card-actions">
          <button class="card-action-btn" @click="previewTour(tour.id)" :title="t('tourBuilder.play')">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 010 1.972l-11.54 6.347a1.125 1.125 0 01-1.667-.986V5.653z" />
            </svg>
          </button>
          <button class="card-action-btn" @click="loadTour(tour.id)" :title="t('common.edit')">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
            </svg>
          </button>
          <button class="card-action-btn" @click="shareTour(tour.id)" :title="t('tourBuilder.share')">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" />
            </svg>
          </button>
          <button class="card-action-btn card-action-danger" @click="confirmDelete(tour.id)" :title="t('common.delete')">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Editor Modal -->
    <UModal
      :open="showEditor"
      size="lg"
      :title="editingTourId ? t('tourBuilder.editTour') : t('tourBuilder.newTour')"
      @close="showEditor = false"
    >
      <div class="space-y-6">

        <!-- Sprint 8 R4 Bucket C F18: Inline helper panel explaining the 3
             main concepts of the tour builder to reduce the "unübersichtlich"
             feeling the user reported. Shows once per modal open. -->
        <div class="tour-builder-helper">
          <svg class="h-5 w-5 shrink-0 mt-0.5 text-[var(--primary)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z" />
          </svg>
          <div class="min-w-0">
            <p class="text-sm font-semibold text-[var(--text-primary)]">{{ t('tourBuilder.helperTitle') }}</p>
            <ul class="mt-1 space-y-0.5 text-xs text-[var(--text-muted)] list-disc list-inside">
              <li>{{ t('tourBuilder.helperBullet1') }}</li>
              <li>{{ t('tourBuilder.helperBullet2') }}</li>
              <li>{{ t('tourBuilder.helperBullet3') }}</li>
            </ul>
          </div>
        </div>

        <!-- Tour Settings -->
        <div class="tour-settings-section">
          <h3 class="section-label">{{ t('tourBuilder.tourSettings') }}</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="field">
              <label class="field-label">{{ t('tourBuilder.tourName') }}</label>
              <input
                v-model="tourName"
                class="field-input"
                :placeholder="t('tourBuilder.tourNamePlaceholder')"
                maxlength="100"
              />
            </div>
            <div class="field">
              <label class="field-label">{{ t('tourBuilder.category') }}</label>
              <input
                value="custom"
                class="field-input"
                disabled
              />
            </div>
          </div>
          <div class="field mt-3">
            <label class="field-label">{{ t('tourBuilder.description') }}</label>
            <textarea
              v-model="tourDescription"
              class="field-input min-h-[60px]"
              :placeholder="t('tourBuilder.descriptionPlaceholder')"
              rows="2"
            />
          </div>
          <div class="flex items-center gap-6 mt-3">
            <UToggle v-model="tourAutoplay" :label="t('tourBuilder.autoplay')" />
            <div v-if="tourAutoplay" class="flex items-center gap-2">
              <label class="text-xs text-[var(--text-muted)]">{{ t('tourBuilder.interval') }}</label>
              <input
                type="range"
                v-model.number="tourAutoplayInterval"
                min="3"
                max="10"
                class="w-24 accent-[var(--primary)]"
              />
              <span class="text-xs text-[var(--text-secondary)] tabular-nums">{{ tourAutoplayInterval }}s</span>
            </div>
          </div>
        </div>

        <!-- Steps -->
        <div class="steps-section">
          <div class="flex items-center justify-between mb-3">
            <h3 class="section-label mb-0">{{ t('tourBuilder.steps') }} ({{ steps.length }})</h3>
          </div>

          <div v-if="steps.length === 0" class="empty-steps">
            <p class="text-sm text-[var(--text-muted)]">{{ t('tourBuilder.noStepsYet') }}</p>
          </div>

          <div v-else class="steps-list">
            <div
              v-for="(step, index) in steps"
              :key="step.id"
              class="step-card"
              draggable="true"
              @dragstart="onDragStart(index, $event)"
              @dragover="onDragOver(index, $event)"
              @dragend="onDragEnd"
              :class="{ 'opacity-50': dragIndex === index }"
            >
              <!-- Step header (always visible) -->
              <div class="step-header" @click="toggleStep(index)">
                <div class="flex items-center gap-2">
                  <span class="drag-handle cursor-grab" title="Drag to reorder">
                    <svg class="h-4 w-4 text-[var(--text-muted)]" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                    </svg>
                  </span>
                  <span class="step-number">{{ index + 1 }}</span>
                  <span class="step-title-preview">
                    {{ step.title || t('tourBuilder.untitledStep') }}
                  </span>
                  <UBadge size="xs" color="neutral">{{ step.action }}</UBadge>
                  <UBadge v-if="step.page" size="xs" color="amber">{{ step.page }}</UBadge>
                </div>
                <div class="flex items-center gap-1">
                  <button class="step-btn" @click.stop="moveStep(index, -1)" :disabled="index === 0" :title="t('tourBuilder.moveUp')">
                    <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 15.75l7.5-7.5 7.5 7.5" /></svg>
                  </button>
                  <button class="step-btn" @click.stop="moveStep(index, 1)" :disabled="index === steps.length - 1" :title="t('tourBuilder.moveDown')">
                    <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" /></svg>
                  </button>
                  <button class="step-btn" @click.stop="duplicateStep(index)" :title="t('tourBuilder.duplicate')">
                    <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75" /></svg>
                  </button>
                  <button class="step-btn step-btn-danger" @click.stop="removeStep(index)" :title="t('common.delete')">
                    <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                  </button>
                  <svg
                    class="h-4 w-4 text-[var(--text-muted)] transition-transform"
                    :class="{ 'rotate-180': expandedSteps.has(index) }"
                    fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                  </svg>
                </div>
              </div>

              <!-- Step body (expandable) -->
              <Transition name="expand">
                <div v-if="expandedSteps.has(index)" class="step-body">
                  <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div class="field">
                      <label class="field-label">{{ t('tourBuilder.page') }}</label>
                      <USelect
                        v-model="step.page"
                        :options="routeOptions"
                        :placeholder="t('tourBuilder.selectPage')"
                      />
                    </div>
                    <div class="field">
                      <label class="field-label">{{ t('tourBuilder.action') }}</label>
                      <USelect
                        v-model="step.action"
                        :options="actionOptions"
                      />
                    </div>
                    <div class="field">
                      <label class="field-label">{{ t('tourBuilder.position') }}</label>
                      <USelect
                        v-model="step.position"
                        :options="positionOptions"
                      />
                    </div>
                  </div>

                  <div class="field mt-3">
                    <label class="field-label">{{ t('tourBuilder.targetSelector') }}</label>
                    <input
                      v-model="step.target"
                      class="field-input font-mono text-xs"
                      :placeholder="t('tourBuilder.targetPlaceholder')"
                    />
                  </div>

                  <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
                    <div class="field">
                      <label class="field-label">{{ t('tourBuilder.stepTitle') }}</label>
                      <input
                        v-model="step.title"
                        class="field-input"
                        :placeholder="t('tourBuilder.stepTitlePlaceholder')"
                      />
                    </div>
                    <div class="field">
                      <label class="field-label">{{ t('tourBuilder.duration') }}</label>
                      <div class="flex items-center gap-2">
                        <input
                          type="range"
                          v-model.number="step.duration"
                          min="2000"
                          max="15000"
                          step="500"
                          class="flex-1 accent-[var(--primary)]"
                        />
                        <span class="text-xs text-[var(--text-secondary)] tabular-nums w-10 text-right">
                          {{ step.duration ? (step.duration / 1000).toFixed(1) + 's' : 'auto' }}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div class="field mt-3">
                    <label class="field-label">{{ t('tourBuilder.stepText') }}</label>
                    <textarea
                      v-model="step.text"
                      class="field-input min-h-[60px]"
                      :placeholder="t('tourBuilder.stepTextPlaceholder')"
                      rows="2"
                    />
                  </div>
                </div>
              </Transition>
            </div>
          </div>

          <button class="add-step-btn" @click="addStep">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            {{ t('tourBuilder.addStep') }}
          </button>
        </div>
      </div>

      <!-- Footer -->
      <template #footer>
        <div class="flex items-center justify-between">
          <UButton variant="ghost" @click="previewCurrentTour" :disabled="steps.length === 0">
            <svg class="h-4 w-4 mr-1" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 010 1.972l-11.54 6.347a1.125 1.125 0 01-1.667-.986V5.653z" />
            </svg>
            {{ t('tourBuilder.preview') }}
          </UButton>
          <div class="flex gap-2">
            <UButton variant="secondary" @click="showEditor = false">{{ t('common.cancel') }}</UButton>
            <UButton @click="saveTour" :loading="saving">{{ t('common.save') }}</UButton>
          </div>
        </div>
      </template>
    </UModal>

    <!-- Delete confirm modal -->
    <UModal
      :open="confirmDeleteId !== null"
      size="sm"
      :title="t('tourBuilder.confirmDelete')"
      @close="confirmDeleteId = null"
    >
      <p class="text-sm text-[var(--text-secondary)]">{{ t('tourBuilder.confirmDeleteText') }}</p>
      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton variant="secondary" @click="confirmDeleteId = null">{{ t('common.cancel') }}</UButton>
          <UButton variant="danger" @click="executeDelete">{{ t('common.delete') }}</UButton>
        </div>
      </template>
    </UModal>

  </div>
</template>

<style scoped>
.tour-builder-page {
  padding: 1.5rem;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.page-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary);
  font-family: var(--font-display, "Satoshi", sans-serif);
}

.page-sub {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
}

/* Tour cards */
.tour-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  padding: 1rem;
  cursor: default;
  transition: border-color 0.15s, box-shadow 0.15s;
  position: relative;
}

.tour-card:hover {
  border-color: var(--primary);
  box-shadow: 0 0 0 1px var(--primary);
}

.tour-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.tour-card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
  background: var(--bg-raised);
}

.tour-card-badges {
  display: flex;
  gap: 0.25rem;
}

.tour-card-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.tour-card-desc {
  font-size: 0.75rem;
  color: var(--text-muted);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tour-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border);
}

.tour-time {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.tour-card-actions {
  display: flex;
  gap: 0.25rem;
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border);
}

.card-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 0.375rem;
  background: transparent;
  color: var(--text-muted);
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.15s;
}

.card-action-btn:hover {
  background: var(--bg-raised);
  color: var(--text-primary);
  border-color: var(--border);
}

.card-action-danger:hover {
  color: #ef4444;
  border-color: #ef4444;
  background: rgba(239, 68, 68, 0.08);
}

/* Editor sections */
.tour-settings-section,
.steps-section {
  background: var(--bg-raised);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  padding: 1rem;
}

/* Sprint 8 F18: inline helper panel at top of tour editor modal */
.tour-builder-helper {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  background: color-mix(in srgb, var(--primary) 6%, var(--bg-raised));
  border: 1px solid color-mix(in srgb, var(--primary) 25%, var(--border));
  border-radius: 0.5rem;
}

.section-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 0.75rem;
}

/* Fields */
.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.field-label {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

.field-input {
  background: var(--bg-base);
  border: 1px solid var(--border);
  border-radius: 0.375rem;
  padding: 0.5rem 0.75rem;
  color: var(--text-primary);
  font-size: 0.8rem;
  transition: border-color 0.15s;
}

.field-input:focus {
  outline: none;
  border-color: var(--primary);
}

.field-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Steps */
.steps-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.step-card {
  background: var(--bg-base);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  transition: border-color 0.15s;
}

.step-card:hover {
  border-color: var(--border-hover, var(--text-muted));
}

.step-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  gap: 0.5rem;
}

.step-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  border-radius: 50%;
  background: var(--primary);
  color: var(--text-invert);
  font-size: 0.65rem;
  font-weight: 700;
  flex-shrink: 0;
}

.step-title-preview {
  font-size: 0.8rem;
  color: var(--text-primary);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.step-body {
  padding: 0.75rem;
  border-top: 1px solid var(--border);
}

.step-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 0.25rem;
  background: transparent;
  color: var(--text-muted);
  border: none;
  cursor: pointer;
  transition: all 0.15s;
}

.step-btn:hover:not(:disabled) {
  background: var(--bg-raised);
  color: var(--text-primary);
}

.step-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.step-btn-danger:hover:not(:disabled) {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.08);
}

.add-step-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.625rem;
  border: 1px dashed var(--border);
  border-radius: 0.5rem;
  background: transparent;
  color: var(--text-muted);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.15s;
}

.add-step-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
  background: rgba(245, 166, 35, 0.05);
}

.empty-steps {
  text-align: center;
  padding: 1.5rem;
  border: 1px dashed var(--border);
  border-radius: 0.5rem;
  margin-bottom: 0.75rem;
}

/* Expand transition */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
  padding-top: 0;
  padding-bottom: 0;
}
</style>
