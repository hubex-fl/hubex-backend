<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
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

type EventItem = {
  cursor?: number;
};

type EventsResponse = {
  stream?: string;
  cursor?: number;
  next_cursor?: number;
  items?: EventItem[];
};

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
const loading = ref(false);

const capsReady = computed(() => caps.status === "ready");
const failedCount = ref<number | null>(null);
const offlineCount = ref<number | null>(null);
const eventsCount = ref<number | null>(null);
const caughtUp = ref<boolean | null>(null);
const eventsCursor = ref(0);

const devicesPaused = ref(false);
const effectsPaused = ref(false);
const eventsPaused = ref(false);

const timeToAck = computed(() => {
  if (!canReadEvents.value) return "Missing capability: events.read";
  if (eventsError.value) return eventsError.value;
  return "Unavailable";
});

const anyCap = computed(() => canReadDevices.value || canReadEffects.value || canReadEvents.value);

const DEVICES_PATH = "/api/v1/devices";
const EFFECTS_PATH = "/api/v1/effects?limit=200";
const EVENTS_STREAM = "tenant.system";
const EVENTS_LIMIT = 100;
const offlineThresholdMs = 5 * 60 * 1000;

let devicesInflight = false;
let effectsInflight = false;
let eventsInflight = false;
let polling = false;

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
  const failed = statuses.filter((s) => s === "failed").length;
  return { failed };
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
  if (devicesPaused.value) return;
  if (devicesInflight) return;
  devicesInflight = true;
  devicesError.value = null;
  try {
    devices.value = await fetchJson<DeviceRow[]>(DEVICES_PATH, { method: "GET" }, signal);
    offlineCount.value = computeOfflineCount(devices.value);
    devicesPaused.value = false;
  } catch (err) {
    devicesError.value = mapError(err);
    offlineCount.value = null;
    devicesPaused.value = true;
  } finally {
    devicesInflight = false;
  }
}

async function refreshEffects() {
  if (!capsReady.value) {
    effects.value = [];
    effectsError.value = capsStatusMessage();
    failedCount.value = null;
    return;
  }
  if (!canReadEffects.value) {
    effects.value = [];
    effectsError.value = "Missing capability: effects.read";
    failedCount.value = null;
    return;
  }
  if (effectsPaused.value) return;
  if (effectsInflight) return;
  effectsInflight = true;
  effectsError.value = null;
  try {
    const res = await fetchJson<EffectsResponse>(EFFECTS_PATH, { method: "GET" }, signal);
    const rows = Array.isArray(res) ? res : res.items ?? [];
    effects.value = rows;
    const counts = computeEffectCounts(rows);
    failedCount.value = counts.failed;
    effectsPaused.value = false;
  } catch (err) {
    effectsError.value = mapError(err);
    failedCount.value = null;
    effectsPaused.value = true;
  } finally {
    effectsInflight = false;
  }
}

async function refreshEvents() {
  if (!capsReady.value) {
    eventsError.value = capsStatusMessage();
    eventsCount.value = null;
    caughtUp.value = null;
    return;
  }
  if (!canReadEvents.value) {
    eventsError.value = "Missing capability: events.read";
    eventsCount.value = null;
    caughtUp.value = null;
    return;
  }
  if (eventsPaused.value) return;
  if (eventsInflight) return;
  eventsInflight = true;
  eventsError.value = null;
  try {
    const url = `/api/v1/events?stream=${encodeURIComponent(EVENTS_STREAM)}&cursor=${eventsCursor.value}&limit=${EVENTS_LIMIT}`;
    const res = await fetchJson<EventsResponse>(url, { method: "GET" }, signal);
    const items = res?.items ?? [];
    eventsCount.value = items.length;
    caughtUp.value = items.length === 0;
    if (typeof res?.next_cursor === "number") {
      eventsCursor.value = res.next_cursor;
    }
    eventsPaused.value = false;
  } catch (err) {
    eventsError.value = mapError(err);
    eventsCount.value = null;
    caughtUp.value = null;
    eventsPaused.value = true;
  } finally {
    eventsInflight = false;
  }
}

