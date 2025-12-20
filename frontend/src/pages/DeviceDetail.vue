<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";
import { apiFetch, getToken } from "../lib/api";

const route = useRoute();
const deviceId = route.params.id as string;

type DeviceInfo = {
  id: number;
  device_uid: string;
  last_seen_at: string | null;
  health: "ok" | "stale" | "dead";
  last_seen_age_seconds: number | null;
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
const leaseSecondsRemaining = ref<number | null>(null);
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
  } catch (e: any) {
    deviceInfoError.value = e?.message || String(e);
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
    currentTaskError.value = e?.message || String(e);
  }
}

async function loadTaskHistory() {
  taskHistoryError.value = null;
  try {
    taskHistory.value = await apiFetch<TaskHistoryItemOut[]>(
      `/api/v1/devices/${deviceId}/task-history?limit=5`
    );
  } catch (e: any) {
    taskHistoryError.value = e?.message || String(e);
  }
}

function fmtTime(iso: string) {
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

function fmtTemp(value: any) {
  if (value === null || value === undefined || value === "") return "-";
  return `${value} \u00b0C`;
}

function fmtHumidity(value: any) {
  if (value === null || value === undefined || value === "") return "-";
  return `${value} %`;
}

function healthClass(health: "ok" | "stale" | "dead") {
  if (health === "ok") return "pill-ok";
  if (health === "stale") return "pill-warn";
  return "pill-bad";
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

function onVisibilityChange() {
  if (document.visibilityState === "visible") {
    loadCurrentTask();
    loadTaskHistory();
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
    <h2>Device Telemetry (last 5)</h2>

    <div v-if="deviceInfoError" class="error">{{ deviceInfoError }}</div>
    <div v-else class="row" style="margin-bottom: 12px;">
      <div><strong>ID:</strong> {{ deviceInfo?.id ?? deviceId }}</div>
      <div v-if="deviceInfo?.device_uid"><strong>UID:</strong> {{ deviceInfo.device_uid }}</div>
      <div>
        <strong>Health:</strong>
        <span
          :class="['pill', healthClass(deviceInfo?.health ?? 'dead')]"
          style="margin-left: 6px;"
        >
          {{ deviceInfo?.health ?? "dead" }}
        </span>
      </div>
      <div>
        <strong>Last seen:</strong>
        {{ fmtAge(deviceInfo?.last_seen_age_seconds ?? null) }}
      </div>
    </div>

    <div v-if="currentTaskError" class="error">{{ currentTaskError }}</div>
    <div class="row" style="margin-bottom: 10px;">
      <div>
        <strong>Current Task:</strong>
        <span v-if="currentTask?.has_active_lease && !isLeaseExpiredLocally">
          Running: {{ currentTask?.task_name ?? "-" }}
          <span v-if="currentTask?.task_type && currentTask.task_type !== currentTask.task_name">
            ({{ currentTask.task_type }})
          </span>
        </span>
        <span v-else>none</span>
      </div>
      <div>
        <span :class="['pill', currentTaskStatusClass()]" style="margin-left: 6px;">
          {{
            currentTask?.has_active_lease && !isLeaseExpiredLocally
              ? (currentTask?.task_status ?? "active")
              : "no lease"
          }}
        </span>
      </div>
      <div>
        <strong>Lease expires in:</strong>
        {{ currentTask?.has_active_lease && !isLeaseExpiredLocally ? fmtRemaining(leaseSecondsRemaining) : "-" }}
      </div>
    </div>

    <div v-if="taskHistoryError" class="error">{{ taskHistoryError }}</div>
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

    <div v-if="telemetryError" class="error">{{ telemetryError }}</div>

    <table class="table">
      <thead>
        <tr>
          <th>Time</th>
          <th>Temperature</th>
          <th>Humidity</th>
          <th>Event Type</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="t in telemetry" :key="t.id">
          <td>{{ fmtTime(t.received_at || t.created_at || "") }}</td>
          <td>{{ fmtTemp(t.payload?.temperature) }}</td>
          <td>{{ fmtHumidity(t.payload?.humidity) }}</td>
          <td>{{ t.event_type || "-" }}</td>
        </tr>
        <tr v-if="telemetry.length === 0">
          <td colspan="4">No telemetry yet</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
