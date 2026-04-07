<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute } from "vue-router";
import { branding } from "../lib/branding";
import VizWidget from "../components/viz/VizWidget.vue";
import type { VizDataPoint } from "../lib/viz-types";
import type { TimeRange } from "../composables/useVariableHistory";

const { t } = useI18n();
const route = useRoute();
const token = route.params.token as string;

const AUTO_REFRESH_MS = 30_000;
const TIME_RANGES: TimeRange[] = ["1h", "6h", "24h", "7d", "30d"];

type Widget = {
  id: number;
  widget_type: string;
  variable_key: string | null;
  device_uid: string | null;
  label: string | null;
  unit: string | null;
  min_value: number | null;
  max_value: number | null;
  display_config: Record<string, unknown> | null;
  sort_order: number;
  grid_col: number;
  grid_row: number;
  grid_span_w: number;
  grid_span_h: number;
};

type Dashboard = {
  id: number;
  name: string;
  description: string | null;
  widgets: Widget[];
};

const dashboard = ref<Dashboard | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
const needsPin = ref(false);
const pinInput = ref("");
const pinError = ref("");
const currentPin = ref<string | undefined>(undefined);
const currentRange = ref<TimeRange>("1h");

// History data per widget
const historyData = ref<Record<number, VizDataPoint[]>>({});
const historyLoading = ref<Record<number, boolean>>({});
const currentValues = ref<Record<number, unknown>>({});

let refreshTimer: ReturnType<typeof setInterval> | null = null;

function rangeToFrom(range: TimeRange): number {
  const now = Math.floor(Date.now() / 1000);
  const map: Record<TimeRange, number> = {
    "1h": now - 3600,
    "6h": now - 21600,
    "24h": now - 86400,
    "7d": now - 604800,
    "30d": now - 2592000,
  };
  return map[range] ?? now - 3600;
}

