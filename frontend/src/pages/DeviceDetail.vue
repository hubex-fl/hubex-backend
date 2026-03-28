<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiFetch, getToken, reissueDeviceToken, unclaimDevice } from "../lib/api";
import { mapErrorToUserText, parseApiError } from "../lib/errors";
import { hasCap, useCapabilities } from "../lib/capabilities";
import { runRefresh } from "../lib/refresh";
import {
  getEffectiveVariables,
  putValue,
  EffectiveVariable as EffectiveVariableOut,
} from "../lib/variables";
import UCard from "../components/ui/UCard.vue";
import UBadge from "../components/ui/UBadge.vue";
import UButton from "../components/ui/UButton.vue";
import UInput from "../components/ui/UInput.vue";
import USelect from "../components/ui/USelect.vue";
import USkeleton from "../components/ui/USkeleton.vue";
import UEmpty from "../components/ui/UEmpty.vue";
import { DEVICE_TYPE_META } from "../composables/useDevices";
import type { DeviceType } from "../composables/useDevices";

const route = useRoute();
const router = useRouter();
const deviceId = ref(route.params.id as string);

type DeviceInfo = {
  id: number;
  device_uid: string;
  device_type: string;
  name?: string | null;
  firmware_version?: string | null;
  last_seen_at: string | null;
  health: "ok" | "stale" | "dead";
  last_seen_age_seconds: number | null;
  state?: "unprovisioned" | "provisioned_unclaimed" | "pairing_active" | "claimed" | "busy";
  pairing_active?: boolean;
  busy?: boolean;
  __sig?: string;
};

type TelemetryItem = {
  id: number;
  received_at?: string;
  created_at?: string;
  event_type?: string | null;
  payload?: Record<string, any> | null;
  __sig?: string;
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
  id: number;
  task_id: number;
  task_name: string;
  task_type: string;
  task_status: string;
  claimed_at: string | null;
  finished_at: string | null;
  last_seen_at: string | null;
  __sig?: string;
};

type UserTelemetryOut = {
  id: number;
  created_at: string;
  event_type?: string | null;
  payload?: Record<string, any> | null;
};

type AuditEntry = {
  id: number;
  ts: string;
  actor_type: string;
  actor_id: string;
  action: string;
  resource: string | null;
  metadata?: Record<string, any> | null;
};

const deviceInfo = ref<DeviceInfo | null>(null);
const deviceInfoError = ref<string | null>(null);
const caps = useCapabilities();
const deviceInfoLoading = computed(
  () => deviceInfo.value === null && deviceInfoError.value === null
);
const deviceInfoUpdatedAt = ref<string | null>(null);
const deviceCardRef = ref<HTMLElement | null>(null);
const telemetryTableRef = ref<HTMLTableElement | null>(null);
const DEBUG_REFRESH = false;
const nowBucket = ref(Math.floor(Date.now() / 30000));

const telemetry = ref<TelemetryItem[]>([]);
const telemetryError = ref<string | null>(null);
const latestTelemetry = computed(() => telemetry.value[0] ?? null);

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
let nowBucketTimer: number | null = null;
const editingVarKey = ref<string | null>(null);
const editingVarValue = ref<string>("");
const reissueBusy = ref(false);
const reissueError = ref<string | null>(null);
const reissueToken = ref<string | null>(null);
const reissueRevokedCount = ref<number | null>(null);
const reissueCopied = ref(false);
const canReissueToken = computed(() => hasCap("devices.token.reissue"));
const capsUnavailable = computed(() => caps.status !== "ready");
const canReadTelemetry = computed(() => hasCap("telemetry.read"));
const canAdmin = computed(() => hasCap("cap.admin"));
const telemetryLoading = ref(false);
const canReadAudit = computed(() => hasCap("audit.read"));
const auditEntries = ref<AuditEntry[]>([]);
const auditError = ref<string | null>(null);
const auditLoading = ref(false);
const canUnclaim = computed(() => hasCap("devices.unclaim"));
const unclaimBusy = ref(false);
const unclaimConfirm = ref(false);
const unclaimError = ref<string | null>(null);
const unclaimStatus = ref<string | null>(null);

const isUnclaimed = computed(() => {
  const state = deviceInfo.value?.state;
  return state === "provisioned_unclaimed" || state === "pairing_active" || state === "unprovisioned";
});
const restrictUnclaimed = computed(() => isUnclaimed.value && !canAdmin.value);

// ── Hero ring helpers ─────────────────────────────────────────────────────────
const RING_R = 52;
const RING_CIRC = 2 * Math.PI * RING_R;

const heroRingColor = computed(() => {
  const h = deviceInfo.value?.health;
  if (h === "ok") return "var(--status-ok)";
  if (h === "stale") return "var(--status-warn)";
  return "var(--status-bad)";
});

const heroRingOnline = computed(() => deviceInfo.value?.health === "ok");

const heroStatusLabel = computed(() => {
  const h = deviceInfo.value?.health;
  if (h === "ok") return "ONLINE";
  if (h === "stale") return "STALE";
  return "OFFLINE";
});
const heroStatusClass = computed(() => {
  const h = deviceInfo.value?.health;
  if (h === "ok") return "text-[var(--status-ok)]";
  if (h === "stale") return "text-[var(--status-warn)]";
  return "text-[var(--status-bad)]";
});
const connectionLabel = computed(() => {
  const h = deviceInfo.value?.health;
  if (h === "ok") return "Stabil";
  if (h === "stale") return "Unterbrochen";
  return "Offline";
});
const telemetryBattery = computed(() => {
  const p = latestTelemetry.value?.payload;
  if (!p) return null;
  const key = Object.keys(p).find(k => /battery|batt/i.test(k));
  return key ? formatValue(p[key]) : null;
});
const telemetrySignal = computed(() => {
  const p = latestTelemetry.value?.payload;
  if (!p) return null;
  const key = Object.keys(p).find(k => /rssi|signal|wifi/i.test(k));
  return key ? formatValue(p[key]) : null;
});

