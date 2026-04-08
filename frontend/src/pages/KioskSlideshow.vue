<template>
  <div
    class="kiosk-slideshow"
    tabindex="0"
    @keydown.space.prevent="togglePause"
    @keydown.left="prevSlide"
    @keydown.right="nextSlide"
    @keydown.escape="exitKiosk"
    ref="kioskRef"
  >
    <!-- Header -->
    <div v-if="showHeader" class="kiosk-header">
      <div class="kiosk-title">{{ currentDashboardName }}</div>
      <div v-if="showClock" class="kiosk-clock">{{ clockTime }}</div>
      <div class="kiosk-status">
        <span v-if="paused" class="kiosk-paused">{{ t('dashboardEnhance.paused') }}</span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="kiosk-loading">
      <div class="kiosk-spinner"></div>
    </div>

    <!-- Dashboard content -->
    <div v-else class="kiosk-content">
      <TransitionGroup name="kiosk-fade">
        <div
          v-for="(db, idx) in dashboards"
          v-show="idx === currentIndex"
          :key="db.id"
          class="kiosk-dashboard"
        >
          <div class="kiosk-grid">
            <div
              v-for="widget in sortedWidgets(db)"
              :key="widget.id"
              class="kiosk-widget-cell"
              :style="{
                gridColumn: `${widget.grid_col} / span ${widget.grid_span_w}`,
                gridRow: `${widget.grid_row} / span ${widget.grid_span_h}`,
              }"
            >
              <VizWidget
                :variable-key="widget.variable_key || widget.label || `widget_${widget.id}`"
                :label="widget.label || widget.variable_key || 'Widget'"
                :value-type="widgetValueType(widget)"
                :display-hint="widget.widget_type"
                :current-value="currentValues[widget.id] ?? null"
                :points="historyData[widget.id] ?? []"
                :loading="historyLoading[widget.id]"
                :unit="widget.unit || undefined"
                :min="widget.min_value"
                :max="widget.max_value"
                :height="Math.max(120, widget.grid_span_h * 40)"
                :show-header="true"
                time-range="1h"
              />
            </div>
          </div>
        </div>
      </TransitionGroup>
    </div>

    <!-- Page dots -->
    <div v-if="dashboards.length > 1" class="kiosk-dots">
      <button
        v-for="(db, idx) in dashboards"
        :key="db.id"
        class="kiosk-dot"
        :class="{ active: idx === currentIndex }"
        @click="goToSlide(idx)"
        :title="db.name"
      ></button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import VizWidget from "../components/viz/VizWidget.vue";
import { getDashboard, type Dashboard, type DashboardWidget } from "../lib/dashboards";
import { getVariableHistory } from "../lib/variables";
import type { VizDataPoint } from "../lib/viz-types";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();

const kioskRef = ref<HTMLElement | null>(null);

// Parse query params
const dashboardIds = computed(() => {
  const ids = (route.query.ids as string) || "";
  return ids.split(",").map(Number).filter(n => n > 0);
});
const interval = computed(() => {
  const val = Number(route.query.interval) || 30;
  return Math.max(5, val);
});
const showHeader = computed(() => (route.query.header ?? "true") !== "false");
const showClock = computed(() => (route.query.clock ?? "true") !== "false");

// State
const dashboards = ref<Dashboard[]>([]);
const loading = ref(true);
const currentIndex = ref(0);
const paused = ref(false);
const clockTime = ref("");

// History data
const historyData = ref<Record<number, VizDataPoint[]>>({});
const historyLoading = ref<Record<number, boolean>>({});
const currentValues = ref<Record<number, unknown>>({});

let slideTimer: ReturnType<typeof setInterval> | null = null;
let clockTimer: ReturnType<typeof setInterval> | null = null;

const currentDashboardName = computed(() => {
  const db = dashboards.value[currentIndex.value];
  return db?.name || "";
});

onMounted(async () => {
  // Focus for keyboard events
  await nextTick();
  kioskRef.value?.focus();

  // Load all dashboards
  loading.value = true;
  try {
    const results: Dashboard[] = [];
    for (const id of dashboardIds.value) {
      try {
        const db = await getDashboard(id);
        results.push(db);
      } catch {
        // Skip dashboards that fail to load
      }
    }
    dashboards.value = results;

    // Load history for all widgets
    for (const db of results) {
      for (const w of db.widgets) {
        if (w.variable_key) {
          loadWidgetHistory(w);
        }
      }
    }
  } finally {
    loading.value = false;
  }

  // Start auto-slide timer
  startSlideTimer();

  // Start clock
  updateClock();
  clockTimer = setInterval(updateClock, 1000);
});

