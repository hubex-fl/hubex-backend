import { ref, onMounted, onUnmounted, nextTick } from "vue";
import { apiFetch } from "../lib/api";
import { mapErrorToUserText, parseApiError } from "../lib/errors";

export type AlertRule = {
  id: number;
  name: string;
  condition_type: string;
  condition_config: Record<string, unknown>;
  entity_id: string | null;
  severity: "info" | "warning" | "critical";
  enabled: boolean;
  cooldown_seconds: number;
  created_at: string;
  updated_at: string;
  __sig?: string;
};

export type AlertEvent = {
  id: number;
  rule_id: number;
  entity_id: string | null;
  device_id: number | null;
  status: "firing" | "acknowledged" | "resolved";
  message: string;
  triggered_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  acknowledged_by: string | null;
  __sig?: string;
};

function ruleSig(r: AlertRule): string {
  return [r.id, r.name, r.condition_type, r.severity, r.enabled, r.cooldown_seconds, r.updated_at].join("|");
}

function eventSig(e: AlertEvent): string {
  return [e.id, e.status, e.triggered_at, e.acknowledged_at ?? "", e.resolved_at ?? ""].join("|");
}

function reconcileById<T extends { id: number; __sig?: string }>(
  target: T[],
  next: T[],
  sigFn: (item: T) => string,
) {
  const byId = new Map<number, T>();
  for (const item of target) byId.set(item.id, item);
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

export function useAlerts(intervalMs = 10_000) {
  const rules = ref<AlertRule[]>([]);
  const events = ref<AlertEvent[]>([]);
  const loading = ref(true);
  const error = ref<string | null>(null);
  const refreshing = ref(false);

  let inflight = false;
  let pollTimer: number | null = null;
  let refreshTimer: number | null = null;

  async function fetchAll(silent = false): Promise<void> {
    if (inflight) return;
    inflight = true;

    if (silent) {
      if (typeof document !== "undefined" && document.visibilityState !== "visible") {
        inflight = false;
        return;
      }
      if (refreshTimer !== null) window.clearTimeout(refreshTimer);
      refreshTimer = window.setTimeout(() => { refreshing.value = true; }, 350);
    }

    try {
      const [nextRules, nextEvents] = await Promise.all([
        apiFetch<AlertRule[]>("/api/v1/alerts/rules"),
        apiFetch<AlertEvent[]>("/api/v1/alerts"),
      ]);
      reconcileById(rules.value, nextRules, ruleSig);
      reconcileById(events.value, nextEvents, eventSig);
      error.value = null;
    } catch (err: unknown) {
      const info = parseApiError(err);
      error.value = mapErrorToUserText(info, "Failed to load alerts");
    } finally {
      loading.value = false;
      if (refreshTimer !== null) {
        window.clearTimeout(refreshTimer);
        refreshTimer = null;
      }
      refreshing.value = false;
      inflight = false;
    }
  }

  function schedulePoll() {
    if (pollTimer !== null) window.clearTimeout(pollTimer);
    pollTimer = window.setTimeout(async () => {
      pollTimer = null;
      await fetchAll(true);
      schedulePoll();
    }, intervalMs);
  }

  function onVisibilityChange() {
    if (typeof document !== "undefined" && document.visibilityState === "visible") {
      fetchAll(true);
    }
  }

  onMounted(async () => {
    await fetchAll(false);
    schedulePoll();
    document.addEventListener("visibilitychange", onVisibilityChange);
  });

  onUnmounted(() => {
    if (pollTimer !== null) { window.clearTimeout(pollTimer); pollTimer = null; }
    if (refreshTimer !== null) { window.clearTimeout(refreshTimer); refreshTimer = null; }
    document.removeEventListener("visibilitychange", onVisibilityChange);
  });

  async function reload(): Promise<void> {
    return fetchAll(false);
  }

  async function ackEvent(id: number): Promise<void> {
    const updated = await apiFetch<AlertEvent>(`/api/v1/alerts/${id}/ack`, { method: "POST" });
    const idx = events.value.findIndex((e) => e.id === id);
    if (idx !== -1) {
      Object.assign(events.value[idx], updated);
      events.value[idx].__sig = eventSig(events.value[idx]);
    }
  }

  async function resolveEvent(id: number): Promise<void> {
    const updated = await apiFetch<AlertEvent>(`/api/v1/alerts/${id}/resolve`, { method: "POST" });
    const idx = events.value.findIndex((e) => e.id === id);
    if (idx !== -1) {
      Object.assign(events.value[idx], updated);
      events.value[idx].__sig = eventSig(events.value[idx]);
    }
  }

  async function createRule(data: Partial<AlertRule>): Promise<void> {
    await apiFetch<AlertRule>("/api/v1/alerts/rules", {
      method: "POST",
      body: JSON.stringify(data),
    });
    const next = await apiFetch<AlertRule[]>("/api/v1/alerts/rules");
    reconcileById(rules.value, next, ruleSig);
  }

  async function updateRule(id: number, data: Partial<AlertRule>): Promise<void> {
    const updated = await apiFetch<AlertRule>(`/api/v1/alerts/rules/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
    const idx = rules.value.findIndex((r) => r.id === id);
    if (idx !== -1) {
      Object.assign(rules.value[idx], updated);
      rules.value[idx].__sig = ruleSig(rules.value[idx]);
    }
  }

  async function deleteRule(id: number): Promise<void> {
    await apiFetch(`/api/v1/alerts/rules/${id}`, { method: "DELETE" });
    const idx = rules.value.findIndex((r) => r.id === id);
    if (idx !== -1) rules.value.splice(idx, 1);
  }

  return {
    rules,
    events,
    loading,
    error,
    refreshing,
    reload,
    ackEvent,
    resolveEvent,
    createRule,
    updateRule,
    deleteRule,
  };
}
