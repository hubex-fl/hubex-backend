<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch, nextTick } from "vue";
import { useRouter } from "vue-router";
import { useCapabilities, hasCap } from "../lib/capabilities";
import { fetchJson, ApiError } from "../lib/request";
import { useAbortHandle } from "../lib/abort";
import { createPoller } from "../lib/poller";

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
  __sig?: string;
};

type EntityRow = {
  entity_id: string;
  type: string;
  name: string;
  __sig?: string;
};

const caps = useCapabilities();
const { signal } = useAbortHandle();
const router = useRouter();

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
const bindingsSigByEntity = ref<Record<string, string>>({});

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

function onRowClick(device: DeviceRow): void {
  if (device.state !== "claimed") return;
  router.push(`/devices/${device.id}`);
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

function scheduleScrollRestore(y: number) {
  if (typeof window === "undefined") return;
  const schedule = typeof window.requestAnimationFrame === "function"
    ? window.requestAnimationFrame.bind(window)
    : (cb: FrameRequestCallback) => window.setTimeout(cb, 0);
  schedule(() => window.scrollTo({ top: y }));
}

function deviceSig(device: DeviceRow): string {
  return [
    device.id,
    device.device_uid,
    device.state ?? "",
    device.last_seen_at ?? device.last_seen ?? "",
  ].join("|");
}

function entitySig(entity: EntityRow): string {
  return [entity.entity_id, entity.type, entity.name].join("|");
}

function reconcileById<T extends { id: number; __sig?: string }>(
  target: T[],
  next: T[],
  sigFn: (item: T) => string
) {
  const byId = new Map<number, T>();
  for (const item of target) {
    byId.set(item.id, item);
  }
  const ordered: T[] = [];
  for (const item of next) {
    const existing = byId.get(item.id);
    if (existing) {
      const nextSig = sigFn(item);
      if (existing.__sig !== nextSig) {
        Object.assign(existing, item);
        existing.__sig = nextSig;
      }
      ordered.push(existing);
    } else {
      item.__sig = sigFn(item);
      ordered.push(item);
    }
  }
  target.splice(0, target.length, ...ordered);
}

function reconcileByKey<T extends { __sig?: string }>(
  target: T[],
  next: T[],
  keyFn: (item: T) => string,
  sigFn: (item: T) => string
) {
  const byKey = new Map<string, T>();
  for (const item of target) {
    byKey.set(keyFn(item), item);
  }
  const ordered: T[] = [];
  for (const item of next) {
    const key = keyFn(item);
    const existing = byKey.get(key);
    if (existing) {
      const nextSig = sigFn(item);
      if (existing.__sig !== nextSig) {
        Object.assign(existing, item);
        existing.__sig = nextSig;
      }
      ordered.push(existing);
    } else {
      item.__sig = sigFn(item);
      ordered.push(item);
    }
  }
  target.splice(0, target.length, ...ordered);
}

function capsStatusMessage(): string {
  if (caps.status === "loading") return "Capabilities loading.";
  if (caps.status === "error") return `Capabilities error: ${caps.error ?? "unknown"}`;
  return "Capabilities unavailable";
}

async function refreshDevices() {
  if (document.visibilityState !== "visible") return;
  if (!capsReady.value) {
    devicesError.value = capsStatusMessage();
    return;
  }
  if (!canReadDevices.value) {
    devicesError.value = "Missing capability: devices.read";
    return;
  }
  if (devicesInflight) return;
  devicesInflight = true;
  devicesError.value = null;
  const scrollY = typeof window !== "undefined" ? window.scrollY : 0;
  try {
    const next = await fetchJson<DeviceRow[]>(DEVICES_PATH, { method: "GET" }, signal);
    reconcileById(devices.value, next, deviceSig);
    await nextTick();
    scheduleScrollRestore(scrollY);
  } finally {
    devicesInflight = false;
  }
}

async function refreshEntities() {
  if (!capsReady.value) {
    entitiesError.value = capsStatusMessage();
    return;
  }
  if (!canReadEntities.value) {
    entitiesError.value = "Missing capability: entities.read";
    return;
  }
  if (entitiesInflight) return;
  entitiesInflight = true;
  entitiesError.value = null;
  try {
    const next = await fetchJson<EntityRow[]>(ENTITIES_PATH, { method: "GET" }, signal);
    reconcileByKey(entities.value, next, (item) => item.entity_id, entitySig);
    bindingsError.value = null;
  } catch (err) {
    const e = err as ApiError;
    if (e?.status === 404) {
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
    bindingsError.value = capsStatusMessage();
    return;
  }
  if (!canReadEntities.value) {
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
    const current = bindingsByEntity.value;
    for (const key of Object.keys(current)) {
      if (!(key in next)) {
        delete current[key];
      }
    }
    for (const key of Object.keys(next)) {
      current[key] = next[key];
    }
    const sigs: Record<string, string> = {};
    for (const key of Object.keys(current)) {
      const list = current[key] ?? [];
      sigs[key] = list
        .map((b) => `${b.device_id}:${b.enabled}:${b.priority}`)
        .sort()
        .join("|");
    }
    bindingsSigByEntity.value = sigs;
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
  if (!canReadDevices.value && !canReadEntities.value) {
    devicesError.value = "Missing capability: devices.read";
    entitiesError.value = "Missing capability: entities.read";
    bindingsError.value = "Missing capability: entities.read";
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

    <div class="status-line">
      <span v-if="caps.status === 'unavailable'" class="muted">Capabilities unavailable</span>
      <span v-else-if="caps.status === 'loading'" class="muted">Loading capabilities.</span>
      <span v-else-if="caps.status === 'error'" class="error">Capabilities error: {{ caps.error }}</span>
    </div>

    <section class="card">
      <h3>Entities</h3>
      <div class="section-status">
        <span v-if="entitiesError" class="error">{{ entitiesError }}</span>
        <span v-else-if="!capsReady" class="muted">Capabilities unavailable</span>
        <span v-else-if="!canReadEntities" class="muted">Missing capability: entities.read</span>
        <span v-else-if="loading" class="muted">Loading.</span>
      </div>
      <table class="table table-fixed entities-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Type</th>
            <th>Name</th>
            <th>Devices</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="entitiesError">
            <td colspan="4" class="muted">{{ entitiesError }}</td>
          </tr>
          <tr v-else-if="!capsReady">
            <td colspan="4" class="muted">Capabilities unavailable</td>
          </tr>
          <tr v-else-if="!canReadEntities">
            <td colspan="4" class="muted">Missing capability: entities.read</td>
          </tr>
          <tr v-else-if="loading">
            <td colspan="4" class="muted">Loading.</td>
          </tr>
          <tr v-else-if="!entities.length">
            <td colspan="4" class="muted">No entities.</td>
          </tr>
          <tr v-else v-for="entity in entities" :key="entity.entity_id" v-memo="[entity.__sig]">
            <td>{{ entity.entity_id }}</td>
            <td>{{ entity.type }}</td>
            <td>{{ entity.name }}</td>
            <td>
              <div v-if="bindingsError" class="error">{{ bindingsError }}</div>
              <ul v-else class="muted" v-memo="[bindingsSigByEntity[entity.entity_id] || '']">
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
    </section>

    <section class="card">
      <h3>Devices</h3>
      <div class="section-status">
        <span v-if="devicesError" class="error">{{ devicesError }}</span>
        <span v-else-if="!capsReady" class="muted">Capabilities unavailable</span>
        <span v-else-if="!canReadDevices" class="muted">Missing capability: devices.read</span>
        <span v-else-if="!canReadVars" class="muted">
          Missing capability: vars.read (runtime states unavailable)
        </span>
        <span v-else-if="loading" class="muted">Loading.</span>
      </div>
      <table class="table table-fixed devices-table">
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
          <tr v-if="devicesError">
            <td colspan="6" class="muted">{{ devicesError }}</td>
          </tr>
          <tr v-else-if="!capsReady">
            <td colspan="6" class="muted">Capabilities unavailable</td>
          </tr>
          <tr v-else-if="!canReadDevices">
            <td colspan="6" class="muted">Missing capability: devices.read</td>
          </tr>
          <tr v-else-if="!canReadVars">
            <td colspan="6" class="muted">
              Missing capability: vars.read (runtime states unavailable)
            </td>
          </tr>
          <tr v-else-if="loading">
            <td colspan="6" class="muted">Loading.</td>
          </tr>
          <tr v-else-if="!devices.length">
            <td colspan="6" class="muted">No devices.</td>
          </tr>
          <tr
            v-else
            v-for="device in devices"
            :key="device.id"
            v-memo="[device.__sig]"
            :class="device.state === 'claimed' ? 'row-clickable' : ''"
            @click="onRowClick(device)"
          >
            <td>{{ device.id }}</td>
            <td>
              <router-link :to="`/devices/${device.id}`" @click.stop>
                {{ device.device_uid }}
              </router-link>
            </td>
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
    </section>
  </div>
</template>

<style scoped>
.row-clickable {
  cursor: pointer;
}
.status-line,
.section-status {
  min-height: 24px;
  display: flex;
  align-items: center;
}
.table-fixed {
  table-layout: fixed;
  width: 100%;
}
.entities-table th,
.entities-table td,
.devices-table th,
.devices-table td {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: middle;
}
.entities-table tbody tr,
.devices-table tbody tr {
  height: 36px;
}
.entities-table td,
.devices-table td {
  line-height: 36px;
}
.row {
  display: flex;
  flex-wrap: nowrap;
  gap: 6px;
  overflow: hidden;
}
.row .pill {
  flex: 0 0 auto;
  display: inline-block;
  white-space: nowrap;
}
.entities-table th:nth-child(1),
.entities-table td:nth-child(1) {
  width: 140px;
}
.entities-table th:nth-child(2),
.entities-table td:nth-child(2) {
  width: 120px;
}
.entities-table th:nth-child(3),
.entities-table td:nth-child(3) {
  width: 220px;
}
.entities-table th:nth-child(4),
.entities-table td:nth-child(4) {
  width: auto;
}
.devices-table th:nth-child(1),
.devices-table td:nth-child(1) {
  width: 70px;
}
.devices-table th:nth-child(2),
.devices-table td:nth-child(2) {
  width: 220px;
}
.devices-table th:nth-child(3),
.devices-table td:nth-child(3) {
  width: 110px;
}
.devices-table th:nth-child(4),
.devices-table td:nth-child(4) {
  width: 260px;
}
.devices-table th:nth-child(5),
.devices-table td:nth-child(5) {
  width: 120px;
}
.devices-table th:nth-child(6),
.devices-table td:nth-child(6) {
  width: 160px;
}
</style>


