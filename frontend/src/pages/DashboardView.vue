<template>
  <div class="db-view">

    <!-- Top bar -->
    <div class="db-topbar">
      <div class="db-topbar-left">
        <button v-if="!isKiosk" class="back-btn" @click="router.push('/dashboards')">← {{ t('nav.dashboards') }}</button>
        <h1 v-if="dashboard" class="db-name">{{ dashboard.name }}</h1>
        <USkeleton v-else class="h-5 w-40" />
      </div>
      <div class="db-topbar-right">
        <div class="time-btns">
          <button
            v-for="r in TIME_RANGES"
            :key="r"
            class="tr-btn"
            :class="{ active: currentRange === r }"
            @click="currentRange = r"
          >{{ r }}</button>
        </div>
        <button v-if="!isKiosk" class="edit-btn" :class="{ active: editMode }" @click="editMode = !editMode">
          {{ editMode ? '✓ Done' : '✏ Edit' }}
        </button>
        <button class="refresh-btn" @click="loadDashboard" :title="t('common.refresh')">↺</button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="db-grid loading-grid">
      <div v-for="i in 6" :key="i" class="grid-skel" :style="{ gridColumn: `span 4`, gridRow: 'span 3' }">
        <USkeleton class="h-full w-full rounded-lg" />
      </div>
    </div>

    <!-- Empty dashboard -->
    <div v-else-if="dashboard && !dashboard.widgets.length" class="db-empty">
      <div class="empty-icon">📊</div>
      <p class="empty-title">No widgets yet</p>
      <p class="empty-sub">Click "Edit" to add widgets to this dashboard</p>
      <UButton @click="editMode = true; openAddWidget()">Add Widget</UButton>
    </div>

    <!-- Dashboard grid -->
    <div v-else-if="dashboard" class="db-grid">
      <div
        v-for="widget in sortedWidgets"
        :key="widget.id"
        class="db-widget-cell"
        :style="{
          gridColumn: `${widget.grid_col} / span ${widget.grid_span_w}`,
          gridRow: `${widget.grid_row} / span ${widget.grid_span_h}`,
        }"
      >
        <!-- Edit mode overlay -->
        <div v-if="editMode" class="widget-edit-overlay">
          <button class="overlay-btn move" @click="moveWidget(widget, -1)" title="Move left/up">◀</button>
          <button class="overlay-btn cfg" @click="openWidgetConfig(widget)" title="Configure">⚙</button>
          <button class="overlay-btn del" @click="confirmDeleteWidget(widget)" title="Remove widget">✕</button>
          <button class="overlay-btn move" @click="moveWidget(widget, 1)" title="Move right/down">▶</button>
        </div>

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
          :writable="isWritable(widget)"
          @range-change="(r) => { currentRange = r; reloadWidgetHistory(widget) }"
          @control-change="(v) => handleControlChange(widget, v)"
        />
      </div>

      <!-- Add widget placeholder (edit mode) -->
      <div v-if="editMode" class="add-widget-cell" @click="openAddWidget()">
        <span class="add-icon">＋</span>
        <span>Add Widget</span>
      </div>
    </div>

    <!-- Add Widget Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showAddWidget" class="modal-overlay" @click.self="showAddWidget = false">
          <div class="modal-box">
            <h2 class="modal-title">{{ editingWidgetId ? 'Edit Widget' : 'Add Widget' }}</h2>
            <div class="form-fields">

              <!-- Widget type -->
              <div class="field">
                <label class="field-label">Widget Type</label>
                <select v-model="newWidget.widget_type" class="field-input">
                  <optgroup label="Visualizations">
                    <option value="line_chart">Line Chart</option>
                    <option value="gauge">Gauge</option>
                    <option value="sparkline">Sparkline</option>
                    <option value="bool">Status / Bool</option>
                    <option value="log">Log</option>
                    <option value="json">JSON Viewer</option>
                    <option value="map">Map (GPS)</option>
                  </optgroup>
                  <optgroup label="Controls">
                    <option value="control_toggle">Toggle Switch</option>
                    <option value="control_slider">Slider</option>
                  </optgroup>
                </select>
              </div>

              <!-- Device first, then variable (filtered by device) -->
              <div class="field">
                <UEntitySelect v-model="newWidget.device_uid" entity-type="device" label="1. Select Device" placeholder="Choose device first..." :optional="true" />
              </div>

              <div class="field">
                <UEntitySelect v-model="newWidget.variable_key" entity-type="variable" label="2. Select Variable" :placeholder="newWidget.device_uid ? 'Variables for this device...' : 'Select device first or choose global...'" />
              </div>

              <!-- Label -->
              <div class="field">
                <label class="field-label">Label</label>
                <input v-model="newWidget.label" class="field-input" placeholder="Display label" />
              </div>

              <!-- Unit (numeric widgets) -->
              <div v-if="isNumericType(newWidget.widget_type)" class="field-row-3">
                <div class="field">
                  <label class="field-label">Unit</label>
                  <input v-model="newWidget.unit" class="field-input" placeholder="°C" />
                </div>
                <div class="field">
                  <label class="field-label">Min</label>
                  <input v-model.number="newWidget.min_value" type="number" class="field-input" placeholder="0" />
                </div>
                <div class="field">
                  <label class="field-label">Max</label>
                  <input v-model.number="newWidget.max_value" type="number" class="field-input" placeholder="100" />
                </div>
              </div>

              <!-- Grid size -->
              <div class="field-row-2">
                <div class="field">
                  <label class="field-label">Width (cols)</label>
                  <select v-model.number="newWidget.grid_span_w" class="field-input">
                    <option v-for="n in [2,3,4,5,6,8,10,12]" :key="n" :value="n">{{ n }}</option>
                  </select>
                </div>
                <div class="field">
                  <label class="field-label">Height (rows)</label>
                  <select v-model.number="newWidget.grid_span_h" class="field-input">
                    <option v-for="n in [2,3,4,5,6]" :key="n" :value="n">{{ n }}</option>
                  </select>
                </div>
              </div>

              <p v-if="addError" class="field-error">{{ addError }}</p>

              <div class="modal-actions">
                <UButton variant="ghost" @click="showAddWidget = false">{{ t('common.cancel') }}</UButton>
                <UButton :loading="adding" @click="submitAddWidget">{{ editingWidgetId ? 'Save Changes' : 'Add Widget' }}</UButton>
              </div>

            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Delete widget confirm -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="deletingWidget" class="modal-overlay" @click.self="deletingWidget = null">
          <div class="modal-box modal-small">
            <h2 class="modal-title">Remove Widget?</h2>
            <p class="modal-sub">Remove "{{ deletingWidget.label || deletingWidget.variable_key || 'this widget' }}" from the dashboard?</p>
            <div class="modal-actions">
              <UButton variant="ghost" @click="deletingWidget = null">{{ t('common.cancel') }}</UButton>
              <UButton color="red" :loading="deleting" @click="submitDeleteWidget">Remove</UButton>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { parseApiError, mapErrorToUserText } from "../lib/errors";
