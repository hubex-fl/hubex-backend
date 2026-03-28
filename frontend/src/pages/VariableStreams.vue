<script setup lang="ts">
/**
 * Variable Streams — Real-time variable monitoring dashboard.
 * Grafana / Home Assistant / n8n-inspired design.
 * Foundation for M20 Dashboard Builder.
 */
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import {
  type VariableDefinition,
  type VariableScope,
  listDefinitions,
  getValue,
  getVariableHistory,
  type VariableHistoryPoint,
} from "../lib/variables";
import type { VizDataPoint } from "../lib/viz-types";
import { resolveVizType } from "../lib/viz-resolve";
import type { TimeRange } from "../composables/useVariableHistory";
import { apiFetch } from "../lib/api";
import type { Device } from "../composables/useDevices";

import UButton from "../components/ui/UButton.vue";
import USelect from "../components/ui/USelect.vue";
import UInput  from "../components/ui/UInput.vue";
import UBadge  from "../components/ui/UBadge.vue";
import VizWidget from "../components/viz/VizWidget.vue";

// ── State ──────────────────────────────────────────────────────────────
const definitions  = ref<VariableDefinition[]>([]);
const currentValues = ref<Record<string, unknown>>({});
const historyData  = ref<Record<string, VizDataPoint[]>>({});
const loading      = ref(true);
const error        = ref<string | null>(null);

// Device selector (M8d Step 6)
const deviceUid    = ref(localStorage.getItem("streams_device_uid") ?? "");
const availableDevices = ref<Device[]>([]);
const devicesLoading = ref(false);
const scopeFilter  = ref<"all" | VariableScope>("all");
const searchTerm   = ref("");
const timeRange    = ref<TimeRange>("1h");
const selectedKeys = ref<Set<string>>(new Set());
const gridCols     = ref<2 | 3 | 4>(3);
const fullscreenKey = ref<string | null>(null);
const refreshing   = ref(false);

// ── Grid col options ───────────────────────────────────────────────────
const COL_OPTIONS = [
  { value: 2, label: "2 cols" },
  { value: 3, label: "3 cols" },
  { value: 4, label: "4 cols" },
] as const;

const TIME_RANGES: { value: TimeRange; label: string }[] = [
  { value: "1h",  label: "1h" },
  { value: "6h",  label: "6h" },
  { value: "24h", label: "24h" },
  { value: "7d",  label: "7d" },
  { value: "30d", label: "30d" },
];

const SCOPE_OPTIONS = [
  { value: "all",    label: "All scopes" },
  { value: "global", label: "Global" },
  { value: "device", label: "Device" },
] as const;

const deviceOptions = computed(() => [
  { value: "", label: "All devices" },
  ...availableDevices.value.map((d) => ({
    value: d.device_uid,
    label: d.label || d.device_uid,
  })),
]);

// ── Filtered definitions ───────────────────────────────────────────────
const filteredDefs = computed(() => {
  const term = searchTerm.value.trim().toLowerCase();
  return definitions.value.filter((d) => {
    if (scopeFilter.value !== "all" && d.scope !== scopeFilter.value) return false;
    if (!term) return true;
    return d.key.toLowerCase().includes(term)
      || (d.category ?? "").toLowerCase().includes(term)
      || (d.description ?? "").toLowerCase().includes(term);
  });
});

const activeDefs = computed(() =>
  selectedKeys.value.size === 0
    ? filteredDefs.value
    : filteredDefs.value.filter((d) => selectedKeys.value.has(d.key))
);

// ── Load data ─────────────────────────────────────────────────────────
async function loadAll() {
  loading.value = true;
  error.value = null;
  try {
    const defs = await listDefinitions(scopeFilter.value === "all" ? undefined : scopeFilter.value);
    definitions.value = defs;
    await Promise.all([loadCurrentValues(defs), loadAllHistory(defs)]);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load";
  } finally {
    loading.value = false;
  }
}

