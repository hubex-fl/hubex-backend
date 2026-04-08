<script setup lang="ts">
/**
 * Variable Streams — Clean, grouped live variable monitoring.
 * Progressive Disclosure: streams grouped by device, collapsed by default.
 * Click a group header to expand, click a stream row to see full detail.
 */
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useI18n } from "vue-i18n";
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
import UBadge  from "../components/ui/UBadge.vue";
import UEntitySelect from "../components/ui/UEntitySelect.vue";
import VizWidget from "../components/viz/VizWidget.vue";
import VizSparkline from "../components/viz/VizSparkline.vue";

const { t } = useI18n();

// ── State ──────────────────────────────────────────────────────────────
const definitions  = ref<VariableDefinition[]>([]);
const currentValues = ref<Record<string, unknown>>({});
const historyData  = ref<Record<string, VizDataPoint[]>>({});
const loading      = ref(true);
const error        = ref<string | null>(null);

// Device filter
const deviceUid    = ref(localStorage.getItem("streams_device_uid") ?? "");
const availableDevices = ref<Device[]>([]);
const devicesLoading = ref(false);
const searchTerm   = ref("");
const timeRange    = ref<TimeRange>("1h");
const refreshing   = ref(false);

// Progressive disclosure: expanded groups (collapsed by default)
const expandedGroups = ref<Set<string>>(new Set());

// Detail overlay for a single stream
const detailKey = ref<string | null>(null);

// ── Time range options ────────────────────────────────────────────────
const TIME_RANGES: { value: TimeRange; label: string }[] = [
  { value: "1h",  label: "1h" },
  { value: "6h",  label: "6h" },
  { value: "24h", label: "24h" },
  { value: "7d",  label: "7d" },
  { value: "30d", label: "30d" },
];

// ── Group definitions by scope/device ─────────────────────────────────
interface StreamGroup {
  id: string;        // "global" or device_uid
  label: string;
  isDevice: boolean;
  device?: Device;
  streams: VariableDefinition[];
}

const filteredDefs = computed(() => {
  const term = searchTerm.value.trim().toLowerCase();
  return definitions.value.filter((d) => {
    // If device filter is set, only show device-scoped vars
    if (deviceUid.value && d.scope === "device") return true;
    if (deviceUid.value && d.scope === "global") return true;
    if (!term) return true;
    return d.key.toLowerCase().includes(term)
      || (d.category ?? "").toLowerCase().includes(term)
      || (d.description ?? "").toLowerCase().includes(term);
  }).filter((d) => {
    if (!term) return true;
    return d.key.toLowerCase().includes(term)
      || (d.category ?? "").toLowerCase().includes(term)
      || (d.description ?? "").toLowerCase().includes(term);
  });
});

const streamGroups = computed<StreamGroup[]>(() => {
  const groups: StreamGroup[] = [];
  const globalStreams = filteredDefs.value.filter((d) => d.scope === "global");
  const deviceStreams = filteredDefs.value.filter((d) => d.scope === "device");

  if (globalStreams.length) {
    groups.push({
      id: "global",
      label: t('variableStreams.globalVariables'),
      isDevice: false,
      streams: globalStreams,
    });
  }

  if (deviceUid.value) {
    // When a specific device is selected, show device streams under that device
    const dev = availableDevices.value.find((d) => d.device_uid === deviceUid.value);
    if (deviceStreams.length) {
      groups.push({
        id: deviceUid.value,
        label: dev?.name || deviceUid.value,
        isDevice: true,
        device: dev,
        streams: deviceStreams,
      });
    }
  } else {
    // No device filter: show device-scoped streams grouped generically
    if (deviceStreams.length) {
      groups.push({
        id: "device-scoped",
        label: t('variableStreams.deviceVariables'),
        isDevice: true,
        streams: deviceStreams,
      });
    }
  }

  return groups;
});

const totalStreamCount = computed(() =>
  streamGroups.value.reduce((sum, g) => sum + g.streams.length, 0)
);

// ── Group toggle ──────────────────────────────────────────────────────
function toggleGroup(groupId: string) {
  const next = new Set(expandedGroups.value);
  if (next.has(groupId)) next.delete(groupId); else next.add(groupId);
  expandedGroups.value = next;
}

