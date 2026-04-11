<template>
  <!--
    VizHtmlTemplate — Custom HTML widget with template variable substitution.
    Renders user-authored HTML inside a sandboxed iframe (no script execution).
    Template variables like {{value}}, {{unit}}, {{device:name}} are replaced
    with live data before rendering.
  -->
  <div class="viz-html-template" :style="{ height: `${height}px` }">
    <iframe
      ref="iframeRef"
      :srcdoc="renderedHtml"
      sandbox="allow-same-origin"
      class="html-frame"
      :style="{ height: `${height}px` }"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import type { VizDataPoint } from "../../lib/viz-types";
import { fmtAgeSeconds } from "../../lib/relativeTime";

export interface VizHtmlTemplateProps {
  htmlTemplate?: string;
  currentValue?: unknown;
  points?: VizDataPoint[];
  unit?: string;
  label?: string;
  deviceName?: string;
  deviceStatus?: string;
  variableKey?: string;
  height?: number;
  /** Map of variable keys to their current values for {{value:key}} syntax */
  variableValues?: Record<string, unknown>;
  /** Map of variable keys to their units */
  variableUnits?: Record<string, string>;
}

const props = withDefaults(defineProps<VizHtmlTemplateProps>(), {
  htmlTemplate: "",
  currentValue: undefined,
  points: () => [],
  unit: "",
  label: "",
  deviceName: "",
  deviceStatus: "unknown",
  variableKey: "",
  height: 200,
  variableValues: () => ({}),
  variableUnits: () => ({}),
});

const iframeRef = ref<HTMLIFrameElement | null>(null);

/** Format a value for display */
function formatValue(val: unknown): string {
  if (val === null || val === undefined) return "--";
  if (typeof val === "number") {
    return Number.isInteger(val) ? String(val) : val.toFixed(2);
  }
  if (typeof val === "boolean") return val ? "ON" : "OFF";
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}

/** Get last timestamp from points */
function lastTimestamp(): number | null {
  const pts = props.points ?? [];
  if (!pts.length) return null;
  return Math.max(...pts.map((p) => p.t));
}

/** Format timestamp as absolute time */
function formatTimestamp(ts: number | null): string {
  if (!ts) return "--";
  const d = new Date(ts * 1000);
  return d.toLocaleString();
}

/** Format timestamp as relative time ("2m ago" / "vor 2 Min") */
function formatRelativeTime(ts: number | null): string {
  if (!ts) return "--";
  const ago = Math.floor(Date.now() / 1000 - ts);
  if (ago < 0) return fmtAgeSeconds(0);
  return fmtAgeSeconds(ago);
}

/** Replace all template variables in the HTML string */
function resolveTemplate(html: string): string {
  let result = html;

  // {{value}} — current variable value
  result = result.replace(/\{\{value\}\}/g, formatValue(props.currentValue));

  // {{value:key}} — specific variable value by key
  result = result.replace(/\{\{value:([^}]+)\}\}/g, (_match, key: string) => {
    const k = key.trim();
    if (k === props.variableKey) return formatValue(props.currentValue);
    if (props.variableValues[k] !== undefined) return formatValue(props.variableValues[k]);
    return "--";
  });

  // {{unit}} — unit of the bound variable
  result = result.replace(/\{\{unit\}\}/g, props.unit || "");

  // {{unit:key}} — unit of a specific variable
  result = result.replace(/\{\{unit:([^}]+)\}\}/g, (_match, key: string) => {
    const k = key.trim();
    if (k === props.variableKey) return props.unit || "";
    return props.variableUnits[k] || "";
  });

  // {{device:name}} — device name
  result = result.replace(/\{\{device:name\}\}/g, props.deviceName || "--");

  // {{device:status}} — online/offline
  result = result.replace(/\{\{device:status\}\}/g, props.deviceStatus || "unknown");

  // {{label}} — widget label
  result = result.replace(/\{\{label\}\}/g, props.label || "");

  // {{timestamp}} — last update time (formatted)
  result = result.replace(/\{\{timestamp\}\}/g, formatTimestamp(lastTimestamp()));

  // {{timestamp:relative}} — "2m ago"
  result = result.replace(/\{\{timestamp:relative\}\}/g, formatRelativeTime(lastTimestamp()));

  // {{points:count}} — number of data points
  result = result.replace(/\{\{points:count\}\}/g, String(props.points?.length ?? 0));

  return result;
}

/** The full srcdoc HTML with base styling and resolved template */
const renderedHtml = computed(() => {
  const template = props.htmlTemplate || DEFAULT_TEMPLATE;
  const body = resolveTemplate(template);

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html, body {
    background: transparent;
    color: #e6edf3;
    font-family: Inter, -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 14px;
    line-height: 1.5;
    overflow: hidden;
  }
</style>
</head>
<body>${body}</body>
</html>`;
});

/** Default starter template */
const DEFAULT_TEMPLATE = `<div style="padding: 16px; font-family: Inter, sans-serif; color: #fff;">
  <h2 style="margin: 0 0 8px; font-size: 14px; opacity: 0.7;">{{device:name}}</h2>
  <div style="font-size: 36px; font-weight: bold;">{{value}} {{unit}}</div>
  <div style="margin-top: 8px; font-size: 12px; opacity: 0.5;">Updated {{timestamp:relative}}</div>
</div>`;

// Export the default template for use in the config modal
defineExpose({ DEFAULT_TEMPLATE });
</script>

<style scoped>
.viz-html-template {
  position: relative;
  width: 100%;
  overflow: hidden;
}

.html-frame {
  width: 100%;
  border: none;
  background: transparent;
  display: block;
}
</style>