async function loadCurrentValues(defs: VariableDefinition[]) {
  const vals: Record<string, unknown> = {};
  await Promise.all(
    defs.filter((d) => d.scope === "global" || !!deviceUid.value).map(async (d) => {
      try {
        const v = await getValue({
          key: d.key, scope: d.scope,
          deviceUid: d.scope === "device" ? deviceUid.value || undefined : undefined,
        });
        vals[d.key] = v.value;
      } catch { /* no value */ }
    })
  );
  currentValues.value = vals;
}

const RANGE_SECONDS: Record<TimeRange, number> = {
  "1h": 3600, "6h": 21600, "24h": 86400, "7d": 604800, "30d": 2592000,
};

async function loadAllHistory(defs: VariableDefinition[]) {
  const now = Math.floor(Date.now() / 1000);
  const rangeS = RANGE_SECONDS[timeRange.value];
  const bucket = Math.max(1, Math.floor(rangeS / 200));

  const hist: Record<string, VizDataPoint[]> = {};
  await Promise.all(
    defs.map(async (d) => {
      try {
        const resp = await getVariableHistory({
          key: d.key, scope: d.scope,
          deviceUid: d.scope === "device" ? deviceUid.value || undefined : undefined,
          from: now - rangeS, to: now,
          limit: 500, downsample: bucket,
        });
        hist[d.key] = resp.points as VizDataPoint[];
      } catch { /* ignore */ }
    })
  );
  historyData.value = hist;
}

// ── Auto-refresh ───────────────────────────────────────────────────────
let refreshTimer: ReturnType<typeof setInterval> | null = null;

function startRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(async () => {
    refreshing.value = true;
    try {
      await loadCurrentValues(definitions.value);
      await loadAllHistory(definitions.value);
    } finally {
      refreshing.value = false;
    }
  }, 15_000);
}

function stopRefresh() {
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
}

// ── Fullscreen ─────────────────────────────────────────────────────────
function openFullscreen(key: string) {
  fullscreenKey.value = key;
}
function closeFullscreen() {
  fullscreenKey.value = null;
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === "Escape") closeFullscreen();
}

// ── Toggle selection ───────────────────────────────────────────────────
function toggleSelect(key: string) {
  const next = new Set(selectedKeys.value);
  if (next.has(key)) next.delete(key); else next.add(key);
  selectedKeys.value = next;
}

function clearSelection() {
  selectedKeys.value = new Set();
}

// ── Watchers ────────────────────────────────────────────────────────────
watch([scopeFilter, deviceUid], loadAll);
watch(deviceUid, (v) => localStorage.setItem("streams_device_uid", v));
watch(timeRange, () => loadAllHistory(definitions.value));

// ── Load available devices for selector ───────────────────────────────────
async function loadDevices() {
  devicesLoading.value = true;
  try {
    const data = await apiFetch<Device[]>("/api/v1/devices?include_unclaimed=false");
    availableDevices.value = data.filter((d) => d.state === "claimed");
  } catch {
    availableDevices.value = [];
  } finally {
    devicesLoading.value = false;
  }
}

// ── Lifecycle ────────────────────────────────────────────────────────────
onMounted(() => {
  loadDevices();
  loadAll();
  startRefresh();
  window.addEventListener("keydown", handleKeydown);
});
onUnmounted(() => {
  stopRefresh();
  window.removeEventListener("keydown", handleKeydown);
});

const fullscreenDef = computed(() =>
  fullscreenKey.value ? definitions.value.find((d) => d.key === fullscreenKey.value) ?? null : null
);
</script>