function isGroupExpanded(groupId: string): boolean {
  return expandedGroups.value.has(groupId);
}

// ── Format helpers ────────────────────────────────────────────────────
function formatValue(val: unknown): string {
  if (val === null || val === undefined) return "--";
  if (typeof val === "number") return Number.isInteger(val) ? String(val) : (val as number).toFixed(2);
  if (typeof val === "boolean") return val ? "true" : "false";
  if (typeof val === "object") return JSON.stringify(val).slice(0, 40);
  return String(val).slice(0, 40);
}

function lastUpdateText(key: string): string {
  const pts = historyData.value[key];
  if (!pts?.length) return "--";
  const last = Math.max(...pts.map((p) => p.t));
  const ago = Math.floor(Date.now() / 1000 - last);
  if (ago < 60)   return `${ago}s`;
  if (ago < 3600) return `${Math.floor(ago / 60)}m`;
  if (ago < 86400) return `${Math.floor(ago / 3600)}h`;
  return `${Math.floor(ago / 86400)}d`;
}

// ── Detail overlay ────────────────────────────────────────────────────
function openDetail(key: string) {
  detailKey.value = key;
}
function closeDetail() {
  detailKey.value = null;
}
function handleKeydown(e: KeyboardEvent) {
  if (e.key === "Escape") closeDetail();
}

const detailDef = computed(() =>
  detailKey.value ? definitions.value.find((d) => d.key === detailKey.value) ?? null : null
);

