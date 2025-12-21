<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiFetch, getToken } from "../lib/api";
import { mapErrorToUserText, parseApiError } from "../lib/errors";
import { getDeviceVariables, putValue, VariableValue } from "../lib/variables";

const route = useRoute();
const router = useRouter();
const deviceId = route.params.id as string;

type DeviceInfo = {
  id: number;
  device_uid: string;
  last_seen_at: string | null;
  health: "ok" | "stale" | "dead";
  last_seen_age_seconds: number | null;
  state?: "unprovisioned" | "provisioned_unclaimed" | "pairing_active" | "claimed" | "busy";
  pairing_active?: boolean;
  busy?: boolean;
};

type TelemetryItem = {
  id: number;
  received_at?: string;
  created_at?: string;
  event_type?: string | null;
  payload?: Record<string, any> | null;
};

type CurrentTaskOut = {
  has_active_lease: boolean;
  device_id: number;
  task_id: number | null;
  task_name: string | null;
  task_type: string | null;
  task_status: string | null;
  claimed_at: string | null;
  lease_expires_at: string | null;
  lease_seconds_remaining: number | null;
  lease_token_hint: string | null;
  context_key: string | null;
};

type TaskHistoryItemOut = {
  task_id: number;
  task_name: string;
  task_type: string;
  task_status: string;
  claimed_at: string | null;
  finished_at: string | null;
  last_seen_at: string | null;
};

const deviceInfo = ref<DeviceInfo | null>(null);
const deviceInfoError = ref<string | null>(null);

const telemetry = ref<TelemetryItem[]>([]);
const telemetryError = ref<string | null>(null);

const currentTask = ref<CurrentTaskOut | null>(null);
const currentTaskError = ref<string | null>(null);
const taskHistory = ref<TaskHistoryItemOut[]>([]);
const taskHistoryError = ref<string | null>(null);
const variablesError = ref<string | null>(null);
const variablesLoading = ref(false);
type EffectiveVariable = VariableValue & { source: "global" | "device" };
const variables = ref<EffectiveVariable[]>([]);
const leaseSecondsRemaining = ref<number | null>(null);
const expandedTelemetry = ref<Set<number>>(new Set());
const isLeaseExpiredLocally = computed(() => {
  const s = leaseSecondsRemaining.value;
  if (s === null) return false;
  return s <= 0;
});

let ws: WebSocket | null = null;
let mounted = false;
let reconnectTimer: number | null = null;
let reconnectAttempt = 0;
let heartbeatTimer: number | null = null;
let deviceInfoTimer: number | null = null;
let lastDeviceInfoRefreshMs = 0;
let taskStatusTimer: number | null = null;
let leaseCountdownTimer: number | null = null;
let lastCurrentTaskRefreshMs = 0;
let lastTaskHistoryRefreshMs = 0;
let lastVariablesRefreshMs = 0;
const editingVarKey = ref<string | null>(null);
const editingVarValue = ref<string>("");

function buildWsUrl(token: string): string {
  const apiBase = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000/api/v1";
  const u = new URL(apiBase);
  u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
  const basePath = u.pathname.replace(/\/+$/, "");
  const prefix = basePath && basePath !== "/" ? basePath : "/api/v1";
  u.pathname = `${prefix}/telemetry/devices/${deviceId}/telemetry/ws`;
  u.search = `token=${encodeURIComponent(token)}`;
  return u.toString();
}

function cleanupWs() {
  if (heartbeatTimer !== null) {
    window.clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
  if (ws) {
    try { ws.onopen = ws.onmessage = ws.onerror = ws.onclose = null; } catch {}
    try { ws.close(); } catch {}
  }
  ws = null;
}

function scheduleReconnect(reason: string) {
  if (!mounted) return;
  if (reconnectTimer !== null) return;
  telemetryError.value = reason;
  const delay = Math.min(5000, 250 * Math.pow(2, reconnectAttempt));
  reconnectAttempt = Math.min(reconnectAttempt + 1, 6);
  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = null;
    connectWs();
  }, delay);
}

function refreshDeviceInfoDebounced() {
  const now = Date.now();
  if (now - lastDeviceInfoRefreshMs < 1000) return;
  lastDeviceInfoRefreshMs = now;
  loadDeviceInfo();
}

function refreshCurrentTaskDebounced() {
  const now = Date.now();
  if (now - lastCurrentTaskRefreshMs < 1000) return;
  lastCurrentTaskRefreshMs = now;
  loadCurrentTask();
}

