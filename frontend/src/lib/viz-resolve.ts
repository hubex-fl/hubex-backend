// ─── Viz Type Resolver ──────────────────────────────────────────────────────
// Maps (value_type, display_hint) → concrete VizType.
// Single source of truth — used by VizWidget and list views alike.

import type { VizType } from "./viz-types";

type ValueType = "string" | "int" | "float" | "bool" | "json";

// Explicit display_hint values from the backend
const HINT_MAP: Record<string, VizType> = {
  line_chart:      "line_chart",
  gauge:           "gauge",
  sparkline:       "sparkline",
  map:             "map",
  image:           "image",
  toggle:          "bool",
  log:             "log",
  json:            "json",
  control_toggle:  "control_toggle",
  control_slider:  "control_slider",
  html_template:   "html_template",
  auto:            "auto",
};

// Default viz per value_type when no hint is set or hint is "auto"
const DEFAULT_BY_TYPE: Record<ValueType, VizType> = {
  int:    "sparkline",
  float:  "sparkline",
  bool:   "bool",
  string: "log",
  json:   "json",
};

/**
 * Sprint 8 R3-F06 helper: detect GPS shape `{lat, lng}` (or
 * `{latitude, longitude}` or `{lat, lon}`) inside a JSON current
 * value so we can auto-pick the map widget without the user having
 * to manually set display_hint='map'.
 */
function looksLikeGps(value: unknown): boolean {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const obj = value as Record<string, unknown>;
  const lat = obj.lat ?? obj.latitude;
  const lng = obj.lng ?? obj.longitude ?? obj.lon;
  const latN = Number(lat);
  const lngN = Number(lng);
  return (
    !Number.isNaN(latN) &&
    !Number.isNaN(lngN) &&
    latN >= -90 &&
    latN <= 90 &&
    lngN >= -180 &&
    lngN <= 180
  );
}

/**
 * Resolve which visualization to use.
 * @param valueType  - backend value_type ("int", "float", "bool", "string", "json")
 * @param displayHint - optional backend display_hint string
 * @param compact    - when true, prefer inline variants (sparkline over line_chart)
 * @param currentValue - optional current value for auto-detection (e.g. GPS shape)
 */
export function resolveVizType(
  valueType: ValueType,
  displayHint?: string | null,
  compact = false,
  currentValue?: unknown,
): VizType {
  // 1. Explicit valid hint → use it
  if (displayHint && displayHint !== "auto") {
    const mapped = HINT_MAP[displayHint];
    if (mapped && mapped !== "auto") return mapped;
  }

  // 2. Sprint 8 R3-F06: auto-detect GPS shape for JSON values.
  // If display_hint is "auto" or unset AND value_type is json AND
  // the current value parses as a valid lat/lng pair, switch to
  // the map widget. Previously GPS variables defaulted to the
  // json-tree viewer which is technically correct but useless
  // when a map is what the user wants.
  if (valueType === "json" && looksLikeGps(currentValue)) {
    return "map";
  }

  // 3. Compact override: never show large chart in compact mode
  const base = DEFAULT_BY_TYPE[valueType] ?? "log";
  if (compact && base === "line_chart") return "sparkline";

  return base;
}

/**
 * Human-readable label for a viz type.
 */
export function vizTypeLabel(type: VizType): string {
  const labels: Record<VizType, string> = {
    sparkline:       "Sparkline",
    line_chart:      "Line Chart",
    gauge:           "Gauge",
    bool:            "Status",
    log:             "Log",
    json:            "JSON",
    map:             "Map",
    image:           "Image",
    control_toggle:  "Toggle Control",
    control_slider:  "Slider Control",
    html_template:   "Custom HTML",
    auto:            "Auto",
  };
  return labels[type] ?? type;
}

/**
 * All selectable display hints for the definition editor UI.
 */
export const DISPLAY_HINT_OPTIONS: { value: string; label: string }[] = [
  { value: "auto",       label: "Auto (inferred from type)" },
  { value: "sparkline",  label: "Sparkline — inline trend" },
  { value: "line_chart", label: "Line Chart — full time series" },
  { value: "gauge",      label: "Gauge — radial with min/max" },
  { value: "toggle",     label: "Toggle — boolean status" },
  { value: "log",        label: "Log — scrolling text" },
  { value: "json",       label: "JSON — collapsible tree" },
  { value: "map",        label: "Map — GPS pin (lat/lng)" },
  { value: "image",      label: "Image — URL preview" },
];
