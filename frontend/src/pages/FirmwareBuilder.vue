<script setup lang="ts">
/**
 * Sprint 4 — Firmware Builder UI.
 *
 * Lists past firmware builds (for the current user), lets them kick off
 * a new build against any of their registered board profiles, and tails
 * the live log of the in-flight build via polling. When the build
 * finishes successfully a "Download .bin" button appears.
 */
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";

import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";
import UCard from "../components/ui/UCard.vue";
import UButton from "../components/ui/UButton.vue";
import UBadge from "../components/ui/UBadge.vue";
import UEmpty from "../components/ui/UEmpty.vue";
import USkeleton from "../components/ui/USkeleton.vue";
import UModal from "../components/ui/UModal.vue";

const { t } = useI18n();
const toast = useToastStore();

// ── Types ──────────────────────────────────────────────────────────────────

interface BoardProfile {
  id: number;
  name: string;
  chip: string;
  description: string | null;
  is_builtin: boolean;
}

interface FirmwareBuild {
  id: number;
  status: "queued" | "building" | "success" | "failed" | "cancelled";
  board_profile_id: number;
  device_id: number | null;
  pio_env: string;
  container_name: string | null;
  artifact_size_kb: number | null;
  artifact_filename: string | null;
  error_code: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  has_logs: boolean;
  // Sprint 7 — OTA linkage
  ota_rollout_id: number | null;
  ota_status: "pending" | "active" | "paused" | "completed" | "failed" | null;
}

// Sprint 7 — minimal device shape for the device selector modal
interface DeviceLite {
  id: number;
  device_uid: string;
  name: string | null;
  device_type: string;
  online: boolean;
}

// ── State ──────────────────────────────────────────────────────────────────

const boards = ref<BoardProfile[]>([]);
const builds = ref<FirmwareBuild[]>([]);
const selectedBoardId = ref<number | null>(null);
const loadingBoards = ref(true);
const loadingBuilds = ref(true);
const kicking = ref(false);
const error = ref<string | null>(null);

// Live log tail for a single selected build
const tailedBuildId = ref<number | null>(null);
const tailLogs = ref<string>("");
const tailLoading = ref(false);
let pollHandle: number | null = null;

// Sprint 7 — OTA push modal state
const otaBuildTarget = ref<FirmwareBuild | null>(null);
const otaDevices = ref<DeviceLite[]>([]);
const otaSelectedDeviceId = ref<number | null>(null);
const otaPushing = ref(false);
const otaDevicesLoading = ref(false);
const otaError = ref<string | null>(null);

// ── Loaders ────────────────────────────────────────────────────────────────

