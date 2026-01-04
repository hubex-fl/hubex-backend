<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useCapabilities, hasCap } from "../lib/capabilities";
import { fetchJson, ApiError } from "../lib/request";
import { useAbortHandle } from "../lib/abort";
import { createPoller } from "../lib/poller";

type DeviceRow = {
  id: number;
  device_uid: string;
  last_seen_at?: string | null;
  last_seen?: string | null;
};

type EffectRow = {
  effect_id?: string;
  status?: string;
  created_at?: string;
};

type EffectsResponse = {
  items?: EffectRow[];
} | EffectRow[];

const caps = useCapabilities();
const { signal } = useAbortHandle();

const canReadDevices = computed(() => hasCap("devices.read"));
const canReadEffects = computed(() => hasCap("effects.read"));
const canReadEvents = computed(() => hasCap("events.read"));

const devices = ref<DeviceRow[]>([]);
const effects = ref<EffectRow[]>([]);

const devicesError = ref<string | null>(null);
const effectsError = ref<string | null>(null);
const eventsError = ref<string | null>(null);
const stoppedOnError = ref(false);
const loading = ref(false);

const capsReady = computed(() => caps.status === "ready");
const pendingCount = ref<number | null>(null);
const failedCount = ref<number | null>(null);
const offlineCount = ref<number | null>(null);

const ackOutcome = computed(() => {
  if (!canReadEffects.value) return "Missing capability: effects.read";
  if (effectsError.value) return effectsError.value;
  if (failedCount.value === null || pendingCount.value === null) return "Unavailable";
  const doneCount = effects.value.filter((e) => normalizeStatus(e.status) === "done").length;
  return `ok: ${doneCount}, failed: ${failedCount.value}`;
});

const timeToAck = computed(() => {
  if (!canReadEvents.value) return "Missing capability: events.read";
  if (eventsError.value) return eventsError.value;
  return "Unavailable";
});

const anyCap = computed(() => canReadDevices.value || canReadEffects.value || canReadEvents.value);

const DEVICES_PATH = "/api/v1/devices";
const EFFECTS_PATH = "/api/v1/effects?limit=200";
const offlineThresholdMs = 5 * 60 * 1000;

let devicesInflight = false;
let effectsInflight = false;

function mapError(err: unknown): string {
  const e = err as ApiError;
  if (e?.status) {
    return `HTTP ${e.status}: ${e.message}`;
  }
  return (e && "message" in e) ? String(e.message) : "request_failed";
}

function capsStatusMessage(): string {
  if (caps.status === "loading") return "Capabilities loading.";
  if (caps.status === "error") return `Capabilities error: ${caps.error ?? "unknown"}`;
  return "Capabilities unavailable";
}

function lastSeen(device: DeviceRow): string | null {
  return device.last_seen_at ?? device.last_seen ?? null;
}

function computeOfflineCount(rows: DeviceRow[]): number | null {
  const withSeen = rows.filter((d) => lastSeen(d));
  if (!withSeen.length) return null;
  const now = Date.now();
  return withSeen.filter((d) => {
    const seen = lastSeen(d);
    if (!seen) return false;
    const delta = now - new Date(seen).getTime();
    return Number.isFinite(delta) && delta > offlineThresholdMs;
  }).length;
}

function normalizeStatus(value?: string): string {
  return (value ?? "").toLowerCase();
}

function computeEffectCounts(rows: EffectRow[]) {
  const statuses = rows.map((row) => normalizeStatus(row.status));
  const pending = statuses.filter((s) => s === "queued" || s === "in_flight").length;
  const failed = statuses.filter((s) => s === "failed").length;
  return { pending, failed };
}

async function refreshDevices() {
  if (!capsReady.value) {
    devices.value = [];
    devicesError.value = capsStatusMessage();
    offlineCount.value = null;
    return;
  }
  if (!canReadDevices.value) {
    devices.value = [];
    devicesError.value = "Missing capability: devices.read";
    offlineCount.value = null;
    return;
  }
  if (devicesInflight) return;
  devicesInflight = true;
  devicesError.value = null;
  try {
    devices.value = await fetchJson<DeviceRow[]>(DEVICES_PATH, { method: "GET" }, signal);
    offlineCount.value = computeOfflineCount(devices.value);
  } catch (err) {
    devicesError.value = mapError(err);
    offlineCount.value = null;
  } finally {
    devicesInflight = false;
  }
}