const healthBadgeStatus = computed((): "ok" | "warn" | "bad" => {
  const h = deviceInfo.value?.health;
  if (h === "ok") return "ok";
  if (h === "stale") return "warn";
  return "bad";
});

const stateBadgeStatus = computed((): "ok" | "warn" | "bad" | "neutral" => {
  const s = deviceInfo.value?.state;
  if (!s) return "neutral";
  if (s === "claimed") return "ok";
  if (s === "busy" || s === "unprovisioned") return "bad";
  return "warn";
});

const taskBadgeStatus = computed((): "ok" | "warn" | "bad" => {
  const task = currentTask.value;
  if (!task || !task.has_active_lease) return "bad";
  if (isLeaseExpiredLocally.value) return "bad";
  const status = (task.task_status || "").toLowerCase();
  if (status.includes("fail") || status.includes("error") || status.includes("cancel")) return "bad";
  if (leaseSecondsRemaining.value !== null && leaseSecondsRemaining.value <= 30) return "warn";
  return "ok";
});

// ── Latest telemetry tiles ────────────────────────────────────────────────────
const showAllTelemetry = ref(false);
const MAX_TILES = 8;

const latestPayloadFields = computed(() => {
  const p = latestTelemetry.value?.payload;
  if (!p || typeof p !== "object") return [];
  return Object.entries(p).map(([k, v]) => ({ key: k, value: formatValue(v) }));
});

const visibleTelemetryFields = computed(() => {
  const all = latestPayloadFields.value;
  return showAllTelemetry.value ? all : all.slice(0, MAX_TILES);
});

// ── WS / polling logic (unchanged) ───────────────────────────────────────────

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

function logRefresh(phase: "start" | "end") {
  if (!DEBUG_REFRESH) return;
  // eslint-disable-next-line no-console
  console.log(
    `[device-detail] refresh:${phase}`,
    "deviceInfo=",
    deviceInfo.value?.id ?? "-",
    "telemetry=",
    telemetry.value.length,
    "audit=",
    auditEntries.value.length,
    "card=",
    deviceCardRef.value,
    "telemetryTable=",
    telemetryTableRef.value
  );
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
  logRefresh("start");
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
  logRefresh("end");
}

function startPolling() {
  stopPolling();
  scheduleNextPoll();
}

function telemetryAllowed(): boolean {
  return caps.status === "ready" && canReadTelemetry.value;
}

async function loadTelemetry(): Promise<boolean> {
  if (!telemetryAllowed()) return true;
  const res = await runRefresh<UserTelemetryOut[] | undefined>({
    fallback: "Failed to load telemetry",
    setBusy: (value) => { telemetryLoading.value = value; },
    setError: (value) => { telemetryError.value = value; },
    action: () => guardedFetch("telemetry", (signal) =>
      apiFetch<UserTelemetryOut[]>(
        `/api/v1/devices/${deviceId.value}/telemetry?limit=50`,
        { signal }
      )
    ),
  });
  if (res === null) return false;
  if (!res) return true;
  const next = res.map((row) => ({
    id: row.id,
    received_at: row.created_at,
    event_type: row.event_type ?? null,
    payload: row.payload ?? null,
  }));
  reconcileById(telemetry.value, next, telemetrySig);
  return true;
}

async function loadAuditEntries(): Promise<boolean> {
  if (caps.status !== "ready") {
    auditError.value = null;
    auditLoading.value = false;
    return false;
  }
  if (!canReadAudit.value) {
    auditError.value = null;
    auditLoading.value = false;
    return false;
  }
  const res = await runRefresh<AuditEntry[] | undefined>({
    fallback: "Failed to load audit",
    setBusy: (value) => { auditLoading.value = value; },
    setError: (value) => { auditError.value = value; },
    action: () => apiFetch<AuditEntry[]>(
      "/api/v1/audit?action=device.token.reissue&limit=50"
    ),
  });
  if (res === null) return false;
  if (!res) return true;
  const uid = deviceInfo.value?.device_uid;
  const filtered = uid ? res.filter((entry) => entry.resource === uid) : [];
  reconcileById(auditEntries.value, filtered.slice(0, 5), auditSig);
  return true;
}

