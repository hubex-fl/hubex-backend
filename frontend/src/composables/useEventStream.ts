import { ref, onMounted, onUnmounted } from "vue";
import { apiFetch } from "../lib/api";
import { createPoller } from "../lib/poller";

export interface StreamEvent {
  id: number;
  stream: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export function eventBadgeStatus(
  eventType: string
): "info" | "bad" | "ok" | "warn" | "neutral" {
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

export function useEventStream(intervalMs = 10_000) {
  const events = ref<StreamEvent[]>([]);
  const loading = ref(true);
  const paused = ref(false);
  const error = ref<string | null>(null);

  async function fetchEvents(): Promise<void> {
    if (paused.value) return;
    try {
      events.value = await apiFetch<StreamEvent[]>("/api/v1/events?limit=20");
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
