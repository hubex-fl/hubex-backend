import { apiFetch } from "./api";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface DashboardWidget {
  id: number;
  dashboard_id: number;
  widget_type: string;          // VizType or "control_toggle" | "control_slider"
  variable_key: string | null;
  device_uid: string | null;
  label: string | null;
  unit: string | null;
  min_value: number | null;
  max_value: number | null;
  display_config: Record<string, unknown> | null;
  grid_col: number;
  grid_row: number;
  grid_span_w: number;
  grid_span_h: number;
  sort_order: number;
  created_at: string;
}

export interface Dashboard {
  id: number;
  name: string;
  description: string | null;
  is_default: boolean;
  owner_id: number;
  sharing_mode: "private" | "org" | "public";
  created_at: string;
  updated_at: string;
  widgets: DashboardWidget[];
}

export interface DashboardSummary {
  id: number;
  name: string;
  description: string | null;
  is_default: boolean;
  sharing_mode: "private" | "org" | "public";
  widget_count: number;
  created_at: string;
  updated_at: string;
}

export interface DashboardCreate {
  name: string;
  description?: string | null;
  is_default?: boolean;
  sharing_mode?: "private" | "org" | "public";
}

export interface WidgetCreate {
  widget_type: string;
  variable_key?: string | null;
  device_uid?: string | null;
  label?: string | null;
  unit?: string | null;
  min_value?: number | null;
  max_value?: number | null;
  display_config?: Record<string, unknown> | null;
  grid_col?: number;
  grid_row?: number;
  grid_span_w?: number;
  grid_span_h?: number;
  sort_order?: number;
}

export interface LayoutItem {
  widget_id: number;
  grid_col: number;
  grid_row: number;
  grid_span_w: number;
  grid_span_h: number;
}

// ─── API ──────────────────────────────────────────────────────────────────────

const BASE = "/api/v1/dashboards";

export async function listDashboards(): Promise<DashboardSummary[]> {
  return apiFetch<DashboardSummary[]>(BASE);
}

export async function getDashboard(id: number): Promise<Dashboard> {
  return apiFetch<Dashboard>(`${BASE}/${id}`);
}

export async function getDefaultDashboard(): Promise<Dashboard> {
  return apiFetch<Dashboard>(`${BASE}/default`);
}

export async function createDashboard(data: DashboardCreate): Promise<Dashboard> {
  return apiFetch<Dashboard>(BASE, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateDashboard(id: number, data: Partial<DashboardCreate>): Promise<Dashboard> {
  return apiFetch<Dashboard>(`${BASE}/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteDashboard(id: number): Promise<void> {
  await apiFetch<void>(`${BASE}/${id}`, { method: "DELETE" });
}

export async function addWidget(dashboardId: number, data: WidgetCreate): Promise<DashboardWidget> {
  return apiFetch<DashboardWidget>(`${BASE}/${dashboardId}/widgets`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateWidget(
  dashboardId: number,
  widgetId: number,
  data: Partial<WidgetCreate>
): Promise<DashboardWidget> {
  return apiFetch<DashboardWidget>(`${BASE}/${dashboardId}/widgets/${widgetId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteWidget(dashboardId: number, widgetId: number): Promise<void> {
  await apiFetch<void>(`${BASE}/${dashboardId}/widgets/${widgetId}`, { method: "DELETE" });
}

export async function updateLayout(dashboardId: number, items: LayoutItem[]): Promise<Dashboard> {
  return apiFetch<Dashboard>(`${BASE}/${dashboardId}/layout`, {
    method: "PUT",
    body: JSON.stringify({ widgets: items }),
  });
}

// ─── Templates ────────────────────────────────────────────────────────────────

export interface DashboardTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;
  widgets: Omit<WidgetCreate, "grid_col" | "grid_row">[];
}

export const DASHBOARD_TEMPLATES: DashboardTemplate[] = [
  {
    id: "blank",
    name: "Blank",
    description: "Empty dashboard — build from scratch",
    icon: "⊡",
    widgets: [],
  },
  {
    id: "climate",
    name: "Climate Monitor",
    description: "Temperature, humidity, CO₂ sensors",
    icon: "🌡",
    widgets: [
      { widget_type: "gauge",      label: "Temperature", variable_key: null, unit: "°C", min_value: -20, max_value: 60, grid_span_w: 4, grid_span_h: 3 },
      { widget_type: "gauge",      label: "Humidity",    variable_key: null, unit: "%",  min_value: 0,   max_value: 100, grid_span_w: 4, grid_span_h: 3 },
      { widget_type: "line_chart", label: "History",     variable_key: null, grid_span_w: 8, grid_span_h: 4 },
    ],
  },
  {
    id: "server",
    name: "Server Monitor",
    description: "CPU, memory, disk, uptime",
    icon: "🖥",
    widgets: [
      { widget_type: "gauge",      label: "CPU",    variable_key: null, unit: "%",  min_value: 0, max_value: 100, grid_span_w: 3, grid_span_h: 3 },
      { widget_type: "gauge",      label: "Memory", variable_key: null, unit: "%",  min_value: 0, max_value: 100, grid_span_w: 3, grid_span_h: 3 },
      { widget_type: "sparkline",  label: "Disk",   variable_key: null, unit: "GB", grid_span_w: 3, grid_span_h: 3 },
      { widget_type: "log",        label: "Log",    variable_key: null, grid_span_w: 9, grid_span_h: 4 },
    ],
  },
  {
    id: "fleet",
    name: "Fleet Tracking",
    description: "GPS positions and device status",
    icon: "🗺",
    widgets: [
      { widget_type: "map",        label: "Location",  variable_key: null, grid_span_w: 8, grid_span_h: 6 },
      { widget_type: "bool",       label: "Online",    variable_key: null, grid_span_w: 4, grid_span_h: 3 },
      { widget_type: "sparkline",  label: "Speed",     variable_key: null, unit: "km/h", grid_span_w: 4, grid_span_h: 3 },
    ],
  },
  {
    id: "energy",
    name: "Energy Dashboard",
    description: "Power consumption, solar, battery",
    icon: "⚡",
    widgets: [
      { widget_type: "gauge",      label: "Power",   variable_key: null, unit: "W",  min_value: 0, max_value: 5000, grid_span_w: 4, grid_span_h: 3 },
      { widget_type: "gauge",      label: "Battery", variable_key: null, unit: "%",  min_value: 0, max_value: 100,  grid_span_w: 4, grid_span_h: 3 },
      { widget_type: "line_chart", label: "24h",     variable_key: null, grid_span_w: 12, grid_span_h: 4 },
    ],
  },
];