function connectWs() {
  if (!mounted) return;
  if (!telemetryAllowed()) return;
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
        reconcileById(telemetry.value, data as TelemetryItem[], telemetrySig);
      } else if (data && typeof data === "object") {
        const item = data as TelemetryItem;
        const nextSig = telemetrySig(item);
        const existing = telemetry.value.find((t) => t.id === item.id);
        if (existing && existing.__sig === nextSig) {
          return;
        }
        const next = [...telemetry.value, item];
        if (next.length > 5) {
          next.splice(0, next.length - 5);
        }
        reconcileById(telemetry.value, next, telemetrySig);
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

function isSameCurrentTask(a: CurrentTaskOut | null, b: CurrentTaskOut | null) {
  if (!a || !b) return false;
  return (
    a.task_id === b.task_id &&
    a.task_status === b.task_status &&
    a.lease_expires_at === b.lease_expires_at &&
    a.has_active_lease === b.has_active_lease
  );
}

function bucketSeconds(diffSeconds: number): number {
  const safe = Math.max(0, diffSeconds);
  if (safe < 60) return Math.floor(safe / 5) * 5;
  if (safe < 600) return Math.floor(safe / 30) * 30;
  return Math.floor(safe / 60) * 60;
}

function deviceInfoSig(info: DeviceInfo): string {
  return [
    info.id,
    info.device_uid,
    info.health,
    info.state ?? "",
    info.pairing_active ? "1" : "0",
    info.busy ? "1" : "0",
    info.last_seen_at ?? "",
  ].join("|");
}

function auditSig(entry: AuditEntry): string {
  const revoked = entry.metadata?.revoked_count ?? "";
  return [entry.id, entry.ts, entry.actor_id, entry.action, entry.resource ?? "", revoked].join("|");
}

function taskHistorySig(item: TaskHistoryItemOut): string {
  return [
    item.task_id,
    item.task_status,
    item.finished_at ?? "",
    item.claimed_at ?? "",
    item.task_type ?? "",
    item.task_name ?? "",
  ].join("|");
}

function telemetrySig(item: TelemetryItem): string {
  const keys = item.payload ? Object.keys(item.payload).sort() : [];
  const keySig = keys.length ? `k:${keys.length}|${keys.join(",")}` : "k:0";
  return [
    item.id,
    item.received_at ?? item.created_at ?? "",
    item.event_type ?? "",
    keySig,
  ].join("|");
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
  let changed = false;
  for (const item of next) {
    const existing = byId.get(item.id);
    if (existing) {
      const nextSig = sigFn(item);
      if (existing.__sig !== nextSig) {
        Object.assign(existing, item);
        existing.__sig = nextSig;
        changed = true;
      }
      ordered.push(existing);
    } else {
      item.__sig = sigFn(item);
      ordered.push(item);
      changed = true;
    }
  }
  if (target.length !== ordered.length) {
    changed = true;
  } else if (!changed) {
    for (let i = 0; i < target.length; i += 1) {
      if (target[i] !== ordered[i]) {
        changed = true;
        break;
      }
    }
  }
  if (!changed) return;
  target.splice(0, target.length, ...ordered);
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
  const res = await runRefresh<DeviceInfo | undefined>({
    fallback: "Failed to load device",
    setError: (value) => { deviceInfoError.value = value; },
    action: () => guardedFetch("deviceInfo", (signal) =>
      apiFetch<DeviceInfo>(`/api/v1/devices/${deviceId.value}`, { signal })
    ),
  });
  if (res === null) return false;
  if (!res) return true;
  const sig = deviceInfoSig(res);
  const current = deviceInfo.value;
  if (current && current.__sig === sig) {
    return true;
  }
  if (current) {
    Object.assign(current, res);
    current.__sig = sig;
  } else {
    res.__sig = sig;
    deviceInfo.value = res;
  }
  deviceInfoUpdatedAt.value = new Date().toLocaleTimeString();
  return true;
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
    reconcileById(taskHistory.value, res.map(t => ({ ...t, id: t.task_id })), taskHistorySig);
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
  return row.source === "device_override" ? "override" : "default";
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
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return Number.isFinite(value) ? value.toString() : "—";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

function historyStatusBadge(status: string): "ok" | "warn" | "bad" {
  const s = (status || "").toLowerCase();
  if (["done", "success", "succeeded", "completed"].includes(s)) return "ok";
  if (["failed", "error", "cancelled", "canceled", "timeout", "timed_out"].includes(s)) return "bad";
  return "warn";
}

function formatApiError(err: any, fallback: string) {
  const info = parseApiError(err);
  const mapped = mapErrorToUserText(info, fallback);
  const message = mapped || fallback;
  const statusLabel = info.httpStatus ? `HTTP ${info.httpStatus}` : "HTTP ?";
  const codeText = info.code ? `${info.code}` : "UNKNOWN";
  return `${message} (${statusLabel}, ${codeText})`;
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
  if (capsUnavailable.value) return;
  refreshAll("manual");
  loadTelemetry();
  loadAuditEntries();
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

async function copyReissueToken() {
  if (!reissueToken.value) return;
  try {
    await navigator.clipboard.writeText(reissueToken.value);
    reissueCopied.value = true;
  } catch {
    // ignore
  }
}

function clearReissueToken() {
  reissueToken.value = null;
  reissueRevokedCount.value = null;
  reissueCopied.value = false;
}

async function handleReissueToken() {
  if (!deviceInfo.value) return;
  reissueError.value = null;
  const reason = window.prompt("Reason for reissue (required)");
  if (!reason || reason.trim().length < 3) {
    reissueError.value = "Reason is required (min 3 characters).";
    return;
  }
  if (
    !window.confirm(
      "⚠️ WARNING: After reissuing, the device will lose its current token.\n\n" +
        "It will need to reconnect to show as auth failed, then you must:\n" +
        "  1) Connect to HUBEX-SETUP AP\n" +
        "  2) Go to /portal\n" +
        "  3) Paste the new token in the 'Set Device Token' field\n\n" +
        "This revokes all previous device tokens. Continue?"
    )
  )
    return;
  reissueBusy.value = true;
  try {
    const res = await reissueDeviceToken(deviceInfo.value.id, reason.trim());
    reissueToken.value = res.device_token;
    reissueRevokedCount.value = res.revoked_count;
    reissueCopied.value = false;
    loadAuditEntries();
  } catch (e: any) {
    reissueError.value = formatApiError(e, "Failed to reissue device token");
  } finally {
    reissueBusy.value = false;
  }
}

function startUnclaimConfirm() {
  unclaimError.value = null;
  unclaimStatus.value = null;
  unclaimConfirm.value = true;
}

function cancelUnclaimConfirm() {
  unclaimConfirm.value = false;
}

function resetForExit() {
  deviceInfo.value = null;
  deviceInfoUpdatedAt.value = null;
  deviceInfoError.value = null;
  currentTask.value = null;
  currentTaskError.value = null;
  taskHistory.value = [];
  taskHistoryError.value = null;
  telemetry.value = [];
  telemetryError.value = null;
  telemetryLoading.value = false;
  variables.value = [];
  variablesSnapshotId.value = null;
  variablesAppliedSummary.value = null;
  variablesError.value = null;
  variablesLoading.value = false;
  addOverrideOpen.value = false;
  addOverrideKey.value = "";
  addOverrideValue.value = "";
  addOverrideError.value = null;
  revealVariableKeys.value = new Set();
  expandedTelemetry.value = new Set();
  clearReissueToken();
  auditEntries.value = [];
  auditError.value = null;
  auditLoading.value = false;
  unclaimStatus.value = null;
  unclaimError.value = null;
  unclaimConfirm.value = false;

  if (reconnectTimer !== null) {
    window.clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  stopLeaseCountdown();
  abortInflight();
  stopPolling();
  cleanupWs();
}

async function confirmUnclaim() {
  if (!deviceInfo.value) return;
  unclaimError.value = null;
  unclaimStatus.value = null;
  unclaimBusy.value = true;
  try {
    const res = await unclaimDevice(deviceInfo.value.id);
    unclaimStatus.value = `Unclaimed. Revoked ${res.revoked_count} tokens.`;
    resetForExit();
    await router.push("/devices");
  } catch (e: any) {
    unclaimError.value = formatApiError(e, "Failed to unclaim device");
  } finally {
    unclaimBusy.value = false;
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
      (item) => item.key === addOverrideKey.value && item.source === "device_override"
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
  if (!payload) return "—";
  const text = JSON.stringify(payload);
  if (expanded) return text;
  if (text.length <= 120) return text;
  return text.slice(0, 120) + "...";
}

function fmtAge(ageSeconds: number | null) {
  if (ageSeconds === null) return "—";
  const bucketed = bucketSeconds(ageSeconds);
  if (bucketed < 60) return `${bucketed}s ago`;
  if (bucketed < 3600) return `${Math.floor(bucketed / 60)}m ago`;
  return `${Math.floor(bucketed / 3600)}h ago`;
}

function fmtRemaining(seconds: number | null) {
  if (seconds === null) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

function fmtAgoFromIso(iso: string | null) {
  if (!iso) return "—";
  const dt = new Date(iso);
  if (!Number.isFinite(dt.getTime())) return "—";
  const nowMs = nowBucket.value * 30000;
  const diffSeconds = Math.max(0, Math.floor((nowMs - dt.getTime()) / 1000));
  return fmtAge(diffSeconds);
}

function fmtDeviceLastSeen(info: DeviceInfo | null) {
  if (!info) return "—";
  if (info.last_seen_at) return fmtAgoFromIso(info.last_seen_at);
  if (info.last_seen_age_seconds !== null) return fmtAge(info.last_seen_age_seconds);
  return "—";
}

function fmtRelative(iso: string | undefined) {
  if (!iso) return "—";
  return fmtAgoFromIso(iso);
}

function onVisibilityChange() {
  if (document.visibilityState === "hidden") {
    stopPolling();
    abortInflight();
    return;
  }
  refreshAll("visible");
  loadTelemetry();
  startPolling();
  startLeaseCountdown();
  connectWs();
}

function resetForDeviceChange(nextId: string) {
  deviceId.value = nextId;
  deviceInfo.value = null;
  deviceInfoUpdatedAt.value = null;
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
  clearReissueToken();
  auditEntries.value = [];
  auditError.value = null;

  stopLeaseCountdown();
  abortInflight();
  stopPolling();
  cleanupWs();
  loadTelemetry();
  connectWs();
  refreshAll("route");
  startPolling();
}

watch(
  () => [caps.status, canReadTelemetry.value],
  ([status, canRead]) => {
    if (status === "ready" && canRead) {
      loadTelemetry();
      connectWs();
    } else {
      cleanupWs();
    }
  }
);

watch(
  () => [caps.status, canReadAudit.value, deviceInfo.value?.device_uid],
  ([status, canRead, uid]) => {
    if (status === "ready" && canRead && uid) {
      loadAuditEntries();
    }
  }
);

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
  nowBucketTimer = window.setInterval(() => {
    nowBucket.value = Math.floor(Date.now() / 30000);
  }, 30000);
  loadTelemetry();
  connectWs();
  document.addEventListener("visibilitychange", onVisibilityChange);
  refreshAll("mount");
  loadAuditEntries();
  startPolling();
});

onUnmounted(() => {
  mounted = false;
  if (nowBucketTimer !== null) {
    window.clearInterval(nowBucketTimer);
    nowBucketTimer = null;
  }
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
  <div class="space-y-4" ref="deviceCardRef">

    <!-- ── Page Header ─────────────────────────────────────────────────────── -->
    <div class="flex items-center gap-2">
      <UButton variant="ghost" size="sm" @click="router.push('/devices')" class="shrink-0">
        <svg class="h-4 w-4 mr-1" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
        </svg>
        Devices
      </UButton>
      <span class="text-[var(--text-muted)]">/</span>
      <span class="text-sm font-mono text-[var(--text-muted)] truncate">
        {{ deviceInfo?.name || deviceInfo?.device_uid || `#${deviceId}` }}
      </span>
    </div>

    <!-- Unclaimed warning -->
    <div
      v-if="isUnclaimed"
      class="flex items-center gap-2 px-4 py-3 rounded-lg border border-[var(--status-warn)]/30 bg-[var(--status-warn-bg)] text-sm text-[var(--status-warn)]"
    >
      <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
      </svg>
      Device is unclaimed.
      <span v-if="restrictUnclaimed" class="ml-1 text-[var(--text-muted)]">Claim to view full details.</span>
    </div>

    <!-- ── Hero Card ─────────────────────────────────────────────────────────── -->
    <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] overflow-hidden">
      <!-- Top: device identity + actions -->
      <div class="px-5 py-4 flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <!-- Status ring with chip icon inside -->
        <div class="relative shrink-0">
          <div v-if="deviceInfoLoading">
            <USkeleton width="88px" height="88px" rounded="full" />
          </div>
          <div v-else class="relative">
            <svg width="88" height="88" viewBox="0 0 88 88">
              <circle cx="44" cy="44" r="38" fill="none" stroke="var(--bg-raised)" stroke-width="8" />
              <circle
                cx="44" cy="44" r="38"
                fill="none"
                :style="{ stroke: heroRingColor }"
                stroke-width="8"
                stroke-dasharray="238.8 238.8"
                stroke-dashoffset="0"
                stroke-linecap="round"
                transform="rotate(-90 44 44)"
                :class="heroRingOnline ? 'ring-pulse' : ''"
              />
            </svg>
            <div class="absolute inset-0 flex items-center justify-center">
              <svg class="h-9 w-9" :style="{ color: heroRingColor }" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" :d="DEVICE_TYPE_META[(deviceInfo?.device_type as DeviceType) ?? 'unknown']?.icon ?? DEVICE_TYPE_META.unknown.icon" />
              </svg>
            </div>
          </div>
        </div>

        <!-- Device info -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-3 flex-wrap mb-1">
            <div v-if="deviceInfoLoading" class="flex gap-2">
              <USkeleton height="1.5rem" width="5rem" rounded="full" />
              <USkeleton height="1.5rem" width="4rem" rounded="full" />
            </div>
            <template v-else>
              <span :class="['text-xl font-bold tracking-widest font-mono', heroStatusClass]">
                {{ heroStatusLabel }}
              </span>
              <UBadge v-if="deviceInfo?.state" :status="stateBadgeStatus">
                {{ deviceInfo.state.replace(/_/g, ' ') }}
              </UBadge>
            </template>
          </div>
          <div v-if="deviceInfoLoading">
            <USkeleton height="1.5rem" width="55%" class="mb-1" />
            <USkeleton height="0.875rem" width="35%" />
          </div>
          <template v-else>
            <h1 class="text-lg font-mono font-bold text-[var(--text-primary)] truncate">
              {{ deviceInfo?.name || deviceInfo?.device_uid || `Device #${deviceId}` }}
            </h1>
            <p v-if="deviceInfo?.name" class="text-xs font-mono text-[var(--text-muted)]">{{ deviceInfo.device_uid }}</p>
            <p v-if="deviceInfo?.device_type && deviceInfo.device_type !== 'unknown'" class="text-xs text-[var(--text-muted)] mt-0.5">
              <span class="inline-flex items-center gap-1">
                <svg class="h-3 w-3" :style="{ color: DEVICE_TYPE_META[(deviceInfo.device_type as DeviceType)]?.color ?? 'var(--text-muted)' }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                  <path :d="DEVICE_TYPE_META[(deviceInfo.device_type as DeviceType)]?.icon ?? DEVICE_TYPE_META.unknown.icon" />
                </svg>
                {{ DEVICE_TYPE_META[(deviceInfo.device_type as DeviceType)]?.label ?? deviceInfo.device_type }}
              </span>
              <span v-if="deviceInfo.firmware_version" class="ml-2 text-[var(--text-muted)]">&middot; FW {{ deviceInfo.firmware_version }}</span>
            </p>
            <p class="text-xs text-[var(--text-muted)] mt-0.5">
              Gerät verbunden &middot; Letztes Update:
              <strong class="text-[var(--text-secondary)]">{{ fmtDeviceLastSeen(deviceInfo) }}</strong>
            </p>
          </template>
        </div>

        <!-- Actions (moved from top header) -->
        <div class="flex flex-wrap gap-2 shrink-0">
          <UButton variant="secondary" size="sm" :disabled="capsUnavailable" @click="refreshNow">
            <svg class="h-3.5 w-3.5 mr-1" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
            </svg>
            Refresh
          </UButton>
          <UButton variant="secondary" size="sm" :disabled="!deviceInfo?.device_uid" @click="copyUid">
            Copy UID
          </UButton>
          <UButton v-if="deviceInfo?.state === 'pairing_active'" variant="secondary" size="sm" @click="openPairingPanel">
            Pairing Panel
          </UButton>
        </div>
      </div>

      <!-- Status bar -->
      <div class="border-t border-[var(--border)] bg-[var(--bg-raised)] px-5 py-3 flex flex-wrap items-center gap-6">
        <!-- Verbindung -->
        <div class="flex items-center gap-2">
          <svg class="h-4 w-4 shrink-0" :class="heroRingOnline ? 'text-[var(--status-ok)]' : 'text-[var(--text-muted)]'" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.288 15.038a5.25 5.25 0 017.424 0M5.106 11.856c3.807-3.808 9.98-3.808 13.788 0M1.924 8.674c5.565-5.565 14.587-5.565 20.152 0M12.53 18.22l-.53.53-.53-.53a.75.75 0 011.06 0z" />
          </svg>
          <div>
            <p class="text-[10px] text-[var(--text-muted)] uppercase tracking-wide">Verbindung</p>
            <p class="text-xs font-semibold text-[var(--text-primary)]">{{ connectionLabel }}</p>
          </div>
        </div>

        <!-- Signal (from telemetry if available) -->
        <div v-if="telemetrySignal" class="flex items-center gap-2">
          <svg class="h-4 w-4 shrink-0 text-[var(--accent-cyan)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
          </svg>
          <div>
            <p class="text-[10px] text-[var(--text-muted)] uppercase tracking-wide">Signal</p>
            <p class="text-xs font-semibold text-[var(--text-primary)]">{{ telemetrySignal }}</p>
          </div>
        </div>

        <!-- Battery (from telemetry if available) -->
        <div v-if="telemetryBattery" class="flex items-center gap-2">
          <svg class="h-4 w-4 shrink-0 text-[var(--accent-lime)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 10.5h.375c.621 0 1.125.504 1.125 1.125v2.25c0 .621-.504 1.125-1.125 1.125H21M4.5 10.5H18V15H4.5v-4.5zM3.75 18h15A2.25 2.25 0 0021 15.75v-1.5a2.25 2.25 0 00-2.25-2.25h-15A2.25 2.25 0 001.5 14.25v1.5A2.25 2.25 0 003.75 18z" />
          </svg>
          <div>
            <p class="text-[10px] text-[var(--text-muted)] uppercase tracking-wide">Batterie</p>
            <p class="text-xs font-semibold text-[var(--text-primary)]">{{ telemetryBattery }}</p>
          </div>
        </div>

        <!-- Task -->
        <div class="flex items-center gap-2">
          <svg class="h-4 w-4 shrink-0 text-[var(--text-muted)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
          </svg>
          <div>
            <p class="text-[10px] text-[var(--text-muted)] uppercase tracking-wide">Task</p>
            <p class="text-xs font-semibold text-[var(--text-primary)]">
              {{ currentTask?.has_active_lease && !isLeaseExpiredLocally
                  ? (currentTask?.task_name ?? currentTask?.task_status ?? 'active')
                  : 'idle' }}
            </p>
          </div>
        </div>

        <!-- Lease countdown (if active) -->
        <div v-if="currentTask?.has_active_lease && !isLeaseExpiredLocally" class="flex items-center gap-2">
          <svg class="h-4 w-4 shrink-0 text-[var(--text-muted)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p class="text-[10px] text-[var(--text-muted)] uppercase tracking-wide">Lease</p>
            <p class="text-xs font-semibold text-[var(--text-primary)]">{{ fmtRemaining(leaseSecondsRemaining) }}</p>
          </div>
        </div>

        <!-- Live telemetry indicator -->
        <div v-if="latestPayloadFields.length" class="flex items-center gap-1.5 ml-auto">
          <span class="h-1.5 w-1.5 rounded-full bg-[var(--status-ok)] animate-pulse shrink-0" />
          <span class="text-xs text-[var(--text-muted)]">{{ latestPayloadFields.length }} live fields</span>
        </div>
      </div>
    </div>

    <!-- ── Main panels ─────────────────────────────────────────────────────── -->
    <div v-if="!restrictUnclaimed" class="grid grid-cols-1 lg:grid-cols-2 gap-4">

      <!-- Telemetry / Inputs panel -->
      <UCard padding="none" class="border-l-2 border-l-[var(--accent-cyan)]">
        <template #header>
          <div class="flex items-center gap-2">
            <span
              v-if="!telemetryError && telemetry.length"
              class="h-1.5 w-1.5 rounded-full bg-[var(--status-ok)] animate-pulse"
            />
            <h3 class="text-sm font-semibold text-[var(--text-primary)]">
              <span class="text-[var(--accent-cyan)] mr-1">↓</span>Input
              <span class="text-[var(--text-muted)] font-normal ml-1">· Telemetry</span>
            </h3>
            <span v-if="latestTelemetry" class="text-xs text-[var(--text-muted)]">
              {{ latestTelemetry.event_type || "data" }} · {{ fmtRelative(latestTelemetry.received_at) }}
            </span>
          </div>
          <UButton
            size="sm" variant="ghost"
            :disabled="telemetryLoading || caps.status !== 'ready' || !canReadTelemetry"
            @click="loadTelemetry"
          >
            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
            </svg>
          </UButton>
        </template>

        <!-- Caps error -->
        <div v-if="!canReadTelemetry" class="p-4 text-xs text-[var(--text-muted)]">
          Missing capability: telemetry.read
        </div>
        <div v-else-if="telemetryError" class="p-4 text-xs text-[var(--status-bad)]">
          {{ telemetryError }}
        </div>

        <!-- Loading -->
        <div v-else-if="telemetryLoading && !telemetry.length" class="p-4 grid grid-cols-2 gap-2">
          <div v-for="i in 4" :key="i" class="rounded-lg border border-[var(--border)] p-3">
            <USkeleton height="0.75rem" width="60%" class="mb-2" />
            <USkeleton height="1.25rem" width="40%" />
          </div>
        </div>

        <!-- Metric tiles from latest payload -->
        <div v-else-if="visibleTelemetryFields.length" class="p-3 grid grid-cols-2 gap-2">
          <div
            v-for="field in visibleTelemetryFields"
            :key="field.key"
            class="rounded-lg border border-[var(--border)] bg-[var(--bg-raised)] p-3"
          >
            <p class="text-[10px] text-[var(--text-muted)] truncate mb-1 uppercase tracking-wide">{{ field.key }}</p>
            <p class="text-sm font-mono font-semibold text-[var(--text-primary)] truncate">{{ field.value }}</p>
          </div>
          <button
            v-if="latestPayloadFields.length > MAX_TILES"
            class="col-span-2 text-xs text-[var(--accent-cyan)] hover:underline py-1"
            @click="showAllTelemetry = !showAllTelemetry"
          >
            {{ showAllTelemetry ? 'Show less' : `Show ${latestPayloadFields.length - MAX_TILES} more` }}
          </button>
        </div>

        <!-- Raw telemetry rows (no payload tiles) -->
        <div v-else-if="telemetry.length" class="overflow-x-auto">
          <table class="w-full text-xs" ref="telemetryTableRef">
            <thead>
              <tr class="border-b border-[var(--border)]">
                <th class="text-left px-4 py-2.5 text-[var(--text-muted)] font-medium whitespace-nowrap">Time</th>
                <th class="text-left px-4 py-2.5 text-[var(--text-muted)] font-medium">Type</th>
                <th class="text-left px-4 py-2.5 text-[var(--text-muted)] font-medium">Payload</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--border)]">
              <tr
                v-for="t in telemetry"
                :key="t.id"
                v-memo="[t.__sig, isTelemetryExpanded(t.id) ? 1 : 0]"
                class="hover:bg-[var(--bg-raised)] transition-colors"
              >
                <td class="px-4 py-2 font-mono text-[var(--text-muted)] whitespace-nowrap">
                  {{ fmtRelative(t.received_at || t.created_at) }}
                </td>
                <td class="px-4 py-2 text-[var(--text-secondary)] whitespace-nowrap">{{ t.event_type || "—" }}</td>
                <td class="px-4 py-2">
                  <span class="font-mono text-[var(--text-muted)] break-all">{{ payloadPreview(t.payload, isTelemetryExpanded(t.id)) }}</span>
                  <button class="ml-2 text-[var(--accent-cyan)] hover:underline text-xs" @click="toggleTelemetry(t.id)">
                    {{ isTelemetryExpanded(t.id) ? 'less' : 'more' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Empty -->
        <UEmpty
          v-else
          title="No telemetry yet"
          description="Device must POST /api/v1/telemetry to send data."
          icon="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75z"
        />
      </UCard>

      <!-- Variables / Outputs panel -->
      <UCard padding="none" class="border-l-2 border-l-[var(--accent-lime)]">
        <template #header>
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">
            <span class="text-[var(--accent-lime)] mr-1">↑</span>Output
            <span class="text-[var(--text-muted)] font-normal ml-1">· Variables</span>
          </h3>
          <div class="flex gap-1">
            <UButton size="sm" variant="ghost" @click="loadVariables">
              <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>
            </UButton>
            <UButton
              size="sm" variant="ghost"
              :disabled="overrideDisabled || !deviceInfo?.device_uid"
              @click="openAddOverride"
            >
              + Override
            </UButton>
          </div>
        </template>

        <!-- Warnings -->
        <div
          v-if="deviceInfo?.busy"
          class="mx-3 mt-3 px-3 py-2 rounded-lg border border-[var(--status-warn)]/30 bg-[var(--status-warn-bg)] text-xs text-[var(--status-warn)]"
        >
          Device busy — changes may apply later
        </div>

        <!-- Error -->
        <div v-if="variablesError" class="px-4 py-3 text-xs text-[var(--status-bad)]">{{ variablesError }}</div>

        <!-- Add override form -->
        <div v-if="addOverrideOpen" class="px-4 py-3 border-b border-[var(--border)] space-y-2">
          <div class="flex flex-col sm:flex-row gap-2">
            <USelect
              v-model="addOverrideKey"
              :options="overrideKeyOptions.map(k => ({ value: k, label: k }))"
              class="flex-1"
            />
            <UInput v-model="addOverrideValue" placeholder="value" class="flex-1" />
          </div>
          <p v-if="addOverrideError" class="text-xs text-[var(--status-bad)]">{{ addOverrideError }}</p>
          <p v-if="overrideKeyOptions.length === 0" class="text-xs text-[var(--text-muted)]">No variables available for override.</p>
          <div class="flex gap-2">
            <UButton size="sm" :disabled="overrideDisabled || !addOverrideKey" @click="saveNewOverride">Save</UButton>
            <UButton size="sm" variant="secondary" @click="closeAddOverride">Cancel</UButton>
          </div>
        </div>

        <!-- Loading -->
        <div v-if="variablesLoading && !variables.length" class="p-4 space-y-2">
          <div v-for="i in 3" :key="i" class="flex gap-3 items-center">
            <USkeleton width="6rem" height="1rem" />
            <USkeleton height="1rem" />
          </div>
        </div>

        <!-- Empty -->
        <UEmpty
          v-else-if="!variablesLoading && variables.length === 0"
          title="No variables"
          description="No variables configured for this device."
          icon="M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75"
        />

        <!-- Variable rows -->
        <div v-else class="divide-y divide-[var(--border)]">
          <div
            v-for="row in variablesSorted"
            :key="row.key"
            class="px-4 py-2.5 flex items-center gap-3"
          >
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-xs font-mono font-semibold text-[var(--text-primary)] truncate">{{ row.key }}</span>
                <UBadge :status="row.source === 'device_override' ? 'info' : 'neutral'" class="shrink-0">
                  {{ variableSourceLabel(row) }}
                </UBadge>
              </div>
              <!-- Edit mode -->
              <div v-if="editingVarKey === row.key" class="mt-1.5 flex gap-2">
                <UInput v-model="editingVarValue" class="flex-1" />
                <UButton size="sm" @click="saveVariableOverride(row)">Save</UButton>
                <UButton size="sm" variant="secondary" @click="closeEditVariable">✕</UButton>
              </div>
              <!-- View mode -->
              <p v-else class="text-xs font-mono text-[var(--text-muted)] truncate mt-0.5">
                {{ variableValueText(row) }}
              </p>
            </div>
            <!-- Actions -->
            <div v-if="editingVarKey !== row.key" class="flex gap-1 shrink-0">
              <button
                class="p-1 rounded text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
                title="Edit"
                :disabled="overrideDisabled"
                @click="openEditVariable(row)"
              >
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z" />
                </svg>
              </button>
              <button
                v-if="row.source === 'device_override'"
                class="p-1 rounded text-[var(--text-muted)] hover:text-[var(--status-bad)] hover:bg-[var(--bg-raised)] transition-colors"
                title="Delete override"
                :disabled="overrideDisabled"
                @click="clearVariableOverride(row)"
              >
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                </svg>
              </button>
              <button
                v-if="row.is_secret"
                class="p-1 rounded text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
                :title="revealVariableKeys.has(row.key) ? 'Hide' : 'Reveal'"
                @click="toggleVariableReveal(row.key)"
              >
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path v-if="revealVariableKeys.has(row.key)" stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                  <path v-else stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Snapshot info footer -->
        <div v-if="variablesSnapshotId || variablesAppliedSummary" class="px-4 py-2 border-t border-[var(--border)]">
          <p class="text-[10px] text-[var(--text-muted)]">
            <span v-if="variablesAppliedSummary">Last apply: {{ variablesAppliedSummary }}</span>
          </p>
        </div>
      </UCard>
    </div>

    <!-- ── Task History ────────────────────────────────────────────────────── -->
    <UCard v-if="!restrictUnclaimed" padding="none">
      <template #header>
        <h3 class="text-sm font-semibold text-[var(--text-primary)]">Recent Tasks</h3>
        <span
          v-if="currentTask?.has_active_lease && !isLeaseExpiredLocally"
          class="text-xs text-[var(--text-muted)]"
        >
          Active: {{ currentTask.task_name }} · {{ fmtRemaining(leaseSecondsRemaining) }} left
        </span>
      </template>

      <div v-if="currentTaskError" class="px-4 py-3 text-xs text-[var(--status-bad)]">{{ currentTaskError }}</div>
      <div v-if="taskHistoryError" class="px-4 py-3 text-xs text-[var(--status-bad)]">{{ taskHistoryError }}</div>

      <UEmpty
        v-if="taskHistory.length === 0 && !taskHistoryError"
        title="No recent tasks"
        description="Tasks run on this device will appear here."
        icon="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z"
      />

      <div v-else class="overflow-x-auto">
        <table class="w-full text-xs">
          <thead>
            <tr class="border-b border-[var(--border)]">
              <th class="text-left px-4 py-2.5 text-[var(--text-muted)] font-medium">Task</th>
              <th class="text-left px-4 py-2.5 text-[var(--text-muted)] font-medium whitespace-nowrap">Status</th>
              <th class="text-left px-4 py-2.5 text-[var(--text-muted)] font-medium whitespace-nowrap hidden sm:table-cell">When</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[var(--border)]">
            <tr
              v-for="t in taskHistory"
              :key="t.task_id"
              v-memo="[t.__sig]"
              class="hover:bg-[var(--bg-raised)] transition-colors"
            >
              <td class="px-4 py-2.5 truncate max-w-[12rem]">
                <span class="text-[var(--text-secondary)]">{{ t.task_name }}</span>
                <span v-if="t.task_type !== t.task_name" class="text-[var(--text-muted)] ml-1">({{ t.task_type }})</span>
              </td>
              <td class="px-4 py-2.5 whitespace-nowrap">
                <UBadge :status="historyStatusBadge(t.task_status)">{{ t.task_status }}</UBadge>
              </td>
              <td class="px-4 py-2.5 font-mono text-[var(--text-muted)] whitespace-nowrap hidden sm:table-cell">
                <span v-if="t.finished_at">{{ fmtAgoFromIso(t.finished_at) }}</span>
                <span v-else-if="t.claimed_at">{{ fmtAgoFromIso(t.claimed_at) }}</span>
                <span v-else>—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </UCard>

    <!-- ── Recovery ───────────────────────────────────────────────────────── -->
    <UCard v-if="!restrictUnclaimed" padding="md">
      <template #header>
        <h3 class="text-sm font-semibold text-[var(--text-primary)]">Recovery</h3>
        <router-link to="/audit" class="text-xs text-[var(--accent-cyan)] hover:underline">Audit log</router-link>
      </template>

      <div v-if="capsUnavailable" class="text-xs text-[var(--text-muted)]">Capabilities unavailable.</div>
      <div v-else-if="!canReissueToken" class="text-xs text-[var(--text-muted)]">Missing cap: devices.token.reissue</div>
      <div v-else class="space-y-3">
        <div class="flex flex-wrap items-center gap-3">
          <UButton variant="secondary" size="sm" :disabled="reissueBusy" @click="handleReissueToken">
            {{ reissueBusy ? "Reissuing…" : "Reissue Device Token" }}
          </UButton>
          <p v-if="reissueError" class="text-xs text-[var(--status-bad)]">{{ reissueError }}</p>
        </div>

        <!-- New token display -->
        <div
          v-if="reissueToken"
          class="rounded-lg border border-[var(--status-warn)]/30 bg-[var(--status-warn-bg)] p-4 space-y-3"
        >
          <p class="text-xs font-semibold text-[var(--status-warn)]">New token issued — copy now, shown once.</p>
          <div class="flex items-center gap-2">
            <code class="flex-1 text-xs font-mono bg-[var(--bg-raised)] px-3 py-2 rounded border border-[var(--border)] break-all">{{ reissueToken }}</code>
            <UButton size="sm" variant="secondary" @click="copyReissueToken">
              {{ reissueCopied ? "Copied!" : "Copy" }}
            </UButton>
          </div>
          <p class="text-xs text-[var(--text-muted)]">Revoked tokens: {{ reissueRevokedCount ?? 0 }}</p>
          <div class="text-xs text-[var(--text-secondary)] space-y-0.5">
            <p class="font-semibold">To apply this token to the device:</p>
            <p>1. Wait for "auth failed" or power-cycle the device.</p>
            <p>2. Connect to <strong>HUBEX-SETUP</strong> Wi-Fi AP.</p>
            <p>3. Open <strong>http://192.168.4.1/portal</strong>.</p>
            <p>4. Paste in <em>Set Device Token</em> and save.</p>
          </div>
          <UButton size="sm" variant="ghost" @click="clearReissueToken">Dismiss</UButton>
        </div>

        <!-- Audit entries -->
        <div v-if="canReadAudit && !auditError">
          <p class="text-xs text-[var(--text-muted)] mb-2">Recent reissue audit</p>
          <div v-if="auditLoading" class="space-y-1">
            <USkeleton v-for="i in 2" :key="i" height="1rem" />
          </div>
          <div v-else-if="!auditEntries.length" class="text-xs text-[var(--text-muted)]">No recent entries.</div>
          <ul v-else class="space-y-1">
            <li v-for="entry in auditEntries" :key="entry.id" class="text-xs text-[var(--text-muted)]">
              {{ fmtRelative(entry.ts) }} · {{ entry.actor_id }} · revoked {{ entry.metadata?.revoked_count ?? 0 }}
            </li>
          </ul>
        </div>
        <p v-if="auditError" class="text-xs text-[var(--status-bad)]">{{ auditError }}</p>
      </div>
    </UCard>

    <!-- ── Danger Zone ────────────────────────────────────────────────────── -->
    <UCard v-if="!restrictUnclaimed && canUnclaim" padding="md" class="border-[var(--status-bad)]/20">
      <template #header>
        <h3 class="text-sm font-semibold text-[var(--status-bad)]">Danger Zone</h3>
      </template>

      <p class="text-xs text-[var(--text-muted)] mb-3">
        Unclaiming detaches ownership and revokes all device tokens.
      </p>
      <div class="flex flex-wrap gap-2 items-center">
        <UButton
          v-if="!unclaimConfirm"
          variant="secondary"
          size="sm"
          :disabled="unclaimBusy"
          class="border-[var(--status-bad)]/40 text-[var(--status-bad)] hover:bg-[var(--status-bad)]/10"
          @click="startUnclaimConfirm"
        >
          Unclaim Device
        </UButton>
        <template v-else>
          <UButton
            variant="secondary"
            size="sm"
            :disabled="unclaimBusy"
            class="border-[var(--status-bad)]/40 text-[var(--status-bad)]"
            @click="confirmUnclaim"
          >
            {{ unclaimBusy ? "Unclaiming…" : "Confirm Unclaim" }}
          </UButton>
          <UButton variant="ghost" size="sm" :disabled="unclaimBusy" @click="cancelUnclaimConfirm">
            Cancel
          </UButton>
        </template>
        <p v-if="unclaimError" class="text-xs text-[var(--status-bad)]">{{ unclaimError }}</p>
        <p v-if="unclaimStatus" class="text-xs text-[var(--text-muted)]">{{ unclaimStatus }}</p>
      </div>
    </UCard>

  </div>
</template>

<style scoped>
.ring-pulse {
  animation: ring-glow 2s ease-in-out infinite;
}
@keyframes ring-glow {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.65; }
}
</style>
