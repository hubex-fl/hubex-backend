import { ref, onMounted, onUnmounted } from "vue";
import { apiFetch } from "../lib/api";
import { createPoller } from "../lib/poller";

export interface AlertItem {
  id: number;
  rule_id: number;
  status: string;
  severity: "critical" | "warning" | "info";
  message: string;
  fired_at: string;
}

export function severityStatus(sev: string): "bad" | "warn" | "info" {
  if (sev === "critical") return "bad";
  if (sev === "warning") return "warn";
  return "info";
}

export function relativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(mins / 60);
  const days = Math.floor(hours / 24);
  if (days > 0) return `vor ${days}d`;
  if (hours > 0) return `vor ${hours}h`;
  if (mins > 0) return `vor ${mins}m`;
  return "gerade eben";
}

export function useRecentAlerts(intervalMs = 10_000) {
  const alerts = ref<AlertItem[]>([]);
  const loading = ref(true);
  const error = ref<string | null>(null);

  async function fetchAlerts(): Promise<void> {
    try {
      alerts.value = await apiFetch<AlertItem[]>("/api/v1/alerts?limit=5&status=firing");
      error.value = null;
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : "Failed to load alerts";
    } finally {
      loading.value = false;
    }
  }

  const poller = createPoller(fetchAlerts, intervalMs);

  onMounted(() => poller.start());
  onUnmounted(() => poller.stop());

  return { alerts, loading, error };
}