async function refreshEffects() {
  if (!capsReady.value) {
    effects.value = [];
    effectsError.value = capsStatusMessage();
    pendingCount.value = null;
    failedCount.value = null;
    return;
  }
  if (!canReadEffects.value) {
    effects.value = [];
    effectsError.value = "Missing capability: effects.read";
    pendingCount.value = null;
    failedCount.value = null;
    return;
  }
  if (effectsInflight) return;
  effectsInflight = true;
  effectsError.value = null;
  try {
    const res = await fetchJson<EffectsResponse>(EFFECTS_PATH, { method: "GET" }, signal);
    const rows = Array.isArray(res) ? res : res.items ?? [];
    effects.value = rows;
    const counts = computeEffectCounts(rows);
    pendingCount.value = counts.pending;
    failedCount.value = counts.failed;
  } catch (err) {
    effectsError.value = mapError(err);
    pendingCount.value = null;
    failedCount.value = null;
  } finally {
    effectsInflight = false;
  }
}

async function refreshAll() {
  if (stoppedOnError.value) return;
  loading.value = true;
  try {
    await Promise.all([refreshDevices(), refreshEffects()]);
  } catch (err) {
    if (!devicesError.value) devicesError.value = mapError(err);
    stoppedOnError.value = true;
    poller.stop();
  } finally {
    loading.value = false;
  }
}

function retryAll() {
  if (!capsReady.value) {
    devicesError.value = capsStatusMessage();
    effectsError.value = capsStatusMessage();
    eventsError.value = capsStatusMessage();
    return;
  }
  stoppedOnError.value = false;
  devicesError.value = null;
  effectsError.value = null;
  eventsError.value = null;
  if (document.visibilityState !== "hidden") {
    refreshAll().catch(() => {
      stoppedOnError.value = true;
      poller.stop();
    });
  }
  poller.start();
}

const poller = createPoller(refreshAll, 5000, { pauseWhenHidden: true });

watch(
  () => caps.status,
  (status) => {
    if (status === "ready") {
      retryAll();
    }
  }
);

onMounted(() => {
  if (caps.status === "ready") {
    retryAll();
  }
});

onUnmounted(() => {
  poller.stop();
});
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>Observability (read-only)</h2>
      <button class="btn secondary" @click="retryAll">Retry</button>
    </div>

    <p v-if="caps.status === 'unavailable'" class="muted">Capabilities unavailable</p>
    <p v-else-if="caps.status === 'loading'" class="muted">Loading capabilities.</p>
    <p v-else-if="caps.status === 'error'" class="error">Capabilities error: {{ caps.error }}</p>
    <p v-else-if="!anyCap" class="muted">No capabilities available for observability.</p>

    <div class="info-grid">
      <div class="card">
        <div class="info-label">Pending intents</div>
        <div class="info-value">
          <span v-if="!capsReady" class="muted">Capabilities unavailable</span>
          <span v-else-if="!canReadEffects" class="muted">Missing capability: effects.read</span>
          <span v-else-if="effectsError" class="error">{{ effectsError }}</span>
          <span v-else>{{ pendingCount ?? "Unavailable" }}</span>
        </div>
      </div>

      <div class="card">
        <div class="info-label">Failure counts</div>
        <div class="info-value">
          <span v-if="!capsReady" class="muted">Capabilities unavailable</span>
          <span v-else-if="!canReadEffects" class="muted">Missing capability: effects.read</span>
          <span v-else-if="effectsError" class="error">{{ effectsError }}</span>
          <span v-else>{{ failedCount ?? "Unavailable" }}</span>
        </div>
      </div>

      <div class="card">
        <div class="info-label">Offline devices</div>
        <div class="info-value">
          <span v-if="!capsReady" class="muted">Capabilities unavailable</span>
          <span v-else-if="!canReadDevices" class="muted">Missing capability: devices.read</span>
          <span v-else-if="devicesError" class="error">{{ devicesError }}</span>
          <span v-else>{{ offlineCount ?? "Unavailable" }}</span>
        </div>
      </div>

      <div class="card">
        <div class="info-label">Ack outcomes (last N)</div>
        <div class="info-value">
          <span v-if="!capsReady" class="muted">Capabilities unavailable</span>
          <span v-else-if="ackOutcome.startsWith('Missing capability')" class="muted">{{ ackOutcome }}</span>
          <span v-else-if="ackOutcome.startsWith('HTTP')" class="error">{{ ackOutcome }}</span>
          <span v-else>{{ ackOutcome }}</span>
        </div>
      </div>

      <div class="card">
        <div class="info-label">Time-to-ack (approx)</div>
        <div class="info-value">
          <span v-if="!capsReady" class="muted">Capabilities unavailable</span>
          <span v-else-if="timeToAck.startsWith('Missing capability')" class="muted">{{ timeToAck }}</span>
          <span v-else-if="timeToAck.startsWith('HTTP')" class="error">{{ timeToAck }}</span>
          <span v-else>{{ timeToAck }}</span>
        </div>
      </div>
    </div>

    <div v-if="loading" class="muted">Loading.</div>
  </div>
</template>
