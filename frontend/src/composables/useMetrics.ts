import { ref, onMounted, onUnmounted } from "vue";
import { apiFetch } from "../lib/api";
import { createPoller } from "../lib/poller";

export interface MetricsResponse {
  devices: { total: number; online: number; stale: number; offline: number };
  entities_total: number;
  effects_total: number;
  alerts: { firing: number; acknowledged: number };
  events_24h: number;
  webhooks_active: number;
  uptime_seconds: number;
}

export function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export function useMetrics(intervalMs = 10_000) {
  const data = ref<MetricsResponse | null>(null);
  const loading = ref(true);
  const error = ref<string | null>(null);

  async function fetchMetrics(): Promise<void> {
    try {
      data.value = await apiFetch<MetricsResponse>("/api/v1/metrics");
      error.value = null;
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : "Failed to load metrics";
    } finally {
      loading.value = false;
    }
  }

  const poller = createPoller(fetchMetrics, intervalMs);

  onMounted(() => poller.start());
  onUnmounted(() => poller.stop());

  return { data, loading, error };
}
