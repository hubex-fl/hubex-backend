<template>
  <!--
    VizWidget — Grafana-style panel container.
    Routes to the correct sub-component based on viz type.
    M20 Dashboard Builder will reuse this component directly.
  -->
  <div class="viz-widget" :class="{ 'widget-compact': compact }">
    <!-- Panel header (Grafana-style) -->
    <div v-if="showHeader" class="widget-header">
      <div class="widget-title-row">
        <span class="widget-icon">{{ vizIcon }}</span>
        <span class="widget-title">{{ label || variableKey }}</span>
        <span v-if="unit" class="widget-unit">{{ unit }}</span>
        <span v-if="category" class="widget-category">{{ category }}</span>
      </div>
      <div class="widget-meta">
        <!-- Time range selector (only for chart types) -->
        <div v-if="showTimeRange" class="time-range-tabs">
          <button
            v-for="r in TIME_RANGES"
            :key="r"
            class="tr-btn"
            :class="{ active: currentRange === r }"
            @click="$emit('range-change', r); currentRange = r"
          >{{ r }}</button>
        </div>
        <!-- Current value pill -->
        <span v-if="hasCurrentValue" class="widget-current">
          {{ formatCurrentValue }}
          <span v-if="unit" class="val-unit">{{ unit }}</span>
        </span>
        <span class="widget-type-badge">{{ vizTypeLabel(resolvedType) }}</span>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="widget-loading">
      <div class="skel-bar" v-for="i in 3" :key="i" :style="{ width: `${60 + i * 10}%`, animationDelay: `${i * 0.1}s` }" />
    </div>

    <!-- Widget body -->
    <div v-else class="widget-body">
      <!-- Sparkline -->
      <VizSparkline
        v-if="resolvedType === 'sparkline'"
        :points="points"
        :label="label"
        :color="widgetColor"
        :width="compact ? 80 : 160"
        :height="compact ? 28 : 48"
      />

      <!-- Line Chart -->
      <VizLineChart
        v-else-if="resolvedType === 'line_chart'"
        :points="points"
        :label="label"
        :unit="unit"
        :color="widgetColor"
        :height="height"
        :min="min ?? undefined"
        :max="max ?? undefined"
      />

      <!-- Gauge -->
      <div v-else-if="resolvedType === 'gauge'" class="gauge-wrap">
        <VizGauge
          :value="numericCurrent"
          :min="min"
          :max="max"
          :unit="unit"
          :size="compact ? 140 : 200"
        />
      </div>

      <!-- Bool indicator -->
      <VizBoolIndicator
        v-else-if="resolvedType === 'bool'"
        :currentValue="currentValue"
        :points="points"
        :compact="compact"
      />

      <!-- Log view -->
      <VizLogView
        v-else-if="resolvedType === 'log'"
        :points="points"
        :currentValue="currentValue"
        :maxHeight="height"
      />

      <!-- JSON viewer -->
      <VizJsonViewer
        v-else-if="resolvedType === 'json'"
        :currentValue="currentValue"
      />

      <!-- Map -->
      <VizMapView
        v-else-if="resolvedType === 'map'"
        :currentValue="currentValue"
        :height="height"
      />

      <!-- Image -->
      <VizImageView
        v-else-if="resolvedType === 'image'"
        :currentValue="currentValue"
        :maxHeight="height"
      />

      <!-- Control: Toggle -->
      <div v-else-if="resolvedType === 'control_toggle'" class="control-center">
        <VizControlToggle
          :model-value="Boolean(controlValue)"
          @change="handleControlChange"
        />
      </div>

      <!-- Control: Slider -->
      <div v-else-if="resolvedType === 'control_slider'" class="control-center">
        <VizControlSlider
          :model-value="Number(controlValue) || 0"
          :min="min ?? 0"
          :max="max ?? 100"
          :unit="unit"
          @change="handleControlChange"
        />
      </div>

      <!-- Fallback -->
      <div v-else class="widget-unknown">
        <code>{{ currentValue }}</code>
      </div>
    </div>

    <!-- Panel footer: last updated + point count -->
    <div v-if="!compact && points.length" class="widget-footer">
      <span>{{ points.length }} points</span>
      <span v-if="lastUpdated">· {{ lastUpdated }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import type { VizDataPoint, VizWidgetProps } from "../../lib/viz-types";
import { VIZ_COLORS } from "../../lib/viz-types";
import { resolveVizType, vizTypeLabel } from "../../lib/viz-resolve";
import type { TimeRange } from "../../composables/useVariableHistory";

import VizSparkline      from "./VizSparkline.vue";
import VizLineChart      from "./VizLineChart.vue";
import VizGauge          from "./VizGauge.vue";
import VizBoolIndicator  from "./VizBoolIndicator.vue";
import VizLogView        from "./VizLogView.vue";
import VizJsonViewer     from "./VizJsonViewer.vue";
import VizMapView        from "./VizMapView.vue";
import VizImageView      from "./VizImageView.vue";
import VizControlToggle  from "./VizControlToggle.vue";
import VizControlSlider  from "./VizControlSlider.vue";

// Extended props for control widgets
interface VizWidgetExtProps extends VizWidgetProps {
  writable?: boolean;
  onControlChange?: (value: unknown) => void;
}

const props = withDefaults(defineProps<VizWidgetExtProps>(), {
  points:      () => [],
  loading:     false,
  compact:     false,
  showHeader:  true,
  height:      220,
  timeRange:   "1h",
  writable:    false,
});

const emit = defineEmits<{
  "range-change": [range: TimeRange];
  "control-change": [value: unknown];
}>();

const controlValue = ref<unknown>(props.currentValue ?? null);

function handleControlChange(val: unknown) {
  controlValue.value = val;
  emit("control-change", val);
  if (props.onControlChange) props.onControlChange(val);
}

const TIME_RANGES: TimeRange[] = ["1h", "6h", "24h", "7d", "30d"];
const currentRange = ref<TimeRange>(props.timeRange ?? "1h");

const resolvedType = computed(() =>
  resolveVizType(props.valueType, props.displayHint, props.compact)
);

const showTimeRange = computed(() =>
  !props.compact && ["line_chart", "sparkline", "log"].includes(resolvedType.value)
);

const widgetColor = computed(() => {
  switch (props.valueType) {
    case "bool":  return VIZ_COLORS.green;
    case "string":return VIZ_COLORS.purple;
    case "json":  return VIZ_COLORS.cyan;
    default:      return VIZ_COLORS.blue;
  }
});

const vizIcon = computed(() => {
  const icons: Record<string, string> = {
    sparkline:       "〜",
    line_chart:      "📈",
    gauge:           "◎",
    bool:            "●",
    log:             "≡",
    json:            "{}",
    map:             "⌖",
    image:           "🖼",
    control_toggle:  "⏻",
    control_slider:  "⊟",
    auto:            "◈",
  };
  return icons[resolvedType.value] ?? "◈";
});

const hasCurrentValue = computed(() =>
  props.currentValue !== null && props.currentValue !== undefined
);

const formatCurrentValue = computed(() => {
  const v = props.currentValue;
  if (v === null || v === undefined) return "";
  if (typeof v === "number") {
    return Number.isInteger(v) ? String(v) : v.toFixed(2);
  }
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "object") return "{ … }";
  return String(v).slice(0, 32);
});