async function loadDashboard(pin?: string) {
  loading.value = true;
  error.value = null;
  try {
    const url = `/api/v1/dashboards/public/${token}` + (pin ? `?pin=${pin}` : "");
    const res = await fetch(url);
    if (res.status === 403) {
      const data = await res.json();
      if (data.detail?.includes("PIN")) {
        needsPin.value = true;
        if (pin) pinError.value = t("pages.publicDashboard.invalidPin");
        loading.value = false;
        return;
      }
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    dashboard.value = await res.json();
    needsPin.value = false;
    if (pin) currentPin.value = pin;
    await loadAllHistory();
    startAutoRefresh();
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : t("pages.publicDashboard.loadError");
  } finally {
    loading.value = false;
  }
}

function submitPin() {
  if (pinInput.value.length >= 4) {
    pinError.value = "";
    loadDashboard(pinInput.value);
  }
}

// --- Variable history (public endpoint) ---

async function loadAllHistory() {
  if (!dashboard.value) return;
  for (const w of dashboard.value.widgets) {
    if (w.variable_key) {
      loadWidgetHistory(w);
    }
  }
}

async function loadWidgetHistory(widget: Widget) {
  if (!widget.variable_key) return;
  historyLoading.value[widget.id] = true;
  try {
    const params = new URLSearchParams();
    params.set("key", widget.variable_key);
    params.set("from", String(rangeToFrom(currentRange.value)));
    params.set("limit", "300");
    if (widget.device_uid) params.set("deviceUid", widget.device_uid);
    if (currentPin.value) params.set("pin", currentPin.value);

    const res = await fetch(`/api/v1/dashboards/public/${token}/history?${params.toString()}`);
    if (!res.ok) {
      historyData.value[widget.id] = [];
      return;
    }
    const resp = await res.json();
    const pts: VizDataPoint[] = (resp.points || []).map((p: any) => ({
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

function widgetPoints(widget: Widget): VizDataPoint[] {
  return historyData.value[widget.id] ?? [];
}

function widgetCurrentValue(widget: Widget): unknown {
  return currentValues.value[widget.id] ?? null;
}

function widgetValueType(widget: Widget): "string" | "int" | "float" | "bool" | "json" {
  const cfg = widget.display_config as Record<string, string> | null;
  if (cfg?.value_type) return cfg.value_type as "string" | "int" | "float" | "bool" | "json";
  if (["bool", "control_toggle"].includes(widget.widget_type)) return "bool";
  if (["gauge", "sparkline", "line_chart", "control_slider"].includes(widget.widget_type)) return "float";
  if (["map", "json"].includes(widget.widget_type)) return "json";
  return "string";
}

function widgetBodyHeight(widget: Widget): number {
  return Math.max(120, widget.grid_span_h * 40);
}

const sortedWidgets = computed<Widget[]>(() => {
  if (!dashboard.value) return [];
  return [...dashboard.value.widgets].sort((a, b) => a.sort_order - b.sort_order);
});

// --- Auto-refresh ---

function startAutoRefresh() {
  stopAutoRefresh();
  refreshTimer = setInterval(() => {
    if (dashboard.value) loadAllHistory();
  }, AUTO_REFRESH_MS);
}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
}

watch(currentRange, () => {
  if (dashboard.value) loadAllHistory();
});

onMounted(() => loadDashboard());
onUnmounted(() => stopAutoRefresh());
</script>

<template>
  <div class="min-h-screen bg-[var(--bg-base)] flex flex-col">
    <!-- Minimal header with branding -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-[var(--border)] bg-[var(--bg-surface)]">
      <div class="flex items-center gap-2">
        <img v-if="branding.logoUrl" :src="branding.logoUrl" :alt="branding.productName" class="h-6" />
        <span v-else class="text-sm font-bold text-[var(--primary)] tracking-widest">{{ branding.productName }}</span>
      </div>
      <!-- Time range selector (only when dashboard loaded) -->
      <div v-if="dashboard && dashboard.widgets.length" class="time-btns">
        <button
          v-for="r in TIME_RANGES"
          :key="r"
          class="tr-btn"
          :class="{ active: currentRange === r }"
          @click="currentRange = r"
        >{{ r }}</button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <p class="text-sm text-[var(--text-muted)]">{{ t('pages.publicDashboard.loading') }}</p>
    </div>

    <!-- PIN required -->
    <div v-else-if="needsPin" class="flex-1 flex items-center justify-center">
      <div class="bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl p-8 shadow-2xl w-full max-w-sm">
        <h2 class="text-lg font-semibold text-[var(--text-primary)] mb-2">{{ t('pages.publicDashboard.protectedTitle') }}</h2>
        <p class="text-xs text-[var(--text-muted)] mb-4">{{ t('pages.publicDashboard.enterPin') }}</p>
        <input
          v-model="pinInput"
          type="password"
          maxlength="6"
          class="w-full px-4 py-3 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-center text-xl tracking-[0.5em] font-mono text-[var(--text-primary)]"
          placeholder="****"
          autofocus
          @keyup.enter="submitPin"
        />
        <div v-if="pinError" class="mt-2 text-xs text-red-400">{{ pinError }}</div>
        <button
          class="mt-4 w-full px-4 py-2 rounded-lg bg-[var(--primary)] text-black font-medium text-sm"
          :disabled="pinInput.length < 4"
          @click="submitPin"
        >{{ t('pages.publicDashboard.unlock') }}</button>
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex-1 flex items-center justify-center">
      <div class="text-center">
        <p class="text-sm text-red-400">{{ error }}</p>
        <button class="mt-3 px-3 py-1.5 rounded-lg text-xs border border-[var(--border)] text-[var(--text-muted)]" @click="loadDashboard()">{{ t('pages.publicDashboard.retry') }}</button>
      </div>
    </div>

    <!-- Dashboard content -->
    <div v-else-if="dashboard" class="flex-1 overflow-auto p-4">
      <div class="mb-4">
        <h1 class="text-lg font-semibold text-[var(--text-primary)]">{{ dashboard.name }}</h1>
        <p v-if="dashboard.description" class="text-xs text-[var(--text-muted)] mt-1">{{ dashboard.description }}</p>
      </div>

      <div v-if="!dashboard.widgets.length" class="text-center py-12">
        <p class="text-sm text-[var(--text-muted)]">{{ t('pages.publicDashboard.noWidgets') }}</p>
      </div>

      <!-- 12-column grid layout matching DashboardView -->
      <div v-else class="db-grid">
        <div
          v-for="widget in sortedWidgets"
          :key="widget.id"
          class="db-widget-cell"
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
            :current-value="widgetCurrentValue(widget)"
            :points="widgetPoints(widget)"
            :loading="historyLoading[widget.id]"
            :unit="widget.unit || undefined"
            :min="widget.min_value"
            :max="widget.max_value"
            :height="widgetBodyHeight(widget)"
            :show-header="true"
            :time-range="currentRange"
            :writable="false"
            @range-change="(r) => { currentRange = r; loadWidgetHistory(widget) }"
          />
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="px-4 py-2 border-t border-[var(--border)] text-center flex-shrink-0">
      <span class="text-[10px] text-[var(--text-muted)]">{{ t('pages.publicDashboard.poweredBy', { name: branding.productName }) }}</span>
    </div>
  </div>
</template>

<style scoped>
/* 12-column grid matching DashboardView */
.db-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: 60px;
  gap: 8px;
  align-content: start;
}

.db-widget-cell {
  position: relative;
  min-height: 0;
}
.db-widget-cell > * {
  height: 100%;
}

/* Time range buttons */
.time-btns {
  display: flex;
  gap: 1px;
  background: var(--bg-elevated);
  border-radius: 5px;
  padding: 2px;
}
.tr-btn {
  padding: 3px 8px;
  font-size: 11px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  border-radius: 4px;
  transition: background 0.1s, color 0.1s;
}
.tr-btn:hover {
  background: var(--border);
  color: var(--text-base);
}
.tr-btn.active {
  background: var(--border);
  color: var(--primary);
}
</style>
