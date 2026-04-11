<template>
  <div class="viz-bool">
    <!-- Current state pill -->
    <div class="bool-pill">
      <span class="bool-dot" :class="isTrue ? 'dot-on' : 'dot-off'" />
      <span class="bool-label" :class="isTrue ? 'label-on' : 'label-off'">
        {{ isTrue ? onLabel : offLabel }}
      </span>
      <span class="bool-since" v-if="lastChange">since {{ lastChange }}</span>
    </div>

    <!-- Event timeline (recent history) -->
    <div v-if="!compact && points.length" class="bool-timeline">
      <div class="timeline-track">
        <template v-for="(seg, i) in segments" :key="i">
          <div
            class="timeline-seg"
            :class="seg.value ? 'seg-on' : 'seg-off'"
            :style="{ left: seg.left + '%', width: seg.width + '%' }"
            :title="seg.label"
          />
        </template>
      </div>
      <div class="timeline-labels">
        <span>{{ rangeStart }}</span>
        <span>{{ rangeEnd }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { VizDataPoint } from "../../lib/viz-types";
import { fmtAgeSeconds } from "../../lib/relativeTime";

const props = withDefaults(defineProps<{
  currentValue?: unknown;
  points?: VizDataPoint[];
  onLabel?: string;
  offLabel?: string;
  compact?: boolean;
}>(), {
  currentValue: null,
  points: () => [],
  onLabel: "ON",
  offLabel: "OFF",
  compact: false,
});

const isTrue = computed(() => {
  const v = props.currentValue;
  if (v === null || v === undefined) return false;
  if (typeof v === "boolean") return v;
  if (typeof v === "string") return v === "true" || v === "1" || v === "on";
  if (typeof v === "number") return v !== 0;
  return Boolean(v);
});

const lastChange = computed(() => {
  const sorted = [...props.points].sort((a, b) => b.t - a.t);
  const current = isTrue.value;
  // Find the last transition
  for (const p of sorted) {
    const pVal = Boolean(p.raw);
    if (pVal !== current) {
      const ago = Math.floor((Date.now() / 1000 - p.t));
      return fmtAgeSeconds(ago);
    }
  }
  return null;
});

// Build timeline segments from history
const segments = computed(() => {
  const pts = [...props.points].sort((a, b) => a.t - b.t);
  if (!pts.length) return [];

  const minT = pts[0].t;
  const maxT = pts[pts.length - 1].t;
  const range = maxT - minT || 1;

  return pts.map((p, i) => {
    const nextT = i < pts.length - 1 ? pts[i + 1].t : maxT;
    const left  = ((p.t - minT) / range) * 100;
    const width = ((nextT - p.t) / range) * 100;
    return {
      value: Boolean(p.raw),
      left,
      width: Math.max(width, 0.5),
      label: new Date(p.t * 1000).toLocaleTimeString(),
    };
  });
});

function fmtTime(ts: number) {
  return new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

const rangeStart = computed(() => {
  const pts = props.points;
  if (!pts.length) return "";
  return fmtTime(Math.min(...pts.map((p) => p.t)));
});
const rangeEnd = computed(() => {
  const pts = props.points;
  if (!pts.length) return "";
  return fmtTime(Math.max(...pts.map((p) => p.t)));
});
</script>

<style scoped>
.viz-bool { display: flex; flex-direction: column; gap: 10px; }

.bool-pill {
  display: flex; align-items: center; gap: 8px;
}
.bool-dot {
  width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
}
.dot-on  { background: #56d364; box-shadow: 0 0 6px #56d36488; }
.dot-off { background: #484f58; }

.bool-label {
  font-weight: 600; font-size: 13px; font-family: monospace;
}
.label-on  { color: #56d364; }
.label-off { color: #8b949e; }

.bool-since {
  font-size: 11px; color: #8b949e;
}

.bool-timeline { display: flex; flex-direction: column; gap: 4px; }
.timeline-track {
  position: relative; height: 8px; background: #21262d;
  border-radius: 4px; overflow: hidden;
}
.timeline-seg {
  position: absolute; top: 0; height: 100%;
  border-radius: 0;
}
.seg-on  { background: #56d364; }
.seg-off { background: #21262d; }

.timeline-labels {
  display: flex; justify-content: space-between;
  font-size: 10px; color: #8b949e;
}
</style>