<template>
  <div class="streams-page">
    <!-- ── Header ─────────────────────────────────────────────── -->
    <div class="streams-header">
      <div class="header-left">
        <div class="header-title-row">
          <span class="streams-icon">◈</span>
          <h1 class="streams-title">Variable Streams</h1>
          <span v-if="refreshing" class="refresh-dot" title="Refreshing…" />
        </div>
        <p class="streams-sub">Live variable monitoring · {{ activeDefs.length }} streams</p>
      </div>
      <div class="header-right">
        <!-- Time range tabs -->
        <div class="time-tabs">
          <button
            v-for="tr in TIME_RANGES" :key="tr.value"
            class="time-tab"
            :class="{ active: timeRange === tr.value }"
            @click="timeRange = tr.value"
          >{{ tr.label }}</button>
        </div>
        <!-- Grid cols -->
        <div class="grid-selector">
          <button
            v-for="opt in COL_OPTIONS" :key="opt.value"
            class="grid-btn"
            :class="{ active: gridCols === opt.value }"
            @click="gridCols = opt.value"
          >{{ opt.label }}</button>
        </div>
        <UButton size="sm" variant="secondary" @click="loadAll">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
          Refresh
        </UButton>
      </div>
    </div>

    <!-- ── Filters ────────────────────────────────────────────── -->
    <div class="streams-filters">
      <UInput v-model="searchTerm" placeholder="Filter streams…" class="filter-search" />
      <USelect v-model="scopeFilter" class="filter-scope">
        <option value="all">All scopes</option>
        <option value="global">Global</option>
        <option value="device">Device</option>
      </USelect>
      <USelect v-model="deviceUid" :options="deviceOptions" class="filter-device" :disabled="devicesLoading" />
      <button v-if="selectedKeys.size" class="clear-sel" @click="clearSelection">
        Clear selection ({{ selectedKeys.size }})
      </button>
    </div>

    <!-- ── Error ──────────────────────────────────────────────── -->
    <div v-if="error" class="streams-error">{{ error }}</div>

    <!-- ── Loading ───────────────────────────────────────────── -->
    <div v-if="loading" class="streams-grid" :style="{ '--cols': gridCols }">
      <div v-for="i in 6" :key="i" class="stream-skeleton" />
    </div>

    <!-- ── Empty ─────────────────────────────────────────────── -->
    <div v-else-if="!activeDefs.length" class="streams-empty">
      <span class="empty-icon">◈</span>
      <p>No variable streams match your filter</p>
      <UButton size="sm" variant="secondary" @click="searchTerm = ''; scopeFilter = 'all'">
        Clear filters
      </UButton>
    </div>

    <!-- ── Grid ──────────────────────────────────────────────── -->
    <div v-else class="streams-grid" :style="{ '--cols': gridCols }">
      <div
        v-for="def in activeDefs"
        :key="def.key"
        class="stream-card"
        :class="{ 'card-selected': selectedKeys.has(def.key) }"
      >
        <!-- Selection checkbox (top-left overlay) -->
        <div
          class="card-select-overlay"
          :class="{ selected: selectedKeys.has(def.key) }"
          @click.stop="toggleSelect(def.key)"
          title="Toggle selection"
        >
          <svg v-if="selectedKeys.has(def.key)" width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><polyline points="20 6 9 17 4 12"/></svg>
        </div>

        <!-- Fullscreen button (top-right overlay) -->
        <button class="card-expand-btn" @click="openFullscreen(def.key)" title="Fullscreen">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/>
            <line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>
          </svg>
        </button>

        <!-- VizWidget -->
        <VizWidget
          :variableKey="def.key"
          :label="def.key"
          :unit="def.unit ?? undefined"
          :valueType="def.value_type"
          :displayHint="def.display_hint"
          :currentValue="currentValues[def.key]"
          :points="historyData[def.key] ?? []"
          :min="def.min_value"
          :max="def.max_value"
          :height="180"
          :compact="false"
          :showHeader="true"
          :timeRange="timeRange"
          @range-change="(r) => { timeRange = r; loadAllHistory(definitions) }"
        />
      </div>
    </div>

    <!-- ── Fullscreen overlay ─────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="fullscreenKey && fullscreenDef" class="fullscreen-overlay" @click.self="closeFullscreen">
        <div class="fullscreen-panel">
          <div class="fullscreen-header">
            <span class="fs-title">{{ fullscreenDef.key }}</span>
            <div class="fs-actions">
              <div class="time-tabs">
                <button
                  v-for="tr in TIME_RANGES" :key="tr.value"
                  class="time-tab"
                  :class="{ active: timeRange === tr.value }"
                  @click="timeRange = tr.value; loadAllHistory(definitions)"
                >{{ tr.label }}</button>
              </div>
              <button class="fs-close" @click="closeFullscreen" title="Close (Esc)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
          </div>
          <div class="fullscreen-body">
            <VizWidget
              :variableKey="fullscreenDef.key"
              :label="fullscreenDef.key"
              :unit="fullscreenDef.unit ?? undefined"
              :valueType="fullscreenDef.value_type"
              :displayHint="'line_chart'"
              :currentValue="currentValues[fullscreenDef.key]"
              :points="historyData[fullscreenDef.key] ?? []"
              :min="fullscreenDef.min_value"
              :max="fullscreenDef.max_value"
              :height="400"
              :showHeader="false"
              :timeRange="timeRange"
            />
          </div>
          <div v-if="fullscreenDef.description" class="fullscreen-footer">
            <span class="fs-desc">{{ fullscreenDef.description }}</span>
            <span v-if="fullscreenDef.category" class="fs-cat">{{ fullscreenDef.category }}</span>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* ── Page ─────────────────────────────────────────────────── */