import UButton from "../components/ui/UButton.vue";
import USkeleton from "../components/ui/USkeleton.vue";
import VizWidget from "../components/viz/VizWidget.vue";
import {
  getDashboard,
  addWidget,
  updateWidget,
  deleteWidget,
  updateLayout,
  type Dashboard,
  type DashboardWidget,
} from "../lib/dashboards";
import { getVariableHistory } from "../lib/variables";
import type { VizDataPoint } from "../lib/viz-types";
import type { TimeRange } from "../composables/useVariableHistory";
import { apiFetch } from "../lib/api";
import UEntitySelect from "../components/ui/UEntitySelect.vue";

function rangeToFrom(range: TimeRange): number {
  const now = Math.floor(Date.now() / 1000);
  const map: Record<TimeRange, number> = {
    "1h":  now - 3600,
    "6h":  now - 21600,
    "24h": now - 86400,
    "7d":  now - 604800,
    "30d": now - 2592000,
  };
  return map[range] ?? now - 3600;
}

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const isKiosk = computed(() => route.meta?.layout === "kiosk");

const dashboard = ref<Dashboard | null>(null);
const loading = ref(true);
const editMode = ref(false);
const currentRange = ref<TimeRange>("1h");
const TIME_RANGES: TimeRange[] = ["1h", "6h", "24h", "7d", "30d"];