const numericCurrent = computed(() => {
  const v = props.currentValue;
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return isNaN(n) ? null : n;
});

const lastUpdated = computed(() => {
  const pts = props.points ?? [];
  if (!pts.length) return null;
  const last = Math.max(...pts.map((p) => p.t));
  const ago = Math.floor(Date.now() / 1000 - last);
  if (ago < 60)   return `${ago}s ago`;
  if (ago < 3600) return `${Math.floor(ago / 60)}m ago`;
  return `${Math.floor(ago / 3600)}h ago`;
});

// category prop — may not be part of VizWidgetProps but injected externally
const category = computed(() => (props as unknown as { category?: string }).category ?? null);
</script>

<style scoped>
/* ── Panel shell (Grafana-style) ──────────────────────── */
.viz-widget {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: border-color 0.15s;
}
.viz-widget:hover {
  border-color: #484f58;
}
.widget-compact {
  background: transparent;
  border: none;
  border-radius: 0;
}
.widget-compact:hover { border: none; }

/* ── Header ────────────────────────────────────────────── */
.widget-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px 6px;
  border-bottom: 1px solid #21262d;
  flex-shrink: 0;
}
.widget-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.widget-icon {
  font-size: 12px;
  opacity: 0.7;
  flex-shrink: 0;
}
.widget-title {
  font-size: 12px;
  font-weight: 500;
  color: #c9d1d9;
  font-family: monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.widget-unit {
  font-size: 11px;
  color: #8b949e;
  flex-shrink: 0;
}
.widget-category {
  font-size: 10px;
  color: #58a6ff;
  background: #58a6ff11;
  padding: 1px 5px;
  border-radius: 10px;
  flex-shrink: 0;
}
.widget-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* ── Time range tabs ────────────────────────────────────── */
.time-range-tabs {
  display: flex;
  gap: 1px;
  background: #21262d;
  border-radius: 4px;
  padding: 2px;
}
.tr-btn {
  padding: 2px 6px;
  font-size: 10px;
  color: #8b949e;
  border-radius: 3px;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
  white-space: nowrap;
}
.tr-btn:hover   { background: #30363d; color: #c9d1d9; }
.tr-btn.active  { background: #30363d; color: #58a6ff; }

/* ── Current value pill ─────────────────────────────────── */
.widget-current {
  font-family: monospace;
  font-size: 12px;
  color: #e6edf3;
  font-weight: 600;
}
.val-unit { color: #8b949e; font-weight: 400; margin-left: 2px; }

.widget-type-badge {
  font-size: 9px;
  color: #484f58;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

/* ── Body ──────────────────────────────────────────────── */
.widget-body {
  padding: 12px;
  flex: 1;
  min-height: 0;
}
.gauge-wrap {
  display: flex;
  justify-content: center;
}
.widget-unknown {
  font-family: monospace;
  font-size: 12px;
  color: #8b949e;
  word-break: break-all;
}
.control-center {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 80px;
  padding: 8px;
}

/* ── Loading skeleton ───────────────────────────────────── */
.widget-loading {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.skel-bar {
  height: 8px;
  background: linear-gradient(90deg, #21262d 25%, #30363d 50%, #21262d 75%);
  background-size: 200% 100%;
  border-radius: 4px;
  animation: skel-shimmer 1.4s infinite;
}
@keyframes skel-shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ── Footer ─────────────────────────────────────────────── */
.widget-footer {
  display: flex;
  gap: 6px;
  padding: 4px 12px 6px;
  font-size: 10px;
  color: #484f58;
  border-top: 1px solid #21262d;
  flex-shrink: 0;
}
</style>