async function refreshAll() {
  loading.value = true;
  try {
    await Promise.all([refreshDevices(), refreshEffects(), refreshEvents()]);
  } catch (err) {
    if (!devicesError.value) devicesError.value = mapError(err);
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
  if (!anyCap.value) {
    devicesError.value = "Missing capabilities.";
    effectsError.value = "Missing capabilities.";
    eventsError.value = "Missing capabilities.";
    return;
  }
  devicesError.value = null;
  effectsError.value = null;
  eventsError.value = null;
  devicesPaused.value = false;
  effectsPaused.value = false;
  eventsPaused.value = false;
  if (polling) {
    if (document.visibilityState !== "hidden") {
      refreshAll().catch(() => {
        stopPolling();
      });
    }
    return;
  }
  startPolling();
}

function retryDevices() {
  if (!capsReady.value) {
    devicesError.value = capsStatusMessage();
    return;
  }
  if (!canReadDevices.value) {
    devicesError.value = "Missing capability: devices.read";
    return;
  }
  devicesPaused.value = false;
  devicesError.value = null;
  refreshDevices().catch(() => {
    devicesPaused.value = true;
  });
}

function retryEffects() {
  if (!capsReady.value) {
    effectsError.value = capsStatusMessage();
    return;
  }
  if (!canReadEffects.value) {
    effectsError.value = "Missing capability: effects.read";
    return;
  }
  effectsPaused.value = false;
  effectsError.value = null;
  refreshEffects().catch(() => {
    effectsPaused.value = true;
  });
}

function retryEvents() {
  if (!capsReady.value) {
    eventsError.value = capsStatusMessage();
    return;
  }
  if (!canReadEvents.value) {
    eventsError.value = "Missing capability: events.read";
    return;
  }
  eventsPaused.value = false;
  eventsError.value = null;
  refreshEvents().catch(() => {
    eventsPaused.value = true;
  });
}

const poller = createPoller(refreshAll, 5000, { pauseWhenHidden: true });

function startPolling() {
  if (polling) return;
  polling = true;
  poller.start();
}

function stopPolling() {
  if (!polling) return;
  polling = false;
  poller.stop();
}

onMounted(() => {
  if (caps.status === "ready" && anyCap.value) {
    startPolling();
  }
});

onUnmounted(() => {
  stopPolling();
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
        <div class="card-header-row">
          <div class="info-label">Events lag / caught up</div>
          <button class="btn secondary" :disabled="!capsReady || !canReadEvents" @click="retryEvents">Retry</button>
        </div>
        <div class="info-value">
          <span v-if="!capsReady" class="muted">Capabilities unavailable</span>
          <span v-else-if="!canReadEvents" class="muted">Missing capability: events.read</span>
          <span v-else-if="eventsError" class="error">{{ eventsError }}</span>
          <span v-else-if="caughtUp === null" class="muted">Unavailable</span>
          <span v-else>{{ caughtUp ? "Caught up" : `New events: ${eventsCount ?? 0}` }}</span>
        </div>
      </div>

      <div class="card">
        <div class="card-header-row">
          <div class="info-label">Recent failures</div>
          <button class="btn secondary" :disabled="!capsReady || !canReadEffects" @click="retryEffects">Retry</button>
        </div>
        <div class="info-value">
          <span v-if="!capsReady" class="muted">Capabilities unavailable</span>
          <span v-else-if="!canReadEffects" class="muted">Missing capability: effects.read</span>
          <span v-else-if="effectsError" class="error">{{ effectsError }}</span>
          <span v-else>{{ failedCount ?? "Unavailable" }}</span>
        </div>
      </div>

      <div class="card">
        <div class="card-header-row">
          <div class="info-label">Offline devices</div>
          <button class="btn secondary" :disabled="!capsReady || !canReadDevices" @click="retryDevices">Retry</button>
        </div>
        <div class="info-value">
          <span v-if="!capsReady" class="muted">Capabilities unavailable</span>
          <span v-else-if="!canReadDevices" class="muted">Missing capability: devices.read</span>
          <span v-else-if="devicesError" class="error">{{ devicesError }}</span>
          <span v-else>{{ offlineCount ?? "Unavailable" }}</span>
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