// ── Load data ─────────────────────────────────────────────────────────
async function loadAll() {
  loading.value = true;
  error.value = null;
  try {
    const defs = await listDefinitions();
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

// ── Auto-refresh ──────────────────────────────────────────────────────
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

// ── Load available devices ────────────────────────────────────────────
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

// ── Watchers ──────────────────────────────────────────────────────────
watch(deviceUid, (v) => {
  localStorage.setItem("streams_device_uid", v);
  loadAll();
});
watch(timeRange, () => loadAllHistory(definitions.value));

// ── Lifecycle ─────────────────────────────────────────────────────────
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
</script>

<template>
  <div class="streams-page">
    <!-- ── Header ─────────────────────────────────────────────── -->
    <div class="streams-header">
      <div class="header-left">
        <div class="header-title-row">
          <span class="streams-icon">◈</span>
          <h1 class="streams-title">{{ t('variables.streams') }}</h1>
          <span v-if="refreshing" class="refresh-dot" :title="t('variableStreams.refreshing')" />
        </div>
        <p class="streams-desc">{{ t('variableStreams.description') }}</p>
      </div>
      <div class="header-right">
        <div class="time-tabs">
          <button
            v-for="tr in TIME_RANGES" :key="tr.value"
            class="time-tab"
            :class="{ active: timeRange === tr.value }"
            @click="timeRange = tr.value"
          >{{ tr.label }}</button>
        </div>
        <UButton size="sm" variant="secondary" @click="loadAll">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
          {{ t('common.refresh') }}
        </UButton>
      </div>
    </div>

    <!-- ── Filters ────────────────────────────────────────────── -->
    <div class="streams-filters">
      <div class="filter-device-wrap">
        <UEntitySelect
          v-model="deviceUid"
          entity-type="device"
          :placeholder="t('variableStreams.filterByDevice')"
          :optional="true"
        />
      </div>
      <input
        v-model="searchTerm"
        type="text"
        class="filter-search"
        :placeholder="t('variableStreams.searchStreams')"
      />
      <span class="stream-count">{{ totalStreamCount }} {{ t('variableStreams.streamsLabel') }}</span>
    </div>

    <!-- ── Error ──────────────────────────────────────────────── -->
    <div v-if="error" class="streams-error">{{ error }}</div>

    <!-- ── Loading ───────────────────────────────────────────── -->
    <div v-if="loading" class="streams-loading">
      <div v-for="i in 3" :key="i" class="skeleton-group">
        <div class="skeleton-header" />
        <div class="skeleton-row" v-for="j in 2" :key="j" />
      </div>
    </div>

    <!-- ── Empty ─────────────────────────────────────────────── -->
    <div v-else-if="!streamGroups.length" class="streams-empty">
      <span class="empty-icon">◈</span>
      <p>{{ t('variableStreams.noStreams') }}</p>
      <UButton size="sm" variant="secondary" @click="searchTerm = ''; deviceUid = ''">
        {{ t('variableStreams.clearFilters') }}
      </UButton>
    </div>

    <!-- ── Grouped streams ───────────────────────────────────── -->
    <div v-else class="streams-groups">
      <div
        v-for="group in streamGroups"
        :key="group.id"
        class="stream-group"
      >
        <!-- Group header — click to expand/collapse -->
        <button
          class="group-header"
          :class="{ expanded: isGroupExpanded(group.id) }"
          @click="toggleGroup(group.id)"
        >
          <div class="group-left">
            <svg class="chevron" :class="{ rotated: isGroupExpanded(group.id) }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6" />
            </svg>
            <span v-if="group.isDevice" class="group-icon-device">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z" />
              </svg>
            </span>
            <span v-else class="group-icon-global">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
              </svg>
            </span>
            <span class="group-name">{{ group.label }}</span>
            <span class="group-count">{{ group.streams.length }}</span>
          </div>
          <div class="group-right">
            <UBadge
              v-if="group.device?.online"
              variant="success"
              size="sm"
            >{{ t('status.online') }}</UBadge>
            <UBadge
              v-else-if="group.device && !group.device.online"
              variant="danger"
              size="sm"
            >{{ t('status.offline') }}</UBadge>
          </div>
        </button>

        <!-- Expanded: stream rows -->
        <div v-if="isGroupExpanded(group.id)" class="group-body">
          <div class="stream-table-header">
            <span class="col-key">{{ t('variableStreams.colKey') }}</span>
            <span class="col-value">{{ t('variableStreams.colValue') }}</span>
            <span class="col-sparkline">{{ t('variableStreams.colTrend') }}</span>
            <span class="col-updated">{{ t('variableStreams.colUpdated') }}</span>
            <span class="col-type">{{ t('common.type') }}</span>
          </div>
          <button
            v-for="def in group.streams"
            :key="def.key"
            class="stream-row"
            @click="openDetail(def.key)"
            :title="def.description || def.key"
          >
            <span class="col-key">
              <code class="key-name">{{ def.key }}</code>
              <span v-if="def.unit" class="key-unit">({{ def.unit }})</span>
            </span>
            <span class="col-value">
              <code class="current-val">{{ formatValue(currentValues[def.key]) }}</code>
            </span>
            <span class="col-sparkline">
              <VizSparkline
                :points="historyData[def.key] ?? []"
                :label="def.key"
                :width="80"
                :height="24"
              />
            </span>
            <span class="col-updated">
              {{ lastUpdateText(def.key) }}
            </span>
            <span class="col-type">
              <span class="type-badge">{{ def.value_type }}</span>
            </span>
          </button>

          <div v-if="!group.streams.length" class="group-empty">
            {{ t('variableStreams.noStreamsInGroup') }}
          </div>
        </div>
      </div>
    </div>

    <!-- ── Detail overlay ────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="detailKey && detailDef" class="detail-overlay" @click.self="closeDetail">
        <div class="detail-panel">
          <div class="detail-header">
            <div class="detail-title-row">
              <code class="detail-key">{{ detailDef.key }}</code>
              <span v-if="detailDef.unit" class="detail-unit">{{ detailDef.unit }}</span>
              <span class="detail-scope">{{ detailDef.scope }}</span>
            </div>
            <div class="detail-actions">
              <div class="time-tabs">
                <button
                  v-for="tr in TIME_RANGES" :key="tr.value"
                  class="time-tab"
                  :class="{ active: timeRange === tr.value }"
                  @click="timeRange = tr.value; loadAllHistory(definitions)"
                >{{ tr.label }}</button>
              </div>
              <button class="detail-close" @click="closeDetail" :title="t('variableStreams.closeEsc')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
          </div>
          <div class="detail-body">
            <VizWidget
              :variableKey="detailDef.key"
              :label="detailDef.key"
              :unit="detailDef.unit ?? undefined"
              :valueType="detailDef.value_type"
              :displayHint="'line_chart'"
              :currentValue="currentValues[detailDef.key]"
              :points="historyData[detailDef.key] ?? []"
              :min="detailDef.min_value"
              :max="detailDef.max_value"
              :height="350"
              :showHeader="false"
              :timeRange="timeRange"
            />
          </div>
          <div v-if="detailDef.description || detailDef.category" class="detail-footer">
            <span v-if="detailDef.description" class="detail-desc">{{ detailDef.description }}</span>
            <span v-if="detailDef.category" class="detail-cat">{{ detailDef.category }}</span>
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

/* ── Header ───────────────────────────────────────────────── */
.streams-header {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 16px;
  flex-wrap: wrap;
}
.header-left { display: flex; flex-direction: column; gap: 4px; }
.header-title-row { display: flex; align-items: center; gap: 10px; }
.streams-icon { font-size: 20px; color: #58a6ff; }
.streams-title { font-size: 20px; font-weight: 600; color: #e6edf3; margin: 0; }
.streams-desc { font-size: 13px; color: #8b949e; margin: 0; max-width: 520px; line-height: 1.5; }
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

/* ── Filters ──────────────────────────────────────────────── */
.streams-filters {
  display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
}
.filter-device-wrap { width: 240px; }
.filter-search {
  flex: 1; min-width: 160px;
  padding: 7px 12px; font-size: 13px;
  background: #0d1117; border: 1px solid #30363d; border-radius: 6px;
  color: #e6edf3; outline: none;
  transition: border-color 0.15s;
}
.filter-search:focus { border-color: #58a6ff; }
.filter-search::placeholder { color: #484f58; }
.stream-count {
  font-size: 12px; color: #8b949e; white-space: nowrap;
}

/* ── Error ───────────────────────────────────────────────── */
.streams-error {
  background: #3d1f1f; border: 1px solid #6e2020;
  border-radius: 6px; color: #f85149; font-size: 13px; padding: 10px 14px;
}

/* ── Loading ─────────────────────────────────────────────── */
.streams-loading {
  display: flex; flex-direction: column; gap: 12px;
}
.skeleton-group {
  display: flex; flex-direction: column; gap: 4px;
}
.skeleton-header {
  height: 44px;
  background: linear-gradient(90deg, #21262d 25%, #30363d 50%, #21262d 75%);
  background-size: 200% 100%;
  border-radius: 6px; border: 1px solid #30363d;
  animation: shimmer 1.4s infinite;
}
.skeleton-row {
  height: 36px; margin-left: 16px;
  background: linear-gradient(90deg, #161b22 25%, #21262d 50%, #161b22 75%);
  background-size: 200% 100%;
  border-radius: 4px;
  animation: shimmer 1.4s infinite;
}
@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }

/* ── Empty ───────────────────────────────────────────────── */
.streams-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; padding: 80px; color: #8b949e; font-size: 14px; text-align: center;
}
.empty-icon { font-size: 32px; color: #30363d; }

/* ── Groups ──────────────────────────────────────────────── */
.streams-groups {
  display: flex; flex-direction: column; gap: 8px;
}

.stream-group {
  border: 1px solid #21262d; border-radius: 8px;
  overflow: hidden; background: #0d1117;
}

/* ── Group header ────────────────────────────────────────── */
.group-header {
  display: flex; align-items: center; justify-content: space-between;
  width: 100%; padding: 10px 14px; gap: 12px;
  background: #161b22; border: none; cursor: pointer;
  transition: background 0.1s;
}
.group-header:hover { background: #1c2128; }
.group-header.expanded { border-bottom: 1px solid #21262d; }
.group-left { display: flex; align-items: center; gap: 8px; }
.group-right { display: flex; align-items: center; gap: 8px; }

.chevron {
  color: #484f58; transition: transform 0.15s;
  flex-shrink: 0;
}
.chevron.rotated { transform: rotate(90deg); }

.group-icon-device,
.group-icon-global {
  color: #8b949e; display: flex; align-items: center;
}
.group-icon-device { color: #58a6ff; }
.group-icon-global { color: #2dd4bf; }

.group-name {
  font-size: 13px; font-weight: 600; color: #e6edf3;
}
.group-count {
  font-size: 11px; color: #8b949e; background: #21262d;
  padding: 1px 7px; border-radius: 10px;
}

/* ── Group body (expanded) ───────────────────────────────── */
.group-body {
  animation: fadeIn 0.15s ease;
}
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

.stream-table-header {
  display: grid;
  grid-template-columns: 2fr 1.2fr 100px 70px 70px;
  gap: 8px; padding: 6px 14px;
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em;
  color: #484f58; border-bottom: 1px solid #21262d;
  user-select: none;
}

/* ── Stream row ──────────────────────────────────────────── */
.stream-row {
  display: grid;
  grid-template-columns: 2fr 1.2fr 100px 70px 70px;
  gap: 8px; padding: 8px 14px;
  align-items: center;
  border: none; background: transparent; cursor: pointer;
  width: 100%; text-align: left;
  border-bottom: 1px solid #161b2200;
  transition: background 0.1s, border-color 0.1s;
}
.stream-row:hover {
  background: #161b22;
  border-bottom-color: #21262d;
}
.stream-row:last-child { border-bottom: none; }

.col-key {
  display: flex; align-items: center; gap: 6px; min-width: 0;
}
.key-name {
  font-size: 12px; color: #c9d1d9; font-family: 'IBM Plex Mono', monospace;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.key-unit { font-size: 11px; color: #484f58; flex-shrink: 0; }

.col-value { min-width: 0; }
.current-val {
  font-size: 12px; color: #e6edf3; font-family: 'IBM Plex Mono', monospace;
  font-weight: 500;
}

.col-sparkline { display: flex; align-items: center; }

.col-updated {
  font-size: 11px; color: #8b949e; text-align: right;
}

.col-type { display: flex; align-items: center; }
.type-badge {
  font-size: 10px; color: #8b949e; background: #21262d;
  padding: 2px 6px; border-radius: 3px;
  font-family: 'IBM Plex Mono', monospace;
}

.group-empty {
  padding: 20px 14px; text-align: center;
  font-size: 13px; color: #484f58;
}

/* ── Detail overlay ──────────────────────────────────────── */
.detail-overlay {
  position: fixed; inset: 0; z-index: 9999;
  background: rgba(0,0,0,0.85);
  backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
  padding: 24px;
}
.detail-panel {
  background: #161b22; border: 1px solid #30363d;
  border-radius: 10px; width: 100%; max-width: 900px;
  overflow: hidden; display: flex; flex-direction: column;
  max-height: calc(100vh - 48px);
}
.detail-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 20px 12px; border-bottom: 1px solid #21262d;
  flex-wrap: wrap; gap: 8px;
}
.detail-title-row {
  display: flex; align-items: center; gap: 8px;
}
.detail-key {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 16px; font-weight: 600; color: #e6edf3;
}
.detail-unit { font-size: 13px; color: #8b949e; }
.detail-scope {
  font-size: 10px; color: #58a6ff; background: #58a6ff11;
  padding: 2px 8px; border-radius: 10px; text-transform: uppercase;
}
.detail-actions { display: flex; align-items: center; gap: 10px; }
.detail-close {
  width: 28px; height: 28px; border-radius: 4px;
  background: #21262d; border: 1px solid #30363d;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  color: #8b949e;
}
.detail-close:hover { color: #f85149; }
.detail-body { padding: 16px 20px; flex: 1; overflow: auto; }
.detail-footer {
  padding: 10px 20px; border-top: 1px solid #21262d;
  display: flex; gap: 10px; align-items: center;
  font-size: 12px;
}
.detail-desc { color: #8b949e; }
.detail-cat {
  color: #58a6ff; background: #58a6ff11;
  padding: 2px 8px; border-radius: 10px;
  font-size: 10px;
}

/* ── Responsive ──────────────────────────────────────────── */
@media (max-width: 768px) {
  .stream-table-header { display: none; }
  .stream-row {
    grid-template-columns: 1fr auto;
    grid-template-rows: auto auto;
    gap: 4px;
  }
  .col-sparkline,
  .col-type { display: none; }
  .col-updated { grid-column: 2; grid-row: 1; }
  .col-value { grid-column: 1 / -1; grid-row: 2; }
  .filter-device-wrap { width: 100%; }
  .header-right { flex-direction: column; align-items: flex-start; }
}
</style>
