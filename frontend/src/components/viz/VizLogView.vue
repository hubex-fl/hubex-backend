<template>
  <!-- Scrolling monospace log — n8n execution log style -->
  <div class="viz-log" :style="{ maxHeight: `${maxHeight}px` }" ref="scrollRef">
    <div v-if="!entries.length" class="log-empty">No data yet</div>
    <div
      v-for="(entry, i) in entries"
      :key="i"
      class="log-entry"
    >
      <span class="log-time">{{ entry.time }}</span>
      <span class="log-src" :class="`src-${entry.source}`">{{ entry.source }}</span>
      <span class="log-val">{{ entry.text }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick } from "vue";
import type { VizDataPoint } from "../../lib/viz-types";

const props = withDefaults(defineProps<{
  points?: VizDataPoint[];
  currentValue?: unknown;
  maxHeight?: number;
  autoScroll?: boolean;
}>(), {
  points: () => [],
  currentValue: null,
  maxHeight: 200,
  autoScroll: true,
});

const scrollRef = ref<HTMLElement | null>(null);

interface LogEntry {
  time: string;
  source: string;
  text: string;
}

const entries = computed((): LogEntry[] => {
  const pts = [...props.points].sort((a, b) => a.t - b.t);
  return pts.map((p) => ({
    time:   new Date(p.t * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    source: p.source || "sys",
    text:   p.raw === null || p.raw === undefined ? "(null)" : String(p.raw),
  }));
});

watch(entries, async () => {
  if (!props.autoScroll || !scrollRef.value) return;
  await nextTick();
  scrollRef.value.scrollTop = scrollRef.value.scrollHeight;
});
</script>

<style scoped>
.viz-log {
  overflow-y: auto;
  font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", monospace;
  font-size: 12px;
  line-height: 1.6;
  background: #0d1117;
  border-radius: 4px;
  padding: 8px 6px;
}
.log-empty {
  color: #484f58;
  font-size: 11px;
  text-align: center;
  padding: 12px;
}
.log-entry {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 1px 0;
}
.log-time {
  color: #484f58;
  flex-shrink: 0;
  font-size: 10px;
}
.log-src {
  flex-shrink: 0;
  font-size: 10px;
  padding: 0 4px;
  border-radius: 2px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.src-user     { color: #58a6ff; background: #58a6ff11; }
.src-device   { color: #56d364; background: #56d36411; }
.src-telemetry{ color: #e3b341; background: #e3b34111; }
.src-sys      { color: #8b949e; background: #8b949e11; }
.src-system   { color: #8b949e; background: #8b949e11; }

.log-val {
  color: #e6edf3;
  word-break: break-all;
}
</style>