function refreshTaskHistoryDebounced() {
  const now = Date.now();
  if (now - lastTaskHistoryRefreshMs < 2000) return;
  lastTaskHistoryRefreshMs = now;
  loadTaskHistory();
}

function refreshVariablesDebounced() {
  const now = Date.now();
  if (now - lastVariablesRefreshMs < 1000) return;
  lastVariablesRefreshMs = now;
  loadVariables();
}

function connectWs() {
  if (!mounted) return;
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  cleanupWs();

  const token = getToken();
  if (!token) {
    scheduleReconnect("no token");
    return;
  }

  const url = buildWsUrl(token);
  ws = new WebSocket(url);

  ws.onopen = () => {
    telemetryError.value = null;
    reconnectAttempt = 0;
    heartbeatTimer = window.setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        try { ws.send("ping"); } catch {}
      }
    }, 25000);
  };

  ws.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data);
      if (Array.isArray(data)) {
        telemetry.value = data;
      } else if (data && typeof data === "object") {
        telemetry.value = [...telemetry.value, data].slice(-5);
        refreshDeviceInfoDebounced();
        refreshCurrentTaskDebounced();
        refreshTaskHistoryDebounced();
        refreshVariablesDebounced();
      }
    } catch {
      // ignore
    }
  };

  ws.onerror = () => {
    telemetryError.value = "ws error";
    scheduleReconnect("ws error");
  };

  ws.onclose = (ev) => {
    cleanupWs();
    scheduleReconnect(`ws closed (${ev.code})`);
  };
}

async function loadDeviceInfo() {
  deviceInfoError.value = null;
  try {
    deviceInfo.value = await apiFetch<DeviceInfo>(`/api/v1/devices/${deviceId}`);
    loadVariables();
  } catch (e: any) {
    deviceInfoError.value = formatApiError(e, "Failed to load device");
  }
}

function stopLeaseCountdown() {
  if (leaseCountdownTimer !== null) {
    window.clearInterval(leaseCountdownTimer);
    leaseCountdownTimer = null;
  }
}

function startLeaseCountdown() {
  stopLeaseCountdown();
  if (!currentTask.value?.has_active_lease) return;
  if (leaseSecondsRemaining.value === null) return;
  if (leaseSecondsRemaining.value <= 0) {
    leaseSecondsRemaining.value = 0;
    return;
  }
  leaseCountdownTimer = window.setInterval(() => {
    if (leaseSecondsRemaining.value === null) return;
    leaseSecondsRemaining.value -= 1;
    if (leaseSecondsRemaining.value <= 0) {
      leaseSecondsRemaining.value = 0;
      stopLeaseCountdown();
    }
  }, 1000);
}

async function loadCurrentTask() {
  currentTaskError.value = null;
  try {
    const res = await apiFetch<CurrentTaskOut>(`/api/v1/devices/${deviceId}/current-task`);
    currentTask.value = res;
    leaseSecondsRemaining.value = res.lease_seconds_remaining ?? null;
    startLeaseCountdown();
  } catch (e: any) {
    currentTaskError.value = formatApiError(e, "Failed to load current task");
  }
}

async function loadTaskHistory() {
  taskHistoryError.value = null;
  try {
    taskHistory.value = await apiFetch<TaskHistoryItemOut[]>(
      `/api/v1/devices/${deviceId}/task-history?limit=5`
    );
  } catch (e: any) {
    taskHistoryError.value = formatApiError(e, "Failed to load task history");
  }
}

async function loadVariables() {
  const uid = deviceInfo.value?.device_uid;
  if (!uid) return;
  variablesError.value = null;
  variablesLoading.value = true;
  try {
    const res = await getDeviceVariables(uid);
    const merged = [
      ...res.globals.map((item) => ({ ...item, source: "global" as const })),
      ...res.device.map((item) => ({ ...item, source: "device" as const })),
    ];
    variables.value = merged;
  } catch (e: any) {
    variablesError.value = formatApiError(e, "Failed to load variables");
  } finally {
    variablesLoading.value = false;
  }
}

function openEditVariable(row: EffectiveVariable) {
  editingVarKey.value = row.key;
  editingVarValue.value = JSON.stringify(row.value ?? "");
}

function closeEditVariable() {
  editingVarKey.value = null;
  editingVarValue.value = "";
}

