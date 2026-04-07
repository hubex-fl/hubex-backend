<template>
  <!-- HA-style SVG radial gauge -->
  <svg
    :width="size"
    :height="size * 0.85"
    :viewBox="`0 0 200 170`"
    xmlns="http://www.w3.org/2000/svg"
    class="viz-gauge"
  >
    <!-- Track arc -->
    <path :d="trackPath" fill="none" :stroke="VIZ_COLORS.border" :stroke-width="strokeW" stroke-linecap="round" />

    <!-- Value arc -->
    <path :d="valuePath" fill="none" :stroke="arcColor" :stroke-width="strokeW" stroke-linecap="round"
      class="gauge-arc" />

    <!-- Center value -->
    <text x="100" y="100" text-anchor="middle" :fill="VIZ_COLORS.text"
      font-size="28" font-weight="600" font-family="monospace" class="gauge-val">
      {{ displayValue }}
    </text>

    <!-- Unit -->
    <text v-if="unit" x="100" y="118" text-anchor="middle" :fill="VIZ_COLORS.label"
      font-size="11" font-family="sans-serif">
      {{ unit }}
    </text>

    <!-- Min / Max labels -->
    <text :x="minLabelX" y="155" text-anchor="middle" :fill="VIZ_COLORS.label" font-size="10">
      {{ formatTick(resolvedMin) }}
    </text>
    <text :x="maxLabelX" y="155" text-anchor="middle" :fill="VIZ_COLORS.label" font-size="10">
      {{ formatTick(resolvedMax) }}
    </text>
  </svg>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { VIZ_COLORS } from "../../lib/viz-types";

const props = withDefaults(defineProps<{
  value?: number | null;
  min?: number | null;
  max?: number | null;
  unit?: string;
  size?: number;
  color?: string;
}>(), {
  value: null,
  min: null,
  max: null,
  unit: "",
  size: 200,
  color: "",
});

const strokeW = 14;
// Arc: 210° sweep from bottom-left to bottom-right (like HA)
const START_DEG = 210;
const END_DEG   = 330; // total sweep = 300°

function degToRad(d: number) { return (d * Math.PI) / 180; }

function polarToXY(deg: number, r: number): { x: number; y: number } {
  const rad = degToRad(deg);
  return {
    x: 100 + r * Math.cos(rad),
    y: 100 + r * Math.sin(rad),
  };
}

const R = 75; // radius

function arcPath(startDeg: number, endDeg: number): string {
  const s = polarToXY(startDeg, R);
  const e = polarToXY(endDeg,   R);
  const large = endDeg - startDeg > 180 ? 1 : 0;
  return `M ${s.x} ${s.y} A ${R} ${R} 0 ${large} 1 ${e.x} ${e.y}`;
}

const trackPath = computed(() => arcPath(START_DEG, START_DEG + 300));

const resolvedMin = computed(() => props.min ?? 0);
const resolvedMax = computed(() => props.max ?? 100);

const fraction = computed(() => {
  if (props.value === null || props.value === undefined) return 0;
  const f = (props.value - resolvedMin.value) / (resolvedMax.value - resolvedMin.value);
  return Math.max(0, Math.min(1, f));
});

const valuePath = computed(() => {
  const sweep = fraction.value * 300;
  if (sweep < 0.5) return "";
  return arcPath(START_DEG, START_DEG + sweep);
});

const arcColor = computed(() => {
  if (props.color) return props.color;
  const f = fraction.value;
  if (f < 0.5) return VIZ_COLORS.green;
  if (f < 0.8) return VIZ_COLORS.yellow;
  return VIZ_COLORS.red;
});

const displayValue = computed(() => {
  if (props.value === null || props.value === undefined) return "–";
  const n = props.value;
  if (Math.abs(n) >= 1000) return n.toFixed(0);
  if (Number.isInteger(n)) return String(n);
  return n.toFixed(1);
});

const minLabel = polarToXY(START_DEG, R + 22);
const maxLabel = polarToXY(START_DEG + 300, R + 22);
const minLabelX = minLabel.x;
const maxLabelX = maxLabel.x;

function formatTick(v: number) {
  if (Math.abs(v) >= 10000) return (v / 1000).toFixed(0) + "k";
  return String(v);
}
</script>

<style scoped>
.viz-gauge { display: block; overflow: visible; }
.gauge-arc { transition: stroke-dasharray 0.4s ease; }
.gauge-val { dominant-baseline: auto; }
</style>
