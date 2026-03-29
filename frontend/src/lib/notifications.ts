import { apiFetch } from "./api";

export interface NotificationItem {
  id: number;
  type: string;
  severity: "info" | "warning" | "error" | "critical";
  title: string;
  message: string;
  entity_ref: string | null;
  read_at: string | null;
  created_at: string;
}

export async function fetchNotifications(unreadOnly = false, limit = 50): Promise<NotificationItem[]> {
  const params = new URLSearchParams();
  if (unreadOnly) params.set("unread_only", "true");
  params.set("limit", String(limit));
  return apiFetch<NotificationItem[]>(`/api/v1/notifications?${params}`);
}

export async function fetchUnreadCount(): Promise<number> {
  const r = await apiFetch<{ count: number }>("/api/v1/notifications/unread-count");
  return r.count;
}

export async function markRead(id: number): Promise<void> {
  await apiFetch(`/api/v1/notifications/${id}/read`, { method: "PATCH" });
}

export async function markAllRead(): Promise<void> {
  await apiFetch("/api/v1/notifications/read-all", { method: "PATCH" });
}

export async function deleteNotification(id: number): Promise<void> {
  await apiFetch(`/api/v1/notifications/${id}`, { method: "DELETE" });
}

export function severityColor(severity: string): string {
  switch (severity) {
    case "critical": return "var(--status-bad)";
    case "error":    return "var(--status-bad)";
    case "warning":  return "var(--status-warn)";
    default:         return "var(--status-info)";
  }
}
