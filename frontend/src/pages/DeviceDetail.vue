<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiFetch, getToken } from "../lib/api";
import { mapErrorToUserText, parseApiError } from "../lib/errors";
import {
  getEffectiveVariables,
  putValue,
  EffectiveVariable as EffectiveVariableOut,
} from "../lib/variables";

const route = useRoute();
const router = useRouter();
const deviceId = ref(route.params.id as string);

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
const variables = ref<EffectiveVariableOut[]>([]);
const variablesSnapshotId = ref<string | null>(null);
const variablesAppliedSummary = ref<string | null>(null);
const variablesSorted = computed(() =>
  [...variables.value].sort((a, b) => a.key.localeCompare(b.key))
);
const revealVariableKeys = ref<Set<string>>(new Set());
const addOverrideOpen = ref(false);
const addOverrideKey = ref("");
const addOverrideValue = ref("");
const addOverrideError = ref<string | null>(null);
const leaseSecondsRemaining = ref<number | null>(null);
const expandedTelemetry = ref<Set<number>>(new Set());
const isLeaseExpiredLocally = computed(() => {
  const s = leaseSecondsRemaining.value;
  if (s === null) return false;
  return s <= 0;
});
const overrideDisabled = computed(() => deviceInfo.value?.state === "unprovisioned");
const overrideKeyOptions = computed(() => {
  const keys = new Set<string>();
  for (const item of variables.value) keys.add(item.key);
  return Array.from(keys).sort();
});

let ws: WebSocket | null = null;
let mounted = false;
let reconnectTimer: number | null = null;
let reconnectAttempt = 0;
let heartbeatTimer: number | null = null;
let leaseCountdownTimer: number | null = null;
const POLL_INTERVAL_MS = 2500;
const MAX_BACKOFF_MS = 15000;
const inflightControllers = new Map<string, AbortController>();
let pollTimer: number | null = null;
let pollBackoffMs = 0;
let pollInFlight = false;
let pendingRefresh = false;
let lastRefreshRequestMs = 0;
const editingVarKey = ref<string | null>(null);
const editingVarValue = ref<string>("");

function buildWsUrl(token: string): string {
  const apiBase = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000/api/v1";
  const u = new URL(apiBase);
  u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
  const basePath = u.pathname.replace(/\/+$/, "");
  const prefix = basePath && basePath !== "/" ? basePath : "/api/v1";
  u.pathname = `${prefix}/telemetry/devices/${deviceId.value}/telemetry/ws`;
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
  const baseDelay = Math.min(10000, 250 * Math.pow(2, reconnectAttempt));
  const jitter = Math.floor(Math.random() * 200);
  const delay = baseDelay + jitter;
  reconnectAttempt = Math.min(reconnectAttempt + 1, 6);
  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = null;
    connectWs();
  }, delay);
}

function abortInflight(key?: string) {
  if (key) {
    const controller = inflightControllers.get(key);
    if (controller) {
      controller.abort();
      inflightControllers.delete(key);
    }
    return;
  }
  for (const [k, controller] of inflightControllers.entries()) {
    controller.abort();
    inflightControllers.delete(k);
  }
}

async function guardedFetch<T>(
  key: string,
  fn: (signal: AbortSignal) => Promise<T>
): Promise<T | undefined> {
  if (inflightControllers.has(key)) return undefined;
  const controller = new AbortController();
  inflightControllers.set(key, controller);
  try {
    return await fn(controller.signal);
  } catch (err: any) {
    if (err?.name === "AbortError") return undefined;
    throw err;
  } finally {
    inflightControllers.delete(key);
  }
}

function requestRefreshAllThrottled() {
  const now = Date.now();
  if (document.visibilityState === "hidden") return;
  if (now - lastRefreshRequestMs < 1000) return;
  lastRefreshRequestMs = now;
  refreshAll("ws");
}

function stopPolling() {
  if (pollTimer !== null) {
    window.clearTimeout(pollTimer);
    pollTimer = null;
  }
}

