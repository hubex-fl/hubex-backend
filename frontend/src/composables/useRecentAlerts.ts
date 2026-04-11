import { ref, onMounted, onUnmounted } from "vue";
import { apiFetch } from "../lib/api";
import { createPoller } from "../lib/poller";
import { i18n } from "../i18n";

export interface AlertItem {
  id: number;
  rule_id: number;
  status: string;
  // Sprint 3.5 bugfix: backend response actually doesn't include
  // `severity` on AlertEvent — it lives on AlertRule. For the dashboard
  // widget we accept either shape (events that happen to include it,
  // or fall back to "warning" as a visually-neutral default).
  severity?: "critical" | "warning" | "info";
  message: string;
  // Sprint 3.5 bugfix: backend returns `triggered_at`, not `fired_at`.
  // Keep `fired_at` as a fallback so the dashboard widget doesn't render
  // NaN times when the backend shape changes again. `relativeTime` in
  // the template should read from `firedAtFor(alert)` helper below.
  triggered_at?: string;
  fired_at?: string;
}

/**
 * Resolve the timestamp for an alert event regardless of backend naming.
 * Sprint 3.5: backend returns `triggered_at`, old code read `fired_at`.
 */
export function firedAtFor(a: AlertItem): string {
  return a.triggered_at || a.fired_at || "";
}

export function severityStatus(sev: string): "bad" | "warn" | "info" {
  if (sev === "critical") return "bad";
  if (sev === "warning") return "warn";
  return "info";
}

// Sprint 8 R2-F02 fix: previously hardcoded German strings "vor Xh" /
// "gerade eben" — leaked onto EN locale. Now routes through i18n.
export function relativeTime(dateStr: string): string {
  if (!dateStr) return "";
  const parsed = new Date(dateStr).getTime();
  if (isNaN(parsed)) return "";
  const diff = Date.now() - parsed;
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(mins / 60);
  const days = Math.floor(hours / 24);
  const t = i18n.global.t;
  if (days > 0) return t("dashboardsList.relative.daysAgo", { n: days });
  if (hours > 0) return t("dashboardsList.relative.hoursAgo", { n: hours });
  if (mins > 0) return t("dashboardsList.relative.minutesAgo", { n: mins });
  return t("dashboardsList.relative.justNow");
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
