import { ref, onMounted, onUnmounted } from "vue";
import { apiFetch } from "../lib/api";
import { createPoller } from "../lib/poller";

/**
 * Backend event shape — as of Sprint 3.5 the actual payload from
 * `GET /api/v1/events` is:
 *   { stream, cursor, next_cursor, items: [{ cursor, ts, type, payload, trace_id }] }
 * (not a bare array of {id, stream, event_type, payload, created_at} as
 * the old interface claimed). This caused two P0 runtime errors on
 * every Dashboard load — one for .slice() on a dict, then one for
 * .startsWith() on undefined event_type. Fixed here by matching the
 * real backend shape, and keeping legacy field names as optional for
 * forward/backward compat.
 */
export interface StreamEvent {
  cursor?: number;
  id?: number;
  stream?: string;
  /** Canonical field name since the refactor. */
  type?: string;
  /** Legacy field name, kept for forward compat. */
  event_type?: string;
  payload: Record<string, unknown>;
  /** Canonical timestamp field. */
  ts?: string;
  /** Legacy timestamp field. */
  created_at?: string;
  trace_id?: string | null;
}

/** Resolve the event type regardless of field naming. */
export function eventTypeOf(e: StreamEvent): string {
  return e.type || e.event_type || "";
}

/** Resolve the event timestamp regardless of field naming. */
export function eventTimestampOf(e: StreamEvent): string {
  return e.ts || e.created_at || "";
}

export function eventBadgeStatus(
  eventType: string | undefined | null
): "info" | "bad" | "ok" | "warn" | "neutral" {
  if (!eventType) return "neutral";
  if (eventType.startsWith("device.")) return "info";
  if (eventType.startsWith("alert.")) return "bad";
  if (eventType.startsWith("task.")) return "ok";
  if (eventType.startsWith("telemetry.")) return "warn";
  return "neutral";
}

export function payloadPreview(payload: Record<string, unknown>): string {
  try {
    const str = JSON.stringify(payload);
    return str.length > 60 ? str.slice(0, 60) + "…" : str;
  } catch {
    return "";
  }
}

export type EventStreamOptions = {
  intervalMs?: number;
  /**
   * Sprint 8 R4 NU-F05: when true, fetch from `/api/v1/events/my-activity`
   * which is scoped to the current user's own device streams. Used on
   * the Dashboard activity widget so fresh users don't see cross-org
   * telemetry noise. Defaults to false for back-compat with the /events
   * page which needs the global system stream.
   */
  scope?: "system" | "my";
};

export function useEventStream(
  intervalMsOrOptions: number | EventStreamOptions = 10_000,
) {
  // Back-compat: accept either a plain interval number or an options object.
  const opts: EventStreamOptions =
    typeof intervalMsOrOptions === "number"
      ? { intervalMs: intervalMsOrOptions }
      : intervalMsOrOptions;
  const intervalMs = opts.intervalMs ?? 10_000;
  const scope = opts.scope ?? "system";

  const events = ref<StreamEvent[]>([]);
  const loading = ref(true);
  const paused = ref(false);
  const error = ref<string | null>(null);

  async function fetchEvents(): Promise<void> {
    if (paused.value) return;
    try {
      // Sprint 3.5 bugfix: backend returns {stream, cursor, next_cursor, items}
      // not a bare array. The old code assigned the dict directly to
      // events.value, and then visibleEvents.computed's .slice() threw
      // "TypeError: h.value.slice is not a function" on every Dashboard
      // load — the entire "Aktuelle Alarme / activity feed" widget was
      // broken. Fixed by unwrapping .items, with a fallback to [] if the
      // backend ever changes shape back (and accepting bare arrays for
      // forward-compat).
      const path =
        scope === "my"
          ? "/api/v1/events/my-activity?limit=20"
          : "/api/v1/events?limit=20";
      const resp = await apiFetch<StreamEvent[] | { items?: StreamEvent[] }>(path);
      if (Array.isArray(resp)) {
        events.value = resp;
      } else if (resp && Array.isArray((resp as { items?: StreamEvent[] }).items)) {
        events.value = (resp as { items: StreamEvent[] }).items;
      } else {
        events.value = [];
      }
      error.value = null;
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : "Failed to load events";
    } finally {
      loading.value = false;
    }
  }

  function togglePause(): void {
    paused.value = !paused.value;
  }

  const poller = createPoller(fetchEvents, intervalMs);

  onMounted(() => poller.start());
  onUnmounted(() => poller.stop());

  return { events, loading, paused, togglePause, error };
}