function scheduleNextPoll() {
  if (!mounted) return;
  if (document.visibilityState === "hidden") return;
  if (pollTimer !== null) return;
  const delay = pollBackoffMs > 0 ? pollBackoffMs : POLL_INTERVAL_MS;
  pollTimer = window.setTimeout(async () => {
    pollTimer = null;
    await refreshAll("poll");
    scheduleNextPoll();
  }, delay);
}

async function refreshAll(reason: string) {
  if (!mounted) return;
  if (pollInFlight) {
    pendingRefresh = true;
    return;
  }
  pollInFlight = true;
  let hadError = false;
  const [deviceOk, taskOk, historyOk, varsOk] = await Promise.all([
    loadDeviceInfo(),
    loadCurrentTask(),
    loadTaskHistory(),
    loadVariables(),
  ]);
  if (deviceOk === false || taskOk === false || historyOk === false || varsOk === false) {
    hadError = true;
  }
  pollBackoffMs = hadError
    ? Math.min(MAX_BACKOFF_MS, pollBackoffMs > 0 ? pollBackoffMs * 2 : POLL_INTERVAL_MS)
    : 0;
  pollInFlight = false;
  if (pendingRefresh) {
    pendingRefresh = false;
    refreshAll("queued");
  }
}

function startPolling() {
  stopPolling();
  scheduleNextPoll();
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
    requestRefreshAllThrottled();
  };

  ws.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data);
      if (Array.isArray(data)) {
        telemetry.value = data;
      } else if (data && typeof data === "object") {
        telemetry.value = [...telemetry.value, data].slice(-5);
        requestRefreshAllThrottled();
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

function isSameDeviceInfo(a: DeviceInfo | null, b: DeviceInfo | null) {
  if (!a || !b) return false;
  return (
    a.id === b.id &&
    a.device_uid === b.device_uid &&
    a.last_seen_at === b.last_seen_at &&
    a.health === b.health &&
    a.state === b.state &&
    a.pairing_active === b.pairing_active &&
    a.busy === b.busy
  );
}

function isSameCurrentTask(a: CurrentTaskOut | null, b: CurrentTaskOut | null) {
  if (!a || !b) return false;
  return (
    a.task_id === b.task_id &&
    a.task_status === b.task_status &&
    a.lease_expires_at === b.lease_expires_at &&
    a.has_active_lease === b.has_active_lease
  );
}

function isSameTaskHistory(a: TaskHistoryItemOut[], b: TaskHistoryItemOut[]) {
  if (a.length !== b.length) return false;
  if (a.length === 0) return true;
  return a[0].task_id === b[0].task_id;
}

function hasVariablesChanged(next: EffectiveVariableOut[], snapshotId: string | null) {
  if (!snapshotId || snapshotId !== variablesSnapshotId.value) return true;
  if (next.length !== variables.value.length) return true;
  const currentMap = new Map(
    variables.value.map((item) => [
      item.key,
      `${item.version ?? "n"}|${item.source}|${item.updated_at ?? ""}`,
    ])
  );
  for (const item of next) {
    const sig = `${item.version ?? "n"}|${item.source}|${item.updated_at ?? ""}`;
    if (currentMap.get(item.key) !== sig) return true;
  }
  return false;
}

async function loadDeviceInfo(): Promise<boolean> {
  deviceInfoError.value = null;
  try {
    const res = await guardedFetch("deviceInfo", (signal) =>
      apiFetch<DeviceInfo>(`/api/v1/devices/${deviceId.value}`, { signal })
    );
    if (!res) return true;
    if (!isSameDeviceInfo(deviceInfo.value, res)) {
      deviceInfo.value = res;
    }
    return true;
  } catch (e: any) {
    deviceInfoError.value = formatApiError(e, "Failed to load device");
    return false;
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

async function loadCurrentTask(): Promise<boolean> {
  currentTaskError.value = null;
  try {
    const res = await guardedFetch("currentTask", (signal) =>
      apiFetch<CurrentTaskOut>(`/api/v1/devices/${deviceId.value}/current-task`, { signal })
    );
    if (!res) return true;
    if (!isSameCurrentTask(currentTask.value, res)) {
      currentTask.value = res;
      leaseSecondsRemaining.value = res.lease_seconds_remaining ?? null;
      startLeaseCountdown();
    } else if (leaseSecondsRemaining.value === null && res.lease_seconds_remaining !== null) {
      leaseSecondsRemaining.value = res.lease_seconds_remaining;
      startLeaseCountdown();
    }
    return true;
  } catch (e: any) {
    currentTaskError.value = formatApiError(e, "Failed to load current task");
    return false;
  }
}

async function loadTaskHistory(): Promise<boolean> {
  taskHistoryError.value = null;
  try {
    const res = await guardedFetch("taskHistory", (signal) =>
      apiFetch<TaskHistoryItemOut[]>(
        `/api/v1/devices/${deviceId.value}/task-history?limit=5`,
        { signal }
      )
    );
    if (!res) return true;
    if (!isSameTaskHistory(taskHistory.value, res)) {
      taskHistory.value = res;
    }
    return true;
  } catch (e: any) {
    taskHistoryError.value = formatApiError(e, "Failed to load task history");
    return false;
  }
}

async function loadVariables(): Promise<boolean> {
  const uid = deviceInfo.value?.device_uid;
  if (!uid) return true;
  variablesError.value = null;
  addOverrideError.value = null;
  try {
    variablesLoading.value = true;
    const res = await guardedFetch("variables", () => getEffectiveVariables(uid));
    if (!res) {
      variablesLoading.value = false;
      return true;
    }
    const snapshot = (res as any).snapshot_id ?? (res as any).snapshotId ?? null;
    const snapshotChanged = snapshot !== variablesSnapshotId.value;
    const changed = hasVariablesChanged(res.items, snapshot);
    if (changed) {
      variablesSnapshotId.value = snapshot;
      upsertEffectiveItems(res.items);
      const allowedKeys = new Set(res.items.map((item: EffectiveVariableOut) => item.key));
      const nextReveal = new Set(Array.from(revealVariableKeys.value).filter((k) => allowedKeys.has(k)));
      revealVariableKeys.value = nextReveal;
    }
    if (snapshotChanged || variablesAppliedSummary.value === null) {
      await loadVariablesApplied(uid);
    }
    variablesLoading.value = false;
    return true;
  } catch (e: any) {
    variablesError.value = formatApiError(e, "Failed to load variables");
    variablesSnapshotId.value = null;
    variablesAppliedSummary.value = null;
    variablesLoading.value = false;
    return false;
  } finally {
    variablesLoading.value = false;
  }
}

async function loadVariablesApplied(uid: string): Promise<void> {
  try {
    const res = await guardedFetch("varsApplied", (signal) =>
      apiFetch<any[]>(`/api/v1/variables/applied?deviceUid=${uid}&limit=1`, { signal })
    );
    if (!res) return;
    const latest = Array.isArray(res) ? res[0] : null;
    if (!latest) {
      variablesAppliedSummary.value = null;
      return;
    }
    const appliedCount = Array.isArray(latest.applied) ? latest.applied.length : (latest.applied_count ?? 0);
    const failedCount = Array.isArray(latest.failed) ? latest.failed.length : (latest.failed_count ?? 0);
    variablesAppliedSummary.value = `${appliedCount} applied, ${failedCount} failed`;
  } catch {
    variablesAppliedSummary.value = null;
  }
}

function openEditVariable(row: EffectiveVariableOut) {
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

async function saveVariableOverride(row: EffectiveVariableOut) {
  if (!deviceInfo.value?.device_uid) return;
  if (overrideDisabled.value) return;
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

async function clearVariableOverride(row: EffectiveVariableOut) {
  if (!deviceInfo.value?.device_uid) return;
  if (overrideDisabled.value) return;
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

function variableValueText(row: EffectiveVariableOut) {
  if (row.is_secret && (row.value === null || !revealVariableKeys.value.has(row.key))) {
    return "••••••";
  }
  return formatValue(row.value);
}

function variableSourceLabel(row: EffectiveVariableOut) {
  return row.source === "device_override" ? "device override" : "global default";
}

function toggleVariableReveal(key: string) {
  const next = new Set(revealVariableKeys.value);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  revealVariableKeys.value = next;
}

function fmtTime(iso: string) {
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "number") return Number.isFinite(value) ? value.toString() : "-";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "string") return value;
  return JSON.stringify(value);
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
  const message = mapped || fallback;
  const statusLabel = info.httpStatus ? `HTTP ${info.httpStatus}` : "HTTP ?";
  const codeText = info.code ? `${info.code}` : "UNKNOWN";
  return `${message} (${statusLabel}, ${codeText})`;
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

function upsertEffectiveItems(next: EffectiveVariableOut[]) {
  const byKey = new Map(variables.value.map((i) => [i.key, i]));
  for (const item of next) {
    const cur = byKey.get(item.key);
    if (cur) Object.assign(cur, item);
    else variables.value.push(item);
  }
  const nextKeys = new Set(next.map((i) => i.key));
  variables.value = variables.value.filter((i) => nextKeys.has(i.key));
}

function refreshNow() {
  refreshAll("manual");
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

function openAddOverride() {
  if (overrideDisabled.value || !deviceInfo.value?.device_uid) return;
  addOverrideOpen.value = true;
  addOverrideError.value = null;
  if (!addOverrideKey.value && overrideKeyOptions.value.length > 0) {
    addOverrideKey.value = overrideKeyOptions.value[0];
  }
}

function closeAddOverride() {
  addOverrideOpen.value = false;
  addOverrideValue.value = "";
  addOverrideError.value = null;
}

async function saveNewOverride() {
  if (!deviceInfo.value?.device_uid) return;
  if (!addOverrideKey.value) {
    addOverrideError.value = "Select a variable key";
    return;
  }
  try {
    const existing = variables.value.find(
      (item) => item.key === addOverrideKey.value && item.source === "device"
    );
    await putValue({
      key: addOverrideKey.value,
      scope: "device",
      deviceUid: deviceInfo.value.device_uid,
      value: parseValueInput(addOverrideValue.value),
      expectedVersion: existing?.version ?? undefined,
    });
    closeAddOverride();
    loadVariables();
  } catch (e: any) {
    addOverrideError.value = formatApiError(e, "Failed to add override");
  }
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
  if (document.visibilityState === "hidden") {
    stopPolling();
    abortInflight();
    return;
  }
  refreshAll("visible");
  startPolling();
  startLeaseCountdown();
}

function resetForDeviceChange(nextId: string) {
  deviceId.value = nextId;
  deviceInfo.value = null;
  currentTask.value = null;
  taskHistory.value = [];
  telemetry.value = [];
  telemetryError.value = null;
  currentTaskError.value = null;
  taskHistoryError.value = null;
  variables.value = [];
  variablesSnapshotId.value = null;
  variablesAppliedSummary.value = null;
  revealVariableKeys.value = new Set();
  expandedTelemetry.value = new Set();

  stopLeaseCountdown();
  abortInflight();
  stopPolling();
  cleanupWs();
  connectWs();
  refreshAll("route");
  startPolling();
}

watch(
  () => route.params.id,
  (next) => {
    if (!next) return;
    if (next === deviceId.value) return;
    resetForDeviceChange(next as string);
  }
);

onMounted(() => {
  mounted = true;
  connectWs();
  document.addEventListener("visibilitychange", onVisibilityChange);
  refreshAll("mount");
  startPolling();
});

onUnmounted(() => {
  mounted = false;
  if (reconnectTimer !== null) {
    window.clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  stopLeaseCountdown();
  abortInflight();
  stopPolling();
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
      <div class="card-header-row">
        <strong>Effective Variables</strong>
        <div class="row-actions">
          <button class="btn secondary" @click="loadVariables">Refresh vars</button>
          <button
            class="btn secondary"
            :disabled="overrideDisabled || !deviceInfo?.device_uid"
            @click="openAddOverride"
          >
            Add override
          </button>
        </div>
      </div>
      <div v-if="deviceInfo?.busy" class="inline-warn" style="margin-top: 6px;">
        Device busy — changes may apply later
      </div>
      <div v-if="overrideDisabled" class="pairing-warn" style="margin-top: 6px;">
        Device not provisioned
      </div>
      <div v-if="variablesSnapshotId || variablesAppliedSummary" class="info-note" style="margin-top: 6px;">
        <span v-if="variablesSnapshotId">
          Last snapshot: <span class="cell-mono">{{ variablesSnapshotId }}</span>
        </span>
        <span v-if="variablesSnapshotId && variablesAppliedSummary"> • </span>
        <span v-if="variablesAppliedSummary">Last apply: {{ variablesAppliedSummary }}</span>
      </div>
      <div v-if="variablesError" class="error" style="margin-top: 6px;">
        {{ variablesError }}
      </div>
      <div v-else-if="variablesLoading" style="margin-top: 6px;">Loading...</div>
      <div v-if="addOverrideOpen" class="action-strip">
        <div class="info-grid" style="margin-top: 0;">
          <div class="info-item">
            <div class="info-label">Key</div>
            <select v-model="addOverrideKey" class="input">
              <option value="" disabled>Select variable</option>
              <option v-for="key in overrideKeyOptions" :key="key" :value="key">
                {{ key }}
              </option>
            </select>
          </div>
          <div class="info-item">
            <div class="info-label">Value</div>
            <input v-model="addOverrideValue" class="input" />
          </div>
        </div>
        <div v-if="overrideKeyOptions.length === 0" class="row-error">
          No variables available for override.
        </div>
        <div v-if="addOverrideError" class="row-error">{{ addOverrideError }}</div>
        <div class="row-actions">
          <button
            class="btn secondary"
            :disabled="overrideDisabled || !addOverrideKey"
            @click="saveNewOverride"
          >
            Save override
          </button>
          <button class="btn secondary" @click="closeAddOverride">Cancel</button>
        </div>
      </div>
      <table v-if="!variablesLoading" class="table table-fixed" style="margin-top: 6px;">
        <thead>
          <tr>
            <th class="ev-col-key">Key</th>
            <th class="ev-col-value">Value</th>
            <th class="ev-col-source">Source</th>
            <th class="ev-col-version">Version</th>
            <th class="ev-col-updated">Updated</th>
            <th class="ev-col-actions">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in variablesSorted" :key="row.key">
            <td class="ev-cell ev-col-key">{{ row.key }}</td>
            <td class="ev-cell ev-col-value">
              <span v-if="editingVarKey === row.key">
                <input v-model="editingVarValue" class="input" />
              </span>
              <span v-else>{{ variableValueText(row) }}</span>
            </td>
            <td class="ev-cell ev-col-source">{{ variableSourceLabel(row) }}</td>
            <td class="ev-cell ev-col-version">
              <span class="cell-mono">{{ row.version ?? "-" }}</span>
            </td>
            <td class="ev-cell ev-col-updated">
              <span class="cell-mono">{{ row.updated_at ? fmtTime(row.updated_at) : "-" }}</span>
            </td>
            <td class="ev-cell ev-col-actions">
              <template v-if="editingVarKey === row.key">
                <button class="btn secondary" @click="saveVariableOverride(row)">Save</button>
                <button class="btn secondary" @click="closeEditVariable">Cancel</button>
              </template>
              <template v-else>
                <button
                  class="btn secondary"
                  :disabled="overrideDisabled"
                  @click="openEditVariable(row)"
                >
                  {{ row.source === "global" ? "Edit override" : "Edit" }}
                </button>
                <button
                  v-if="row.source === 'device'"
                  class="btn secondary"
                  :disabled="overrideDisabled"
                  @click="clearVariableOverride(row)"
                >
                  Delete override
                </button>
                <button
                  v-if="row.is_secret"
                  class="btn secondary"
                  @click="toggleVariableReveal(row.key)"
                >
                  {{ revealVariableKeys.has(row.key) ? "Hide" : "Reveal" }}
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
