<template>
  <!-- Pure SVG sparkline — no Chart.js dependency, instant render -->
  <svg
    :width="width"
    :height="height"
    :viewBox="`0 0 ${width} ${height}`"
    xmlns="http://www.w3.org/2000/svg"
    class="viz-sparkline"
    :aria-label="`Sparkline for ${label}`"
  >
    <!-- Background -->
    <rect width="100%" height="100%" fill="transparent" rx="2" />

    <!-- No data state -->
    <template v-if="!validPoints.length">
      <line :x1="0" :y1="height / 2" :x2="width" :y2="height / 2"
        stroke="#30363d" stroke-width="1" stroke-dasharray="3 3" />
    </template>

    <!-- Area fill -->
    <template v-else>
      <defs>
        <linearGradient :id="gradId" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" :stop-color="color" stop-opacity="0.25" />
          <stop offset="100%" :stop-color="color" stop-opacity="0.02" />
        </linearGradient>
      </defs>

      <path v-if="areaPath" :d="areaPath" :fill="`url(#${gradId})`" />
      <polyline
        :points="svgPoints"
        fill="none"
        :stroke="color"
        :stroke-width="strokeWidth"
        stroke-linecap="round"
        stroke-linejoin="round"
      />

      <!-- Current value dot -->
      <circle
        v-if="lastPoint"
        :cx="lastPoint.x"
        :cy="lastPoint.y"
        r="2.5"
        :fill="color"
      />
    </template>
  </svg>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { VizDataPoint } from "../../lib/viz-types";
import { VIZ_COLORS } from "../../lib/viz-types";

const props = withDefaults(defineProps<{
  points?: VizDataPoint[];
  label?: string;
  color?: string;
  width?: number;
  height?: number;
  strokeWidth?: number;
}>(), {
  points: () => [],
  label: "value",
  color: VIZ_COLORS.blue,
  width: 80,
  height: 28,
  strokeWidth: 1.5,
});

// Unique gradient ID (avoid collisions when multiple sparklines on page)
const gradId = computed(() =>
  `sg-${props.label?.replace(/\W/g, "_")}-${Math.random().toString(36).slice(2, 6)}`
);

const validPoints = computed(() =>
  (props.points ?? []).filter((p) => p.v !== null && p.v !== undefined)
);

const svgPoints = computed(() => {
  const pts = validPoints.value;
  if (!pts.length) return "";

  const { width: W, height: H } = props;
  const pad = 3;
  const vals = pts.map((p) => p.v as number);
  const ts   = pts.map((p) => p.t);

  const minV = Math.min(...vals);
  const maxV = Math.max(...vals);
  const rangeV = maxV - minV || 1;
  const minT = Math.min(...ts);
  const maxT = Math.max(...ts);
  const rangeT = maxT - minT || 1;

  return pts
    .map((p, i) => {
      const x = pad + ((ts[i] - minT) / rangeT) * (W - pad * 2);
      const y = H - pad - (((p.v as number) - minV) / rangeV) * (H - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
});

const areaPath = computed(() => {
  const pts = validPoints.value;
  if (!pts.length) return "";

  const { width: W, height: H } = props;
  const pad = 3;
  const vals = pts.map((p) => p.v as number);
  const ts   = pts.map((p) => p.t);

  const minV = Math.min(...vals);
  const maxV = Math.max(...vals);
  const rangeV = maxV - minV || 1;
  const minT = Math.min(...ts);
  const maxT = Math.max(...ts);
  const rangeT = maxT - minT || 1;

  const coords = pts.map((p, i) => {
    const x = pad + ((ts[i] - minT) / rangeT) * (W - pad * 2);
    const y = H - pad - (((p.v as number) - minV) / rangeV) * (H - pad * 2);
    return { x, y };
  });

  const line = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
  const first = coords[0];
  const last  = coords[coords.length - 1];
  return `${line} L${last.x.toFixed(1)},${H} L${first.x.toFixed(1)},${H} Z`;
});

const lastPoint = computed(() => {
  const pts = validPoints.value;
  if (!pts.length) return null;

  const { width: W, height: H } = props;
  const pad = 3;
  const vals = pts.map((p) => p.v as number);
  const ts   = pts.map((p) => p.t);

  const minV = Math.min(...vals);
  const maxV = Math.max(...vals);
  const rangeV = maxV - minV || 1;
  const minT = Math.min(...ts);
  const maxT = Math.max(...ts);
  const rangeT = maxT - minT || 1;

  const last = pts[pts.length - 1];
  return {
    x: pad + ((last.t - minT) / rangeT) * (W - pad * 2),
    y: H - pad - (((last.v as number) - minV) / rangeV) * (H - pad * 2),
  };
});
</script>

<style scoped>
.viz-sparkline {
  display: block;
  overflow: visible;
}
</style>
