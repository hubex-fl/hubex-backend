// ─── Visualization Types ────────────────────────────────────────────────────
// Central type registry for the variable stream visualization system.
// Compatible with M20 Dashboard Builder (widgets are self-contained).

export type VizType =
  | "sparkline"        // SVG inline sparkline — int/float list view
  | "line_chart"       // Chart.js time series — int/float detail
  | "gauge"            // SVG radial gauge — int/float with min/max
  | "bool"             // Status dot + event timeline — bool
  | "log"              // Scrolling monospace log — string
  | "json"             // Collapsible JSON tree — json/object
  | "map"              // Leaflet pin (lazy) — json {lat,lng}
  | "image"            // Auto-refreshing img — string (URL)
  | "control_toggle"   // Interactive toggle — bool (read_write)
  | "control_slider"   // Interactive slider — int/float (read_write)
  | "html_template"    // Custom HTML with template variables
  | "auto";            // Resolved at render time from value_type

// A single time-series data point from /api/v1/variables/history
export interface VizDataPoint {
  t: number;             // Unix timestamp (seconds)
  v: number | null;      // numeric value (for int/float)
  raw: unknown;          // original value_json (any type)
  source: string;        // "user" | "device" | "telemetry" | "system"
}

// Props passed to every VizWidget (and all sub-widgets)
export interface VizWidgetProps {
  // Identity
  variableKey: string;
  label?: string;
  unit?: string;

  // Type hints
  valueType: "string" | "int" | "float" | "bool" | "json";
  displayHint?: string | null;  // raw display_hint from backend

  // Current value (for live display)
  currentValue?: unknown;

  // History data (pre-fetched or via useVariableHistory)
  points?: VizDataPoint[];
  loading?: boolean;

  // Constraints (for gauge)
  min?: number | null;
  max?: number | null;

  // Device context (scoped variables)
  deviceUid?: string | null;
  scope?: "device" | "global";

  // Display options
  height?: number;      // px, default varies per widget
  compact?: boolean;    // for embedded / table cell mode
  showHeader?: boolean; // default true
  timeRange?: "1h" | "6h" | "24h" | "7d" | "30d";
}

// Color palette — Grafana-inspired, dark-mode first
export const VIZ_COLORS = {
  blue:   "#58a6ff",
  green:  "#56d364",
  red:    "#f85149",
  yellow: "#e3b341",
  purple: "#bc8cff",
  cyan:   "#39d0d8",
  orange: "#f0883e",
  gray:   "#8b949e",
  muted:  "#30363d",
  bg:     "#0d1117",
  panel:  "#161b22",
  border: "#30363d",
  text:   "#e6edf3",
  label:  "#8b949e",
} as const;

// Chart.js default dataset style (Grafana-like)
export function defaultDatasetStyle(color = VIZ_COLORS.blue) {
  return {
    borderColor: color,
    backgroundColor: color + "1a", // 10% alpha fill
    borderWidth: 1.5,
    pointRadius: 0,
    pointHoverRadius: 3,
    tension: 0.3,
    fill: true,
  };
}