function parseValueInput(raw: string) {
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

async function saveVariableOverride(row: EffectiveVariable) {
  if (!deviceInfo.value?.device_uid) return;
  variablesError.value = null;
  try {
    await putValue({
      key: row.key,
      scope: "device",
      deviceUid: deviceInfo.value.device_uid,
      value: parseValueInput(editingVarValue.value),
      expectedVersion: row.version ?? undefined,
    });
    closeEditVariable();
    loadVariables();
  } catch (e: any) {
    variablesError.value = formatApiError(e, "Failed to update variable");
  }
}

async function clearVariableOverride(row: EffectiveVariable) {
  if (!deviceInfo.value?.device_uid) return;
  if (!confirm("Clear override?")) return;
  variablesError.value = null;
  try {
    await putValue({
      key: row.key,
      scope: "device",
      deviceUid: deviceInfo.value.device_uid,
      value: null,
      expectedVersion: row.version ?? undefined,
    });
    closeEditVariable();
    loadVariables();
  } catch (e: any) {
    variablesError.value = formatApiError(e, "Failed to clear override");
  }
}

function variableValueText(row: EffectiveVariable) {
  if (row.is_secret) return "***";
  if (row.value === null || row.value === undefined) return "-";
  if (typeof row.value === "string") return row.value;
  return JSON.stringify(row.value);
}

function variableSourceLabel(row: EffectiveVariable) {
  return row.source === "device" ? "device" : "global";
}

function fmtTime(iso: string) {
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

function healthClass(health: "ok" | "stale" | "dead") {
  if (health === "ok") return "pill-ok";
  if (health === "stale") return "pill-warn";
  return "pill-bad";
}

function stateClass(state: DeviceInfo["state"]) {
  if (!state) return "pill-warn";
  if (state === "busy" || state === "unprovisioned") return "pill-bad";
  if (state === "claimed") return "pill-ok";
  if (state === "pairing_active" || state === "provisioned_unclaimed") return "pill-warn";
  return "pill-warn";
}

function fmtAge(ageSeconds: number | null) {
  if (ageSeconds === null) return "-";
  if (ageSeconds < 60) return `${ageSeconds}s ago`;
  if (ageSeconds < 3600) return `${Math.floor(ageSeconds / 60)}m ago`;
  return `${Math.floor(ageSeconds / 3600)}h ago`;
}

function fmtRemaining(seconds: number | null) {
  if (seconds === null) return "-";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

function fmtAgoFromIso(iso: string | null) {
  if (!iso) return "-";
  const dt = new Date(iso);
  if (!Number.isFinite(dt.getTime())) return "-";
  const diffSeconds = Math.max(0, Math.floor((Date.now() - dt.getTime()) / 1000));
  return fmtAge(diffSeconds);
}

function historyStatusClass(status: string) {
  const s = (status || "").toLowerCase();
  if (["done", "success", "succeeded", "completed"].includes(s)) return "pill-ok";
  if (["failed", "error", "cancelled", "canceled", "timeout", "timed_out"].includes(s)) {
    return "pill-bad";
  }
  return "pill-warn";
}

function formatApiError(err: any, fallback: string) {
  const info = parseApiError(err);
  const mapped = mapErrorToUserText(info, fallback);
  const statusLabel = info.httpStatus ? `HTTP ${info.httpStatus}` : "HTTP ?";
  const detailText = (info.message || "").slice(0, 200);
  const codeText = info.code ? ` ${info.code}` : "";
  const metaText = info.meta ? ` ${JSON.stringify(info.meta)}` : "";
  const suffix = detailText ? `${statusLabel}: ${detailText}` : statusLabel;
  if (mapped !== fallback) return `${mapped} (${suffix}${codeText}${metaText})`;
  return `${fallback} (${suffix}${codeText}${metaText})`;
}

function currentTaskStatusClass() {
  const task = currentTask.value;
  if (!task || !task.has_active_lease) return "pill-bad";
  if (isLeaseExpiredLocally.value) return "pill-bad";
  const status = (task.task_status || "").toLowerCase();
  if (status.includes("fail") || status.includes("error") || status.includes("cancel")) {
    return "pill-bad";
  }
  if (leaseSecondsRemaining.value !== null && leaseSecondsRemaining.value <= 30) {
    return "pill-warn";
  }
  return "pill-ok";
}

function refreshNow() {
  loadDeviceInfo();
  loadCurrentTask();
  loadTaskHistory();
}

async function copyUid() {
  const uid = deviceInfo.value?.device_uid;
  if (!uid) return;
  try {
    await navigator.clipboard.writeText(uid);
  } catch {
    // ignore
  }
}

function openPairingPanel() {
  const uid = deviceInfo.value?.device_uid;
  if (!uid) return;
  router.push({ path: "/devices", query: { uid } });
}

function isTelemetryExpanded(id: number) {
  return expandedTelemetry.value.has(id);
}

function toggleTelemetry(id: number) {
  const next = new Set(expandedTelemetry.value);
  if (next.has(id)) {
    next.delete(id);
  } else {
    next.add(id);
  }
  expandedTelemetry.value = next;
}

function payloadPreview(payload: Record<string, any> | null | undefined, expanded: boolean) {
  if (!payload) return "-";
  const text = JSON.stringify(payload);
  if (expanded) return text;
  if (text.length <= 120) return text;
  return text.slice(0, 120) + "...";
}

function fmtRelative(iso: string | undefined) {
  if (!iso) return "-";
  return fmtAgoFromIso(iso);
}

function onVisibilityChange() {
  if (document.visibilityState === "visible") {
    loadCurrentTask();
    loadTaskHistory();
    loadVariables();
    startLeaseCountdown();
  }
}

onMounted(() => {
  mounted = true;
  loadDeviceInfo();
  deviceInfoTimer = window.setInterval(loadDeviceInfo, 5000);
  loadCurrentTask();
  loadTaskHistory();
  taskStatusTimer = window.setInterval(() => {
    loadCurrentTask();
    loadTaskHistory();
  }, 5000);
  connectWs();
  document.addEventListener("visibilitychange", onVisibilityChange);
});

onUnmounted(() => {
  mounted = false;
  if (reconnectTimer !== null) {
    window.clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (deviceInfoTimer !== null) {
    window.clearInterval(deviceInfoTimer);
    deviceInfoTimer = null;
  }
  if (taskStatusTimer !== null) {
    window.clearInterval(taskStatusTimer);
    taskStatusTimer = null;
  }
  stopLeaseCountdown();
  cleanupWs();
  document.removeEventListener("visibilitychange", onVisibilityChange);
});
</script>

<template>
  <div class="card">
    <div class="card-header-row">
      <h2>Device Detail</h2>
      <div class="pill-group">
        <span
          v-if="deviceInfo?.health"
          :class="['pill', healthClass(deviceInfo.health)]"
        >
          {{ deviceInfo.health }}
        </span>
        <span v-if="deviceInfo?.state" :class="['pill', stateClass(deviceInfo.state)]">
          {{ deviceInfo.state }}
        </span>
        <span :class="['pill', currentTaskStatusClass()]">
          {{
            currentTask?.has_active_lease && !isLeaseExpiredLocally
              ? (currentTask?.task_status ?? "active")
              : "no lease"
          }}
        </span>
      </div>
    </div>

    <div class="card-actions">
      <button class="btn secondary" @click="refreshNow">Refresh now</button>
      <button class="btn secondary" :disabled="!deviceInfo?.device_uid" @click="copyUid">
        Copy UID
      </button>
      <button
        v-if="deviceInfo?.state === 'pairing_active'"
        class="btn secondary"
        @click="openPairingPanel"
      >
        Open pairing panel
      </button>
    </div>

    <div v-if="deviceInfoError" class="error">{{ deviceInfoError }}</div>
    <div v-else class="info-grid">
      <div class="info-item">
        <div class="info-label">ID</div>
        <div class="info-value">{{ deviceInfo?.id ?? deviceId }}</div>
      </div>
      <div class="info-item">
        <div class="info-label">UID</div>
        <div class="info-value">{{ deviceInfo?.device_uid ?? "-" }}</div>
      </div>
      <div class="info-item">
        <div class="info-label">Last seen</div>
        <div class="info-value">{{ fmtAge(deviceInfo?.last_seen_age_seconds ?? null) }}</div>
      </div>
      <div class="info-item">
        <div class="info-label">Lease expires in</div>
        <div class="info-value">
          {{ currentTask?.has_active_lease && !isLeaseExpiredLocally ? fmtRemaining(leaseSecondsRemaining) : "-" }}
        </div>
      </div>
      <div class="info-item">
        <div class="info-label">Current task</div>
        <div class="info-value">
          <span v-if="currentTask?.has_active_lease && !isLeaseExpiredLocally">
            {{ currentTask?.task_name ?? "-" }}
            <span v-if="currentTask?.task_type && currentTask.task_type !== currentTask.task_name">
              ({{ currentTask.task_type }})
            </span>
          </span>
          <span v-else>none</span>
        </div>
      </div>
    </div>

    <div class="section-divider"></div>
    <div style="margin-bottom: 14px;">
      <strong>Effective Variables</strong>
      <div v-if="variablesError" class="error" style="margin-top: 6px;">
        {{ variablesError }}
      </div>
      <div v-else-if="variablesLoading" style="margin-top: 6px;">Loading...</div>
      <table v-else class="table" style="margin-top: 6px;">
        <thead>
          <tr>
            <th>Key</th>
            <th>Value</th>
            <th>Source</th>
            <th>Version</th>
            <th>Updated</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in variables" :key="row.key + row.scope">
            <td>{{ row.key }}</td>
            <td>
              <span v-if="editingVarKey === row.key">
                <input v-model="editingVarValue" class="input" />
              </span>
              <span v-else>{{ variableValueText(row) }}</span>
            </td>
            <td>{{ variableSourceLabel(row) }}</td>
            <td>{{ row.version ?? "-" }}</td>
            <td>{{ row.updated_at ? fmtTime(row.updated_at) : "-" }}</td>
            <td>
              <template v-if="editingVarKey === row.key">
                <button class="btn secondary" @click="saveVariableOverride(row)">Save</button>
                <button class="btn secondary" @click="closeEditVariable">Cancel</button>
              </template>
              <template v-else>
                <button class="btn secondary" @click="openEditVariable(row)">
                  {{ row.source === "global" ? "Edit override" : "Edit" }}
                </button>
                <button
                  v-if="row.source === 'device'"
                  class="btn secondary"
                  @click="clearVariableOverride(row)"
                >
                  Delete override
                </button>
              </template>
            </td>
          </tr>
          <tr v-if="variables.length === 0">
            <td colspan="6">No variables</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="section-divider"></div>
    <div style="margin-bottom: 14px;">
      <strong>Current Task + Lease</strong>
      <div v-if="deviceInfo?.state === 'busy'" class="pairing-warn" style="margin-top: 6px;">
        Device busy (task running)
      </div>
      <div v-if="currentTaskError" class="error" style="margin-top: 6px;">
        {{ currentTaskError }}
      </div>
      <div style="margin-top: 6px;">
        <div><strong>Status:</strong> {{ currentTask?.task_status ?? "no lease" }}</div>
        <div><strong>Lease expires in:</strong> {{ currentTask?.has_active_lease && !isLeaseExpiredLocally ? fmtRemaining(leaseSecondsRemaining) : "-" }}</div>
      </div>
    </div>

    <div v-if="taskHistoryError" class="error">{{ taskHistoryError }}</div>
    <div class="section-divider"></div>
    <div style="margin-bottom: 14px;">
      <strong>Recent Tasks</strong>
      <div v-if="taskHistory.length === 0" style="margin-top: 6px;">No recent tasks</div>
      <table v-else class="table" style="margin-top: 6px;">
        <thead>
          <tr>
            <th>Task</th>
            <th>Status</th>
            <th>When</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in taskHistory" :key="t.task_id">
            <td>
              {{ t.task_name }}
              <span v-if="t.task_type !== t.task_name">({{ t.task_type }})</span>
            </td>
            <td>
              <span :class="['pill', historyStatusClass(t.task_status)]">
                {{ t.task_status }}
              </span>
            </td>
            <td>
              <span v-if="t.finished_at">finished {{ fmtAgoFromIso(t.finished_at) }}</span>
              <span v-else-if="t.claimed_at">claimed {{ fmtAgoFromIso(t.claimed_at) }}</span>
              <span v-else>-</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="section-divider"></div>
    <strong>Telemetry</strong>
    <div v-if="telemetryError" class="error" style="margin-top: 6px;">{{ telemetryError }}</div>
    <table class="table">
      <thead>
        <tr>
          <th>Time</th>
          <th>Type</th>
          <th>Payload</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="t in telemetry" :key="t.id">
          <td :title="fmtTime(t.received_at || t.created_at || '')">
            {{ fmtRelative(t.received_at || t.created_at) }}
          </td>
          <td>{{ t.event_type || "-" }}</td>
          <td>
            <span class="payload-preview">{{ payloadPreview(t.payload, isTelemetryExpanded(t.id)) }}</span>
            <button class="link-button" @click="toggleTelemetry(t.id)">
              {{ isTelemetryExpanded(t.id) ? "Collapse" : "Expand" }}
            </button>
          </td>
        </tr>
        <tr v-if="telemetry.length === 0">
          <td colspan="3">No telemetry yet</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