onUnmounted(() => {
  if (slideTimer) clearInterval(slideTimer);
  if (clockTimer) clearInterval(clockTimer);
});

function startSlideTimer() {
  if (slideTimer) clearInterval(slideTimer);
  if (dashboards.value.length <= 1) return;
  slideTimer = setInterval(() => {
    if (!paused.value) {
      currentIndex.value = (currentIndex.value + 1) % dashboards.value.length;
    }
  }, interval.value * 1000);
}

function updateClock() {
  const now = new Date();
  clockTime.value = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function togglePause() {
  paused.value = !paused.value;
}

function prevSlide() {
  currentIndex.value = (currentIndex.value - 1 + dashboards.value.length) % dashboards.value.length;
}

function nextSlide() {
  currentIndex.value = (currentIndex.value + 1) % dashboards.value.length;
}

function goToSlide(idx: number) {
  currentIndex.value = idx;
}

function exitKiosk() {
  window.close();
  // Fallback if window.close() is blocked
  router.push("/dashboards");
}

function sortedWidgets(db: Dashboard): DashboardWidget[] {
  return [...db.widgets].sort((a, b) => a.sort_order - b.sort_order);
}

function widgetValueType(widget: DashboardWidget): "string" | "int" | "float" | "bool" | "json" {
  const cfg = widget.display_config as Record<string, string> | null;
  if (cfg?.value_type) return cfg.value_type as "string" | "int" | "float" | "bool" | "json";
  if (["bool", "control_toggle"].includes(widget.widget_type)) return "bool";
  if (["gauge", "sparkline", "line_chart", "control_slider"].includes(widget.widget_type)) return "float";
  if (["map", "json"].includes(widget.widget_type)) return "json";
  return "string";
}

async function loadWidgetHistory(widget: DashboardWidget) {
  if (!widget.variable_key) return;
  historyLoading.value[widget.id] = true;
  try {
    const now = Math.floor(Date.now() / 1000);
    const scope = widget.device_uid ? "device" : "global";
    const resp = await getVariableHistory({
      key: widget.variable_key,
      scope,
      deviceUid: widget.device_uid || null,
      from: now - 3600,
      limit: 300,
    });
    const pts: VizDataPoint[] = resp.points.map((p) => ({
      t: p.t,
      v: p.v,
      raw: p.raw,
      source: p.source,
    }));
    historyData.value[widget.id] = pts;
    if (pts.length) {
      currentValues.value[widget.id] = pts[pts.length - 1].raw;
    }
  } catch {
    historyData.value[widget.id] = [];
  } finally {
    historyLoading.value[widget.id] = false;
  }
}
</script>

<style scoped>
.kiosk-slideshow {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: var(--bg-base, #111110);
  display: flex;
  flex-direction: column;
  outline: none;
  overflow: hidden;
}

/* Header */
.kiosk-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.kiosk-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-base);
}
.kiosk-clock {
  font-size: 14px;
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text-muted);
}
.kiosk-status {
  min-width: 60px;
  text-align: right;
}
.kiosk-paused {
  font-size: 11px;
  color: var(--primary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

/* Loading */
.kiosk-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.kiosk-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Content */
.kiosk-content {
  flex: 1;
  position: relative;
  overflow: hidden;
}
.kiosk-dashboard {
  position: absolute;
  inset: 0;
  overflow-y: auto;
  padding: 16px;
}
.kiosk-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: 60px;
  gap: 8px;
  align-content: start;
  min-height: 100%;
}
.kiosk-widget-cell {
  position: relative;
  min-height: 0;
  border-radius: 6px;
}
.kiosk-widget-cell > * {
  height: 100%;
}

/* Fade transition */
.kiosk-fade-enter-active,
.kiosk-fade-leave-active {
  transition: opacity 0.6s ease;
}
.kiosk-fade-enter-from {
  opacity: 0;
}
.kiosk-fade-leave-to {
  opacity: 0;
}

/* Page dots */
.kiosk-dots {
  display: flex;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  flex-shrink: 0;
}
.kiosk-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1px solid var(--text-muted);
  background: transparent;
  cursor: pointer;
  transition: all 0.2s;
  padding: 0;
}
.kiosk-dot.active {
  background: var(--primary);
  border-color: var(--primary);
  transform: scale(1.2);
}
.kiosk-dot:hover:not(.active) {
  border-color: var(--text-base);
}
</style>