// History data per widget
const historyData = ref<Record<number, VizDataPoint[]>>({});
const historyLoading = ref<Record<number, boolean>>({});
const currentValues = ref<Record<number, unknown>>({});

// Add widget form
const showAddWidget = ref(false);
const adding = ref(false);
const addError = ref("");
const newWidget = ref(defaultNewWidget());
const editingWidgetId = ref<number | null>(null);  // null = add mode, number = edit mode

// Delete widget
const deletingWidget = ref<DashboardWidget | null>(null);
const deleting = ref(false);

function defaultNewWidget() {
  return {
    widget_type: "line_chart" as string,
    variable_key: "",
    device_uid: "",
    label: "",
    unit: "",
    min_value: null as number | null,
    max_value: null as number | null,
    grid_span_w: 4,
    grid_span_h: 3,
  };
}

onMounted(loadDashboard);

watch(currentRange, () => {
  if (dashboard.value) loadAllHistory();
});

// Auto-suggest widget type + label when variable is selected
watch(() => newWidget.value.variable_key, async (varKey) => {
  if (!varKey) return;
  try {
    const defs = await apiFetch<Array<{ key: string; value_type: string; display_hint?: string; unit?: string; description?: string }>>("/api/v1/variables/definitions");
    const def = defs.find((d: { key: string }) => d.key === varKey);
    if (def) {
      // Auto-fill label from key
      if (!newWidget.value.label) newWidget.value.label = def.description || def.key;
      // Auto-fill unit
      if (!newWidget.value.unit && def.unit) newWidget.value.unit = def.unit;
      // Auto-suggest widget type based on display_hint or value_type
      const hint = def.display_hint;
      if (hint && hint !== "auto") {
        newWidget.value.widget_type = hint;
      } else {
        const typeMap: Record<string, string> = {
          int: "gauge", float: "line_chart", bool: "bool", string: "log", json: "json",
        };
        newWidget.value.widget_type = typeMap[def.value_type] ?? "line_chart";
      }
    }
  } catch { /* ignore — auto-suggest is best-effort */ }
});

async function loadDashboard() {
  loading.value = true;
  try {
    const id = Number(route.params.id);
    dashboard.value = await getDashboard(id);
    await loadAllHistory();
  } catch {
    dashboard.value = null;
  } finally {
    loading.value = false;
  }
}

const sortedWidgets = computed<DashboardWidget[]>(() => {
  if (!dashboard.value) return [];
  return [...dashboard.value.widgets].sort((a, b) => a.sort_order - b.sort_order);
});

function moveWidget(widget: DashboardWidget, direction: number) {
  if (!dashboard.value) return;
  const widgets = dashboard.value.widgets;
  const sorted = [...widgets].sort((a, b) => a.sort_order - b.sort_order);
  const idx = sorted.findIndex(w => w.id === widget.id);
  const newIdx = idx + direction;
  if (newIdx < 0 || newIdx >= sorted.length) return;
  // Swap sort_order
  const tmp = sorted[idx].sort_order;
  sorted[idx].sort_order = sorted[newIdx].sort_order;
  sorted[newIdx].sort_order = tmp;
  // Recalculate grid positions
  recalcGridPositions(sorted);
  dashboard.value.widgets = sorted;
  // Persist to backend
  saveLayout();
}

