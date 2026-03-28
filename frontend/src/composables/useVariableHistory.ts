// ─── useVariableHistory ──────────────────────────────────────────────────────
// Polling composable for variable time-series data.
// Pattern matches useMetrics.ts — start/stop on mount/unmount.

import { ref, watch, onMounted, onUnmounted } from "vue";
import { apiFetch } from "../lib/api";
import { createPoller } from "../lib/poller";
import type { VizDataPoint } from "../lib/viz-types";

export type TimeRange = "1h" | "6h" | "24h" | "7d" | "30d";

const RANGE_SECONDS: Record<TimeRange, number> = {
  "1h":  3_600,
  "6h":  21_600,
  "24h": 86_400,
  "7d":  604_800,
  "30d": 2_592_000,
};

// Target ~200 visible data points regardless of range
function downsampleBucket(range: TimeRange): number {
  return Math.max(1, Math.floor(RANGE_SECONDS[range] / 200));
}

interface BackendHistoryPoint {
  t: number;
  v: number | null;
  raw: unknown;
  source: string;
}

interface BackendHistoryResponse {
  key: string;
  scope: string;
  device_uid: string | null;
  count: number;
  downsampled: boolean;
  bucket_seconds: number | null;
  points: BackendHistoryPoint[];
}

export interface UseVariableHistoryOptions {
  key: string;
  scope: "device" | "global";
  deviceUid?: string | null;
  timeRange?: TimeRange;
  intervalMs?: number;  // polling interval, default 15s; 0 = no polling
  limit?: number;
}

export function useVariableHistory(options: UseVariableHistoryOptions) {
  const points = ref<VizDataPoint[]>([]);
  const loading = ref(true);
  const error = ref<string | null>(null);
  const downsampled = ref(false);
  const count = ref(0);

  const range = ref<TimeRange>(options.timeRange ?? "1h");

  async function fetch(): Promise<void> {
    const now = Math.floor(Date.now() / 1000);
    const from = now - RANGE_SECONDS[range.value];
    const bucket = downsampleBucket(range.value);

    const q = new URLSearchParams({
      key: options.key,
      scope: options.scope,
      from: String(from),
      to:   String(now),
      limit: String(options.limit ?? 500),
      downsample: String(bucket),
    });
    if (options.deviceUid) q.set("deviceUid", options.deviceUid);

    try {
      const resp = await apiFetch<BackendHistoryResponse>(
        `/api/v1/variables/history?${q.toString()}`
      );
      points.value = resp.points as VizDataPoint[];
      downsampled.value = resp.downsampled;
      count.value = resp.count;
      error.value = null;
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : "Failed to load history";
    } finally {
      loading.value = false;
    }
  }

  const intervalMs = options.intervalMs ?? 15_000;
  let poller = intervalMs > 0 ? createPoller(fetch, intervalMs) : null;

  // Re-fetch when time range changes
  watch(range, () => {
    loading.value = true;
    fetch();
  });

  onMounted(() => {
    if (poller) poller.start();
    else fetch();
  });

  onUnmounted(() => {
    if (poller) poller.stop();
  });

  function setRange(r: TimeRange) {
    range.value = r;
  }

  return { points, loading, error, downsampled, count, range, setRange, refetch: fetch };
}
