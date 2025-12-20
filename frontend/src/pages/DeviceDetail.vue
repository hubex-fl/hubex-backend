<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
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

const deviceInfo = ref<DeviceInfo | null>(null);
const deviceInfoError = ref<string | null>(null);

const telemetry = ref<TelemetryItem[]>([]);
const telemetryError = ref<string | null>(null);

let ws: WebSocket | null = null;
let mounted = false;
let reconnectTimer: number | null = null;
let reconnectAttempt = 0;
let heartbeatTimer: number | null = null;
let deviceInfoTimer: number | null = null;
let lastDeviceInfoRefreshMs = 0;

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

onMounted(() => {
  mounted = true;
  loadDeviceInfo();
  deviceInfoTimer = window.setInterval(loadDeviceInfo, 5000);
  connectWs();
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
  cleanupWs();
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