.streams-page {
  display: flex; flex-direction: column; gap: 16px;
  padding-bottom: 40px;
}

/* ── Header ─────────────────────────────────────────────────── */
.streams-header {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 16px;
  flex-wrap: wrap;
}
.header-left { display: flex; flex-direction: column; gap: 4px; }
.header-title-row { display: flex; align-items: center; gap: 10px; }
.streams-icon { font-size: 20px; color: #58a6ff; }
.streams-title { font-size: 20px; font-weight: 600; color: #e6edf3; margin: 0; }
.streams-sub { font-size: 12px; color: #8b949e; margin: 0; }
.refresh-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #58a6ff; animation: pulse 1s infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

.header-right { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

/* ── Time tabs ────────────────────────────────────────────── */
.time-tabs {
  display: flex; gap: 1px; background: #21262d; border-radius: 5px; padding: 2px;
}
.time-tab {
  padding: 3px 8px; font-size: 11px; color: #8b949e; border: none;
  background: transparent; border-radius: 3px; cursor: pointer;
  transition: all 0.1s;
}
.time-tab:hover  { background: #30363d; color: #c9d1d9; }
.time-tab.active { background: #30363d; color: #58a6ff; font-weight: 600; }

/* ── Grid selector ────────────────────────────────────────── */
.grid-selector {
  display: flex; gap: 1px; background: #21262d; border-radius: 5px; padding: 2px;
}
.grid-btn {
  padding: 3px 8px; font-size: 10px; color: #8b949e; border: none;
  background: transparent; border-radius: 3px; cursor: pointer;
}
.grid-btn.active { background: #30363d; color: #c9d1d9; }

/* ── Filters ─────────────────────────────────────────────── */
.streams-filters {
  display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
}
.filter-search { flex: 1; min-width: 160px; }
.filter-scope  { width: 130px; }
.filter-device { width: 200px; }
.clear-sel {
  font-size: 12px; color: #58a6ff; background: #58a6ff11; border: 1px solid #58a6ff33;
  border-radius: 4px; padding: 4px 10px; cursor: pointer;
  white-space: nowrap;
}
.clear-sel:hover { background: #58a6ff22; }

/* ── Error ───────────────────────────────────────────────── */
.streams-error {
  background: #3d1f1f; border: 1px solid #6e2020;
  border-radius: 6px; color: #f85149; font-size: 13px; padding: 10px 14px;
}

/* ── Grid ────────────────────────────────────────────────── */
.streams-grid {
  display: grid;
  grid-template-columns: repeat(var(--cols, 3), minmax(0, 1fr));
  gap: 12px;
}

/* ── Card ────────────────────────────────────────────────── */
.stream-card {
  position: relative;
  border-radius: 6px;
  transition: transform 0.1s, box-shadow 0.15s;
}
.stream-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 20px rgba(0,0,0,0.4);
}
.stream-card.card-selected {
  outline: 2px solid #58a6ff55;
  outline-offset: 1px;
}

/* Selection overlay (top-left circle) */
.card-select-overlay {
  position: absolute; top: 8px; left: 8px; z-index: 10;
  width: 16px; height: 16px; border-radius: 50%;
  border: 1px solid #30363d; background: #21262d;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: opacity 0.1s;
  color: #58a6ff;
}
.stream-card:hover .card-select-overlay,
.card-select-overlay.selected { opacity: 1; }
.card-select-overlay.selected { background: #58a6ff; border-color: #58a6ff; color: #fff; }

/* Expand button (top-right) */
.card-expand-btn {
  position: absolute; top: 8px; right: 8px; z-index: 10;
  width: 22px; height: 22px; border-radius: 4px;
  border: 1px solid #30363d; background: #21262d;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  color: #8b949e; opacity: 0; transition: opacity 0.1s;
}
.stream-card:hover .card-expand-btn { opacity: 1; }
.card-expand-btn:hover { color: #58a6ff; background: #30363d; }

/* ── Skeleton ─────────────────────────────────────────────── */
.stream-skeleton {
  height: 240px;
  background: linear-gradient(90deg, #21262d 25%, #30363d 50%, #21262d 75%);
  background-size: 200% 100%;
  border-radius: 6px;
  border: 1px solid #30363d;
  animation: shimmer 1.4s infinite;
}
@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }

/* ── Empty ───────────────────────────────────────────────── */
.streams-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; padding: 80px; color: #8b949e; font-size: 14px; text-align: center;
}
.empty-icon { font-size: 32px; color: #30363d; }

/* ── Fullscreen ──────────────────────────────────────────── */
.fullscreen-overlay {
  position: fixed; inset: 0; z-index: 9999;
  background: rgba(0,0,0,0.85);
  backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
  padding: 24px;
}
.fullscreen-panel {
  background: #161b22; border: 1px solid #30363d;
  border-radius: 10px; width: 100%; max-width: 1100px;
  overflow: hidden; display: flex; flex-direction: column;
  max-height: calc(100vh - 48px);
}
.fullscreen-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 20px 12px; border-bottom: 1px solid #21262d;
}
.fs-title { font-family: monospace; font-size: 16px; font-weight: 600; color: #e6edf3; }
.fs-actions { display: flex; align-items: center; gap: 10px; }
.fs-close {
  width: 28px; height: 28px; border-radius: 4px;
  background: #21262d; border: 1px solid #30363d;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  color: #8b949e;
}
.fs-close:hover { color: #f85149; }
.fullscreen-body { padding: 16px 20px; flex: 1; overflow: auto; }
.fullscreen-footer {
  padding: 10px 20px; border-top: 1px solid #21262d;
  display: flex; gap: 10px; align-items: center;
  font-size: 12px;
}
.fs-desc { color: #8b949e; }
.fs-cat {
  color: #58a6ff; background: #58a6ff11;
  padding: 2px 8px; border-radius: 10px;
  font-size: 10px;
}

/* ── Responsive ──────────────────────────────────────────── */
@media (max-width: 1024px) {
  .streams-grid { --cols: 2 !important; }
}
@media (max-width: 640px) {
  .streams-grid { --cols: 1 !important; }
  .header-right { flex-direction: column; align-items: flex-start; }
}
</style>