async function saveLayout() {
  if (!dashboard.value) return;
  try {
    const items = dashboard.value.widgets.map(w => ({
      widget_id: w.id,
      sort_order: w.sort_order,
      grid_col: w.grid_col,
      grid_row: w.grid_row,
      grid_span_w: w.grid_span_w,
      grid_span_h: w.grid_span_h,
    }));
    await updateLayout(dashboard.value.id, items);
  } catch { /* silent — layout will reload on next page visit */ }
}

async function loadAllHistory() {
  if (!dashboard.value) return;
  for (const w of dashboard.value.widgets) {
    if (w.variable_key) {
      loadWidgetHistory(w);
    }
  }
}

async function loadWidgetHistory(widget: DashboardWidget) {
  if (!widget.variable_key) return;
  historyLoading.value[widget.id] = true;
  try {
    const scope = widget.device_uid ? "device" : "global";
    const resp = await getVariableHistory({
      key: widget.variable_key,
      scope,
      deviceUid: widget.device_uid || null,
      from: rangeToFrom(currentRange.value),
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

async function reloadWidgetHistory(widget: DashboardWidget) {
  await loadWidgetHistory(widget);
}

function widgetPoints(widget: DashboardWidget): VizDataPoint[] {
  return historyData.value[widget.id] ?? [];
}

function widgetCurrentValue(widget: DashboardWidget): unknown {
  return currentValues.value[widget.id] ?? null;
}

function widgetValueType(widget: DashboardWidget): "string" | "int" | "float" | "bool" | "json" {
  const cfg = widget.display_config as Record<string, string> | null;
  if (cfg?.value_type) return cfg.value_type as "string" | "int" | "float" | "bool" | "json";
  if (["bool", "control_toggle"].includes(widget.widget_type)) return "bool";
  if (["gauge", "sparkline", "line_chart", "control_slider"].includes(widget.widget_type)) return "float";
  if (["map", "json"].includes(widget.widget_type)) return "json";
  return "string";
}

function widgetBodyHeight(widget: DashboardWidget): number {
  return Math.max(120, widget.grid_span_h * 40);
}

function isWritable(widget: DashboardWidget): boolean {
  return ["control_toggle", "control_slider"].includes(widget.widget_type);
}

function isNumericType(type: string): boolean {
  return ["gauge", "sparkline", "line_chart", "control_slider"].includes(type);
}

async function handleControlChange(widget: DashboardWidget, value: unknown) {
  if (!widget.variable_key) return;
  try {
    await apiFetch(`/api/v1/variables/values`, {
      method: "POST",
      body: JSON.stringify({
        key: widget.variable_key,
        scope: widget.device_uid ? "device" : "global",
        device_uid: widget.device_uid || null,
        value,
      }),
    });
    currentValues.value[widget.id] = value;
  } catch (e) {
    console.error("Failed to write variable", e);
  }
}

// Add or update widget
async function submitAddWidget() {
  adding.value = true;
  addError.value = "";
  try {
    const dashId = Number(route.params.id);

    if (editingWidgetId.value) {
      // UPDATE existing widget
      const w = await updateWidget(dashId, editingWidgetId.value, {
        widget_type: newWidget.value.widget_type,
        variable_key: newWidget.value.variable_key || null,
        device_uid: newWidget.value.device_uid || null,
        label: newWidget.value.label || null,
        unit: newWidget.value.unit || null,
        min_value: newWidget.value.min_value,
        max_value: newWidget.value.max_value,
        grid_span_w: newWidget.value.grid_span_w,
        grid_span_h: newWidget.value.grid_span_h,
      });
      const idx = dashboard.value!.widgets.findIndex((x) => x.id === editingWidgetId.value);
      if (idx >= 0) dashboard.value!.widgets[idx] = w;
      if (w.variable_key) loadWidgetHistory(w);
    } else {
      // ADD new widget
      const nextPos = getNextGridPosition();
      const w = await addWidget(dashId, {
        widget_type: newWidget.value.widget_type,
        variable_key: newWidget.value.variable_key || null,
        device_uid: newWidget.value.device_uid || null,
        label: newWidget.value.label || null,
        unit: newWidget.value.unit || null,
        min_value: newWidget.value.min_value,
        max_value: newWidget.value.max_value,
        grid_col: nextPos.col,
        grid_row: nextPos.row,
        grid_span_w: newWidget.value.grid_span_w,
        grid_span_h: newWidget.value.grid_span_h,
      });
      dashboard.value!.widgets.push(w);
      if (w.variable_key) loadWidgetHistory(w);
    }

    showAddWidget.value = false;
    editingWidgetId.value = null;
    newWidget.value = defaultNewWidget();
  } catch (e: unknown) {
    const info = parseApiError(e);
    addError.value = mapErrorToUserText(info, "Widget could not be saved.");
  } finally {
    adding.value = false;
  }
}

function recalcGridPositions(sorted: DashboardWidget[]) {
  // Pack widgets into 12-column grid, flowing left-to-right then top-to-bottom
  let col = 1;
  let row = 1;
  let rowHeight = 0;
  for (const w of sorted) {
    if (col + w.grid_span_w - 1 > 12) {
      // Doesn't fit on current row → next row
      col = 1;
      row += rowHeight;
      rowHeight = 0;
    }
    w.grid_col = col;
    w.grid_row = row;
    col += w.grid_span_w;
    rowHeight = Math.max(rowHeight, w.grid_span_h);
  }
}

function getNextGridPosition(): { col: number; row: number } {
  if (!dashboard.value?.widgets.length) return { col: 1, row: 1 };
  const sorted = [...dashboard.value.widgets].sort((a, b) => a.sort_order - b.sort_order);
  // Find first position that fits a 4-wide widget
  let col = 1;
  let row = 1;
  let rowHeight = 0;
  for (const w of sorted) {
    if (col + w.grid_span_w - 1 > 12) {
      col = 1;
      row += rowHeight;
      rowHeight = 0;
    }
    col += w.grid_span_w;
    rowHeight = Math.max(rowHeight, w.grid_span_h);
  }
  if (col + 4 - 1 > 12) {
    col = 1;
    row += rowHeight;
  }
  return { col, row };
}

function confirmDeleteWidget(widget: DashboardWidget) {
  deletingWidget.value = widget;
}

async function submitDeleteWidget() {
  if (!deletingWidget.value || !dashboard.value) return;
  deleting.value = true;
  try {
    await deleteWidget(dashboard.value.id, deletingWidget.value.id);
    dashboard.value.widgets = dashboard.value.widgets.filter((w) => w.id !== deletingWidget.value!.id);
    deletingWidget.value = null;
  } catch (e: unknown) {
    addError.value = "Failed to remove widget";
  } finally {
    deleting.value = false;
  }
}

function openWidgetConfig(widget: DashboardWidget) {
  editingWidgetId.value = widget.id;
  newWidget.value = {
    widget_type: widget.widget_type,
    variable_key: widget.variable_key || "",
    device_uid: widget.device_uid || "",
    label: widget.label || "",
    unit: widget.unit || "",
    min_value: widget.min_value,
    max_value: widget.max_value,
    grid_span_w: widget.grid_span_w,
    grid_span_h: widget.grid_span_h,
  };
  showAddWidget.value = true;
}

function openAddWidget() {
  editingWidgetId.value = null;
  newWidget.value = defaultNewWidget();
  showAddWidget.value = true;
}
</script>

<style scoped>
.db-view { display: flex; flex-direction: column; height: 100%; overflow: hidden; }

/* ── Top bar ───────────────────────────────────────────── */
.db-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-surface);
  flex-shrink: 0;
  gap: 12px;
  flex-wrap: wrap;
}
.db-topbar-left { display: flex; align-items: center; gap: 12px; }
.back-btn {
  font-size: 12px;
  color: var(--text-muted);
  background: none; border: none; cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: color 0.15s, background 0.15s;
}
.back-btn:hover { color: var(--text-base); background: var(--bg-elevated); }
.db-name { font-size: 16px; font-weight: 600; color: var(--text-base); }

.db-topbar-right { display: flex; align-items: center; gap: 8px; }

.time-btns {
  display: flex;
  gap: 1px;
  background: var(--bg-elevated);
  border-radius: 5px;
  padding: 2px;
}
.tr-btn {
  padding: 3px 8px; font-size: 11px;
  background: none; border: none; cursor: pointer;
  color: var(--text-muted); border-radius: 4px;
  transition: background 0.1s, color 0.1s;
}
.tr-btn:hover { background: var(--border); color: var(--text-base); }
.tr-btn.active { background: var(--border); color: var(--primary); }

.edit-btn {
  padding: 5px 12px;
  font-size: 12px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s;
}
.edit-btn:hover, .edit-btn.active {
  border-color: var(--primary);
  color: var(--primary);
  background: color-mix(in srgb, var(--primary) 10%, transparent);
}
.refresh-btn {
  padding: 5px 10px;
  font-size: 14px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text-muted);
  cursor: pointer;
  transition: color 0.15s;
}
.refresh-btn:hover { color: var(--text-base); }

/* ── Grid ──────────────────────────────────────────────── */
.db-grid {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: 60px;
  gap: 8px;
  padding: 16px;
  align-content: start;
}
.loading-grid { align-items: start; }

.db-widget-cell {
  position: relative;
  min-height: 0;
}
.db-widget-cell > .viz-widget,
.db-widget-cell > * {
  height: 100%;
}

/* Edit overlay */
.widget-edit-overlay {
  position: absolute;
  top: 6px;
  right: 6px;
  z-index: 10;
  display: flex;
  gap: 4px;
}
.overlay-btn {
  width: 24px; height: 24px;
  border-radius: 4px;
  border: 1px solid var(--border);
  background: var(--bg-surface);
  color: var(--text-muted);
  font-size: 12px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
.overlay-btn.del:hover { background: var(--status-bad); color: #fff; border-color: var(--status-bad); }
.overlay-btn.cfg:hover { background: var(--primary); color: #000; border-color: var(--primary); }
.overlay-btn.move:hover { background: var(--bg-raised); color: var(--text-primary); }

/* Add widget placeholder */
.add-widget-cell {
  grid-column: span 3;
  grid-row: span 2;
  border: 2px dashed var(--border);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: var(--text-muted);
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.add-widget-cell:hover { border-color: var(--primary); color: var(--primary); }
.add-icon { font-size: 22px; }

/* Empty state */
.db-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px;
  text-align: center;
}
.empty-icon { font-size: 40px; }
.empty-title { font-size: 18px; font-weight: 600; color: var(--text-base); }
.empty-sub { font-size: 13px; color: var(--text-muted); margin-bottom: 8px; }

/* Grid skeleton */
.grid-skel { min-height: 120px; }

/* ── Modal (reused) ────────────────────────────────────── */
.modal-overlay {
  position: fixed; inset: 0; z-index: 100;
  background: rgba(0,0,0,0.7); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
}
.modal-box {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  width: min(480px, calc(100vw - 32px));
  max-height: 85vh;
  overflow-y: auto;
}
.modal-small { width: min(340px, calc(100vw - 32px)); }
.modal-title { font-size: 17px; font-weight: 700; color: var(--text-base); margin-bottom: 16px; }
.modal-sub { font-size: 13px; color: var(--text-muted); margin-bottom: 16px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }
.form-fields { display: flex; flex-direction: column; gap: 12px; }
.field { display: flex; flex-direction: column; gap: 4px; }
.field-label { font-size: 12px; color: var(--text-muted); }
.field-opt { opacity: 0.6; }
.field-input {
  background: var(--bg-base);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 7px 10px;
  color: var(--text-base);
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}
.field-input:focus { border-color: var(--primary); }
.field-row-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
.field-row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.field-error { font-size: 12px; color: var(--status-bad); }

.modal-enter-active, .modal-leave-active { transition: opacity 0.2s, transform 0.2s; }
.modal-enter-from, .modal-leave-to { opacity: 0; transform: scale(0.97); }
</style>