async function loadBoards(): Promise<void> {
  loadingBoards.value = true;
  try {
    boards.value = await apiFetch<BoardProfile[]>("/api/v1/hardware/boards");
    if (boards.value.length && selectedBoardId.value === null) {
      selectedBoardId.value = boards.value[0].id;
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load boards";
  } finally {
    loadingBoards.value = false;
  }
}

async function loadBuilds(): Promise<void> {
  loadingBuilds.value = true;
  try {
    builds.value = await apiFetch<FirmwareBuild[]>("/api/v1/firmware/builds?limit=50");
  } catch (e) {
    // Non-fatal: feature might be disabled, just show empty list
    builds.value = [];
    if (e instanceof Error && !e.message.includes("FEATURE_DISABLED")) {
      error.value = e.message;
    }
  } finally {
    loadingBuilds.value = false;
  }
}

// ── Actions ────────────────────────────────────────────────────────────────

async function handleKickoff(): Promise<void> {
  if (!selectedBoardId.value) return;
  kicking.value = true;
  try {
    const build = await apiFetch<FirmwareBuild>("/api/v1/firmware/build", {
      method: "POST",
      body: JSON.stringify({ board_profile_id: selectedBoardId.value }),
    });
    toast.addToast(t("firmware.queuedToast", { id: build.id }), "success");
    builds.value.unshift(build);
    tailedBuildId.value = build.id;
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Build failed to queue";
    toast.addToast(msg, "error");
  } finally {
    kicking.value = false;
  }
}

async function cancelBuild(build: FirmwareBuild): Promise<void> {
  try {
    const updated = await apiFetch<FirmwareBuild>(
      `/api/v1/firmware/builds/${build.id}/cancel`,
      { method: "POST" }
    );
    const idx = builds.value.findIndex((b) => b.id === build.id);
    if (idx >= 0) builds.value[idx] = updated;
    toast.addToast(t("firmware.cancelledToast"), "success");
  } catch (e) {
    toast.addToast(e instanceof Error ? e.message : "Cancel failed", "error");
  }
}

function downloadBin(build: FirmwareBuild): void {
  // Fetch download URL with authorization. Easiest route: use a hidden
  // link with the token in a header — but anchors can't set headers, so
  // we fetch the blob and use a temporary object URL.
  const token = localStorage.getItem("hubex_access_token");
  if (!token) return;
  fetch(`/api/v1/firmware/builds/${build.id}/download`, {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then((r) => r.blob())
    .then((blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = build.artifact_filename || `firmware-${build.id}.bin`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    })
    .catch((e) => toast.addToast(e.message || "Download failed", "error"));
}

// ── Sprint 7 — OTA push flow ──────────────────────────────────────────────

async function openOtaModal(build: FirmwareBuild): Promise<void> {
  otaBuildTarget.value = build;
  otaSelectedDeviceId.value = build.device_id;
  otaError.value = null;
  otaDevicesLoading.value = true;
  try {
    const all = await apiFetch<DeviceLite[]>("/api/v1/devices");
    // Only show claimed + hardware-category devices — service/bridge/agent
    // don't accept firmware bin flashes.
    otaDevices.value = all.filter((d) => d.device_type === "esp32" || d.device_type === "hardware");
    if (otaSelectedDeviceId.value === null && otaDevices.value.length > 0) {
      otaSelectedDeviceId.value = otaDevices.value[0].id;
    }
  } catch (e) {
    otaError.value = e instanceof Error ? e.message : "Failed to load devices";
  } finally {
    otaDevicesLoading.value = false;
  }
}

function closeOtaModal(): void {
  otaBuildTarget.value = null;
  otaSelectedDeviceId.value = null;
  otaError.value = null;
}

async function confirmOtaPush(): Promise<void> {
  if (!otaBuildTarget.value || !otaSelectedDeviceId.value) return;
  otaPushing.value = true;
  otaError.value = null;
  try {
    const res = await apiFetch<{ rollout_id: number; firmware_id: number; build: FirmwareBuild }>(
      `/api/v1/firmware/builds/${otaBuildTarget.value.id}/ota`,
      {
        method: "POST",
        body: JSON.stringify({ device_id: otaSelectedDeviceId.value }),
      },
    );
    // Update the build row inline so the status badge appears without
    // waiting for the next poll tick.
    const idx = builds.value.findIndex((b) => b.id === res.build.id);
    if (idx >= 0) builds.value[idx] = res.build;
    toast.addToast(
      t("firmware.otaPushedToast", { rollout: res.rollout_id }),
      "success",
    );
    closeOtaModal();
  } catch (e) {
    const msg = e instanceof Error ? e.message : "OTA push failed";
    otaError.value = msg;
    toast.addToast(msg, "error");
  } finally {
    otaPushing.value = false;
  }
}

function toggleTail(build: FirmwareBuild): void {
  if (tailedBuildId.value === build.id) {
    tailedBuildId.value = null;
    tailLogs.value = "";
  } else {
    tailedBuildId.value = build.id;
    tailLogs.value = "";
  }
}

// ── Polling: refresh builds list + live logs for the selected build ───────

async function pollTick(): Promise<void> {
  // Refresh list to catch status transitions
  try {
    builds.value = await apiFetch<FirmwareBuild[]>("/api/v1/firmware/builds?limit=50");
  } catch {
    /* ignore transient errors */
  }
  // Fetch logs for currently tailed build (if any)
  if (tailedBuildId.value !== null) {
    tailLoading.value = true;
    try {
      const text = await apiFetch<string>(
        `/api/v1/firmware/builds/${tailedBuildId.value}/logs`
      );
      tailLogs.value = text || "";
    } catch {
      /* ignore */
    } finally {
      tailLoading.value = false;
    }
  }
}

function startPolling(): void {
  if (pollHandle !== null) return;
  pollHandle = window.setInterval(pollTick, 3000);
}

function stopPolling(): void {
  if (pollHandle !== null) {
    window.clearInterval(pollHandle);
    pollHandle = null;
  }
}

// Only poll while the page is visible + a build is in-flight OR tail is on
const activeBuildCount = computed(() =>
  builds.value.filter((b) => b.status === "queued" || b.status === "building").length
);

watch(
  () => ({ count: activeBuildCount.value, tailed: tailedBuildId.value }),
  ({ count, tailed }) => {
    if (count > 0 || tailed !== null) startPolling();
    else stopPolling();
  }
);

// ── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(async () => {
  await Promise.all([loadBoards(), loadBuilds()]);
  if (activeBuildCount.value > 0) startPolling();
});

onUnmounted(() => {
  stopPolling();
});

// ── Formatting helpers ────────────────────────────────────────────────────

function boardNameFor(id: number): string {
  return boards.value.find((b) => b.id === id)?.name || `#${id}`;
}

function statusBadge(status: FirmwareBuild["status"]): {
  variant: "info" | "warn" | "ok" | "bad" | "neutral";
  label: string;
} {
  switch (status) {
    case "queued":
      return { variant: "info", label: t("firmware.statusQueued") };
    case "building":
      return { variant: "warn", label: t("firmware.statusBuilding") };
    case "success":
      return { variant: "ok", label: t("firmware.statusSuccess") };
    case "failed":
      return { variant: "bad", label: t("firmware.statusFailed") };
    case "cancelled":
      return { variant: "neutral", label: t("firmware.statusCancelled") };
  }
}

// Sprint 7 — OTA rollout status badge (distinct from build status)
function otaBadge(status: FirmwareBuild["ota_status"]): {
  variant: "info" | "warn" | "ok" | "bad" | "neutral";
  label: string;
} | null {
  if (!status) return null;
  switch (status) {
    case "pending":
      return { variant: "info", label: t("firmware.otaStatusPending") };
    case "active":
      return { variant: "warn", label: t("firmware.otaStatusActive") };
    case "paused":
      return { variant: "neutral", label: t("firmware.otaStatusPaused") };
    case "completed":
      return { variant: "ok", label: t("firmware.otaStatusCompleted") };
    case "failed":
      return { variant: "bad", label: t("firmware.otaStatusFailed") };
    default:
      return null;
  }
}

function fmtDuration(start: string | null, end: string | null): string {
  if (!start) return "—";
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  const ms = Math.max(0, e - s);
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return `${sec}s`;
  return `${Math.floor(sec / 60)}m ${sec % 60}s`;
}

function fmtRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return t("firmware.justNow");
  if (mins < 60) return t("firmware.minutesAgo", { n: mins });
  const hours = Math.floor(mins / 60);
  if (hours < 24) return t("firmware.hoursAgo", { n: hours });
  return new Date(iso).toLocaleDateString();
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-xl font-semibold text-[var(--text-primary)]">
          {{ t("firmware.title") }}
        </h1>
        <p class="text-xs text-[var(--text-muted)] mt-0.5 max-w-2xl">
          {{ t("firmware.subtitle") }}
        </p>
      </div>
    </div>

    <!-- Error banner -->
    <div
      v-if="error"
      class="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-400"
    >
      {{ error }}
    </div>

    <!-- Kickoff card -->
    <UCard>
      <template #header>
        <h3 class="text-sm font-semibold">{{ t("firmware.newBuildTitle") }}</h3>
      </template>
      <div class="space-y-3">
        <div v-if="loadingBoards" class="text-xs text-[var(--text-muted)]">
          <USkeleton height="2rem" width="100%" />
        </div>
        <div v-else-if="!boards.length" class="text-xs text-[var(--text-muted)]">
          {{ t("firmware.noBoardsYet") }}
        </div>
        <div v-else class="space-y-2">
          <label class="text-[11px] font-medium text-[var(--text-muted)]">
            {{ t("firmware.selectBoardLabel") }}
          </label>
          <select
            v-model.number="selectedBoardId"
            class="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-raised)] text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--primary)]"
          >
            <option v-for="b in boards" :key="b.id" :value="b.id">
              {{ b.name }} ({{ b.chip }})
            </option>
          </select>
          <UButton
            variant="primary"
            :loading="kicking"
            :disabled="selectedBoardId === null"
            @click="handleKickoff"
          >
            {{ t("firmware.kickoffButton") }}
          </UButton>
          <p class="text-[11px] text-[var(--text-muted)] leading-relaxed">
            {{ t("firmware.kickoffHint") }}
          </p>
        </div>
      </div>
    </UCard>

    <!-- Builds list -->
    <UCard padding="none">
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-semibold">{{ t("firmware.buildsListTitle") }}</h3>
          <span class="text-[11px] text-[var(--text-muted)]">{{ builds.length }}</span>
        </div>
      </template>
      <div v-if="loadingBuilds" class="p-4 space-y-2">
        <USkeleton v-for="i in 3" :key="i" height="2rem" width="100%" />
      </div>
      <UEmpty
        v-else-if="!builds.length"
        :title="t('firmware.emptyTitle')"
        :description="t('firmware.emptyDescription')"
        icon="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"
      />
      <div v-else class="divide-y divide-[var(--border)]">
        <div
          v-for="build in builds"
          :key="build.id"
          class="px-4 py-3"
        >
          <div class="flex items-center justify-between gap-3">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-sm font-semibold text-[var(--text-primary)]">
                  #{{ build.id }}
                </span>
                <UBadge :status="statusBadge(build.status).variant" size="sm">
                  {{ statusBadge(build.status).label }}
                </UBadge>
                <!-- Sprint 7 — OTA rollout status badge -->
                <UBadge
                  v-if="otaBadge(build.ota_status)"
                  :status="otaBadge(build.ota_status)!.variant"
                  size="sm"
                >
                  📡 {{ otaBadge(build.ota_status)!.label }}
                </UBadge>
                <span class="text-xs text-[var(--text-muted)]">
                  {{ boardNameFor(build.board_profile_id) }}
                </span>
                <span class="text-[11px] font-mono text-[var(--text-muted)]">
                  {{ build.pio_env }}
                </span>
              </div>
              <div class="mt-1 flex items-center gap-3 text-[11px] text-[var(--text-muted)]">
                <span>{{ fmtRelative(build.created_at) }}</span>
                <span v-if="build.started_at">
                  {{ t("firmware.duration") }}: {{ fmtDuration(build.started_at, build.finished_at) }}
                </span>
                <span v-if="build.artifact_size_kb">
                  {{ t("firmware.size") }}: {{ build.artifact_size_kb }} KB
                </span>
                <span
                  v-if="build.error_code"
                  class="font-mono text-[var(--status-bad)]"
                >
                  {{ build.error_code }}
                </span>
              </div>
            </div>
            <div class="flex items-center gap-1.5 shrink-0">
              <UButton
                v-if="build.has_logs"
                size="sm"
                variant="ghost"
                @click="toggleTail(build)"
              >
                {{ tailedBuildId === build.id ? t("firmware.hideLogs") : t("firmware.showLogs") }}
              </UButton>
              <UButton
                v-if="build.status === 'success'"
                size="sm"
                variant="secondary"
                @click="downloadBin(build)"
              >
                {{ t("firmware.download") }}
              </UButton>
              <!-- Sprint 7 — Push to device (disabled if already promoted) -->
              <UButton
                v-if="build.status === 'success'"
                size="sm"
                variant="primary"
                :disabled="build.ota_rollout_id !== null"
                :title="build.ota_rollout_id !== null ? t('firmware.otaAlreadyPushed') : ''"
                @click="openOtaModal(build)"
              >
                {{ build.ota_rollout_id !== null ? t('firmware.otaPushed') : t('firmware.pushToDevice') }}
              </UButton>
              <UButton
                v-if="build.status === 'queued' || build.status === 'building'"
                size="sm"
                variant="ghost"
                @click="cancelBuild(build)"
              >
                {{ t("firmware.cancel") }}
              </UButton>
            </div>
          </div>
          <!-- Live log tail -->
          <pre
            v-if="tailedBuildId === build.id"
            class="mt-3 p-3 rounded-lg bg-[var(--bg-base)] border border-[var(--border)] text-[10px] font-mono text-[var(--text-muted)] max-h-80 overflow-auto whitespace-pre-wrap"
          >{{ tailLogs || t('firmware.noLogsYet') }}</pre>
        </div>
      </div>
    </UCard>

    <!-- Sprint 7 — OTA Push modal -->
    <UModal
      :open="otaBuildTarget !== null"
      :title="t('firmware.otaModalTitle', { id: otaBuildTarget?.id ?? 0 })"
      size="sm"
      @close="closeOtaModal"
    >
      <div class="space-y-3 p-1">
        <p class="text-xs text-[var(--text-muted)]">
          {{ t('firmware.otaModalBody') }}
        </p>

        <!-- Device selector -->
        <div v-if="otaDevicesLoading" class="py-4">
          <USkeleton height="2rem" width="100%" />
        </div>
        <div v-else-if="otaDevices.length === 0" class="py-4 text-xs text-[var(--text-muted)]">
          {{ t('firmware.otaNoDevices') }}
        </div>
        <div v-else class="space-y-2">
          <label class="text-[11px] font-medium text-[var(--text-muted)]">
            {{ t('firmware.otaSelectDeviceLabel') }}
          </label>
          <select
            v-model.number="otaSelectedDeviceId"
            class="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-raised)] text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--primary)]"
          >
            <option
              v-for="d in otaDevices"
              :key="d.id"
              :value="d.id"
            >
              {{ d.name || d.device_uid }} · {{ d.device_type }}
              {{ d.online ? '· online' : '· offline' }}
            </option>
          </select>
          <p class="text-[11px] text-[var(--text-muted)] leading-relaxed">
            {{ t('firmware.otaHint') }}
          </p>
        </div>

        <div v-if="otaError" class="text-xs text-[var(--status-bad)]">
          {{ otaError }}
        </div>
      </div>
      <template #footer>
        <UButton variant="ghost" @click="closeOtaModal">
          {{ t('common.cancel') }}
        </UButton>
        <UButton
          variant="primary"
          :loading="otaPushing"
          :disabled="otaSelectedDeviceId === null || otaDevices.length === 0"
          @click="confirmOtaPush"
        >
          {{ t('firmware.otaConfirm') }}
        </UButton>
      </template>
    </UModal>
  </div>
</template>
