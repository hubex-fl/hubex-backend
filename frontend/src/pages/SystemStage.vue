<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useCapabilities, hasCap } from "../lib/capabilities";
import { fetchJson, ApiError } from "../lib/request";
import { useAbortHandle } from "../lib/abort";
import { createPoller } from "../lib/poller";
import GateBanner from "../components/GateBanner.vue";
import ErrorBox from "../components/ErrorBox.vue";

type RuntimeBadge = {
  label: string;
  value: string;
  className: string;
};

type DeviceRow = {
  id: number;
  device_uid: string;
  last_seen_at?: string | null;
  last_seen?: string | null;
  state?: string | null;
};

type EntityRow = {
  entity_id: string;
  type: string;
  name: string;
};

const caps = useCapabilities();
const { signal } = useAbortHandle();

const devices = ref<DeviceRow[]>([]);
const entities = ref<EntityRow[]>([]);
const devicesError = ref<string | null>(null);
const entitiesError = ref<string | null>(null);
const loading = ref(false);
const stoppedOnError = ref(false);

const capsReady = computed(() => caps.status === "ready");
const canReadDevices = computed(() => hasCap("devices.read"));
const canReadEntities = computed(() => hasCap("entities.read"));
const canReadVars = computed(() => hasCap("vars.read"));

const ENTITIES_PATH = "/api/v1/entities";
const DEVICES_PATH = "/api/v1/devices";
const offlineThresholdMs = 5 * 60 * 1000;

const bindingsByEntity = ref<Record<string, { device_id: number; enabled: boolean; priority: number }[]>>({});
const bindingsError = ref<string | null>(null);

let devicesInflight = false;
let entitiesInflight = false;
let bindingsInflight = false;

function lastSeen(device: DeviceRow): string | null {
  return device.last_seen_at ?? device.last_seen ?? null;
}

function isOffline(device: DeviceRow): boolean {
  const seen = lastSeen(device);
  if (!seen) return false;
  const delta = Date.now() - new Date(seen).getTime();
  return Number.isFinite(delta) && delta > offlineThresholdMs;
}

function statusLabel(device: DeviceRow): string {
  if (!lastSeen(device)) return "Unknown";
  return isOffline(device) ? "Offline" : "Online";
}

function statusClass(device: DeviceRow): string {
  if (!lastSeen(device)) return "pill-warn";
  return isOffline(device) ? "pill-bad" : "pill-ok";
}

function runtimeBadges(device: DeviceRow): RuntimeBadge[] {
  const unknown = !canReadVars.value;
  const offlineValue = lastSeen(device) ? (isOffline(device) ? "Offline" : "Online") : "Unknown";
  const offlineClass = lastSeen(device)
    ? (isOffline(device) ? "pill-bad" : "pill-ok")
    : "pill-warn";
  const unknownValue = unknown ? "N/A" : "Unknown";
  return [
    { label: "Pending", value: unknownValue, className: "pill-warn" },
    { label: "Ack", value: unknownValue, className: "pill-warn" },
    { label: "Stale", value: unknownValue, className: "pill-warn" },
    { label: "Offline", value: offlineValue, className: offlineClass },
  ];
}

function deviceLabel(deviceId: number): string {
  const found = devices.value.find((device) => device.id === deviceId);
  return found ? found.device_uid : `device#${deviceId}`;
}

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

async function refreshDevices() {
  if (!capsReady.value) {
    devices.value = [];
    devicesError.value = capsStatusMessage();
    return;
  }
  if (!canReadDevices.value) {
    devices.value = [];
    devicesError.value = "Missing capability: devices.read";
    return;
  }
  if (devicesInflight) return;
  devicesInflight = true;
  devicesError.value = null;
  try {
    devices.value = await fetchJson<DeviceRow[]>(DEVICES_PATH, { method: "GET" }, signal);
  } finally {
    devicesInflight = false;
  }
}

async function refreshEntities() {
  if (!capsReady.value) {
    entities.value = [];
    entitiesError.value = capsStatusMessage();
    return;
  }
  if (!canReadEntities.value) {
    entities.value = [];
    entitiesError.value = "Missing capability: entities.read";
    return;
  }
  if (entitiesInflight) return;
  entitiesInflight = true;
  entitiesError.value = null;
  try {
    entities.value = await fetchJson<EntityRow[]>(ENTITIES_PATH, { method: "GET" }, signal);
    bindingsError.value = null;
  } catch (err) {
    const e = err as ApiError;
    if (e?.status === 404) {
      entities.value = [];
      entitiesError.value = null;
    } else {
      entitiesError.value = mapError(err);
    }
  } finally {
    entitiesInflight = false;
  }
}

