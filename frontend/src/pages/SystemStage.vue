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

const canReadDevices = computed(() => hasCap("devices.read"));
const canReadEntities = computed(() => hasCap("entities.read"));

const ENTITIES_PATH = "/api/v1/entities";
const DEVICES_PATH = "/api/v1/devices";
const offlineThresholdMs = 5 * 60 * 1000;

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

function mapError(err: unknown): string {
  const e = err as ApiError;
  if (e?.status) {
    return `HTTP ${e.status}: ${e.message}`;
  }
  return (e && "message" in e) ? String(e.message) : "request_failed";
}

async function refreshDevices() {
  if (!canReadDevices.value) {
    devices.value = [];
    devicesError.value = "Missing capability: devices.read";
    return;
  }
  devicesError.value = null;
  devices.value = await fetchJson<DeviceRow[]>(DEVICES_PATH, { method: "GET" }, signal);
}

async function refreshEntities() {
  if (!canReadEntities.value) {
    entities.value = [];
    entitiesError.value = "Missing capability: entities.read";
    return;
  }
  entitiesError.value = null;
  try {
    entities.value = await fetchJson<EntityRow[]>(ENTITIES_PATH, { method: "GET" }, signal);
  } catch (err) {
    const e = err as ApiError;
    if (e?.status === 404) {
      entities.value = [];
      entitiesError.value = null;
      return;
    }
    entitiesError.value = mapError(err);
  }
}

async function refreshAll() {
  if (stoppedOnError.value) return;
  loading.value = true;
  try {
    await Promise.all([refreshDevices(), refreshEntities()]);
  } catch (err) {
    if (!devicesError.value) devicesError.value = mapError(err);
    stoppedOnError.value = true;
    poller.stop();
  } finally {
    loading.value = false;
  }
}

function retryAll() {
  stoppedOnError.value = false;
  devicesError.value = null;
  entitiesError.value = null;
  refreshAll().catch(() => {
    stoppedOnError.value = true;
    poller.stop();
  });
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

    <p v-if="caps.status === 'unavailable'" class="muted">Capabilities unavailable</p>
    <p v-else-if="caps.status === 'loading'" class="muted">Loading capabilities…</p>
    <p v-else-if="caps.status === 'error'" class="error">Capabilities error: {{ caps.error }}</p>

    <section class="card">
      <h3>Entities</h3>
      <div v-if="entitiesError" class="error">{{ entitiesError }}</div>
      <div v-else-if="!canReadEntities" class="muted">Missing capability: entities.read</div>
      <div v-else-if="loading" class="muted">Loading…</div>
      <table v-else-if="entities.length" class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Type</th>
            <th>Name</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="entity in entities" :key="entity.entity_id">
            <td>{{ entity.entity_id }}</td>
            <td>{{ entity.type }}</td>
            <td>{{ entity.name }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="muted">No entities.</div>
    </section>

    <section class="card">
      <h3>Devices</h3>
      <div v-if="devicesError" class="error">{{ devicesError }}</div>
      <div v-else-if="!canReadDevices" class="muted">Missing capability: devices.read</div>
      <div v-else-if="loading" class="muted">Loading…</div>
      <table v-else-if="devices.length" class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>UID</th>
            <th>Status</th>
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
            <td>{{ device.state ?? "Unknown" }}</td>
            <td>{{ lastSeen(device) ?? "-" }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="muted">No devices.</div>
    </section>
  </div>
</template>