async function refreshBindings() {
  if (!capsReady.value) {
    bindingsByEntity.value = {};
    bindingsError.value = capsStatusMessage();
    return;
  }
  if (!canReadEntities.value) {
    bindingsByEntity.value = {};
    bindingsError.value = "Missing capability: entities.read";
    return;
  }
  if (!entities.value.length || entitiesError.value) return;
  if (bindingsInflight) return;
  bindingsInflight = true;
  try {
    const next: Record<string, { device_id: number; enabled: boolean; priority: number }[]> = {};
    await Promise.all(
      entities.value.map(async (entity) => {
        const path = `/api/v1/entities/${encodeURIComponent(entity.entity_id)}/devices`;
        try {
          next[entity.entity_id] = await fetchJson(path, { method: "GET" }, signal);
        } catch (err) {
          const e = err as ApiError;
          if (e?.status === 404) {
            next[entity.entity_id] = [];
            return;
          }
          bindingsError.value = mapError(err);
        }
      })
    );
    bindingsByEntity.value = next;
  } finally {
    bindingsInflight = false;
  }
}

async function refreshAll() {
  if (stoppedOnError.value) return;
  loading.value = true;
  try {
    await Promise.all([refreshDevices(), refreshEntities()]);
    await refreshBindings();
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
    entitiesError.value = capsStatusMessage();
    bindingsError.value = capsStatusMessage();
    return;
  }
  stoppedOnError.value = false;
  devicesError.value = null;
  entitiesError.value = null;
  bindingsError.value = null;
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
      <h2>System Stage (read-only)</h2>
      <button class="btn secondary" @click="retryAll">Retry</button>
    </div>

    <GateBanner
      v-if="caps.status !== 'ready'"
      :status="caps.status"
      :message="capsStatusMessage()"
    />

    <section class="card">
      <h3>Entities</h3>
      <ErrorBox v-if="entitiesError" :message="entitiesError" @retry="retryAll" />
      <div v-else-if="!capsReady" class="muted">Capabilities unavailable</div>
      <div v-else-if="!canReadEntities" class="muted">Missing capability: entities.read</div>
      <div v-else-if="loading" class="muted">Loading.</div>
      <table v-else-if="entities.length" class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Type</th>
            <th>Name</th>
            <th>Devices</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="entity in entities" :key="entity.entity_id">
            <td>{{ entity.entity_id }}</td>
            <td>{{ entity.type }}</td>
            <td>{{ entity.name }}</td>
            <td>
              <ErrorBox v-if="bindingsError" :message="bindingsError" :showRetry="false" />
              <ul v-else class="muted">
                <li
                  v-for="binding in bindingsByEntity[entity.entity_id] || []"
                  :key="`${entity.entity_id}-${binding.device_id}`"
                >
                  {{ deviceLabel(binding.device_id) }}
                </li>
                <li v-if="!bindingsByEntity[entity.entity_id]?.length">-</li>
              </ul>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="muted">No entities.</div>
    </section>

    <section class="card">
      <h3>Devices</h3>
      <ErrorBox v-if="devicesError" :message="devicesError" @retry="retryAll" />
      <div v-else-if="!capsReady" class="muted">Capabilities unavailable</div>
      <div v-else-if="!canReadDevices" class="muted">Missing capability: devices.read</div>
      <div v-else-if="!canReadVars" class="muted">
        Missing capability: vars.read (runtime states unavailable)
      </div>
      <div v-else-if="loading" class="muted">Loading.</div>
      <table v-else-if="devices.length" class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>UID</th>
            <th>Status</th>
            <th>Runtime</th>
            <th>State</th>
            <th>Last seen</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="device in devices" :key="device.id">
            <td>{{ device.id }}</td>
            <td>{{ device.device_uid }}</td>
            <td>
              <span :class="['pill', statusClass(device)]">
                {{ statusLabel(device) }}
              </span>
            </td>
            <td>
              <div class="row">
                <span
                  v-for="badge in runtimeBadges(device)"
                  :key="badge.label"
                  :class="['pill', badge.className]"
                >
                  {{ badge.label }}: {{ badge.value }}
                </span>
              </div>
            </td>
            <td>{{ device.state ?? "Unknown" }}</td>
            <td>{{ lastSeen(device) ?? "-" }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="muted">No devices.</div>
    </section>
  </div>
</template>


