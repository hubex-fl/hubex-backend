<template>
  <div class="db-view">

    <!-- Top bar -->
    <div class="db-topbar">
      <div class="db-topbar-left">
        <button v-if="!isKiosk" class="back-btn" @click="router.push('/dashboards')">&#8592; {{ t('nav.dashboards') }}</button>
        <template v-if="dashboard">
          <template v-if="editingName">
            <input
              ref="nameInputRef"
              v-model="editNameValue"
              class="db-name-input"
              @blur="saveDashboardName"
              @keydown.enter="saveDashboardName"
              @keydown.escape="editingName = false"
            />
          </template>
          <h1 v-else class="db-name" :class="{ 'db-name-editable': editMode }" @click="editMode && startEditName()">
            {{ dashboard.name }}
          </h1>
        </template>
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
        <button v-if="!isKiosk" class="share-btn" @click="showSharePanel = !showSharePanel" :title="t('dashboardEnhance.share')">
          &#128279;
        </button>
        <button v-if="!isKiosk" class="settings-btn" @click="showSettingsPanel = !showSettingsPanel" :title="t('dashboardEnhance.settingsTitle')">
          &#9881;
        </button>
        <button v-if="!isKiosk" class="edit-btn" :class="{ active: editMode }" @click="editMode = !editMode">
          {{ editMode ? '&#10003; ' + t('dashboardEnhance.doneMode') : '&#9998; ' + t('dashboardEnhance.editMode') }}
        </button>
        <button class="refresh-btn" @click="loadDashboard" :title="t('common.refresh')">&#8634;</button>
      </div>
    </div>

    <!-- Share Panel -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showSharePanel" class="modal-overlay" @click.self="showSharePanel = false">
          <div class="modal-box modal-small">
            <h2 class="modal-title">{{ t('dashboardEnhance.shareDashboard') }}</h2>
            <div class="form-fields">
              <!-- Share tabs: Private / Public / Embed -->
              <div class="share-modes">
                <button
                  v-for="tab in (['private', 'public', 'embed'] as const)"
                  :key="tab"
                  class="share-mode-btn"
                  :class="{ active: shareTab === tab }"
                  @click="switchShareTab(tab)"
                >
                  {{ tab === 'private' ? t('dashboardEnhance.private') : tab === 'public' ? t('dashboardEnhance.public') : t('dashboardEnhance.embed') }}
                </button>
              </div>

              <!-- Private tab -->
              <template v-if="shareTab === 'private'">
                <p class="share-info">{{ t('dashboardEnhance.privateDesc') }}</p>
              </template>

              <!-- Public tab -->
              <template v-if="shareTab === 'public'">
                <div class="field">
                  <label class="field-label">{{ t('dashboardEnhance.publicUrl') }}</label>
                  <div class="share-url-row">
                    <input readonly :value="shareUrl" class="field-input share-url-input" />
                    <button class="copy-btn" @click="copyShareUrl" :title="copied ? t('dashboardEnhance.copied') : t('dashboardEnhance.copy')">
                      {{ copied ? '&#10003;' : '&#128203;' }}
                    </button>
                  </div>
                </div>

                <div class="field">
                  <label class="share-pin-label">
                    <input type="checkbox" v-model="pinEnabled" @change="handlePinToggle" />
                    {{ t('dashboardEnhance.pinProtected') }}
                  </label>
                  <input
                    v-if="pinEnabled"
                    v-model="pinValue"
                    class="field-input"
                    :placeholder="t('dashboardEnhance.pinPlaceholder')"
                    maxlength="6"
                    @blur="savePin"
                    @keydown.enter="savePin"
                  />
                </div>
              </template>

              <!-- Embed tab -->
              <template v-if="shareTab === 'embed'">
                <template v-if="shareMode === 'private'">
                  <p class="share-info">{{ t('dashboardEnhance.embedRequiresPublic') }}</p>
                </template>
                <template v-else>
                  <div class="field">
                    <label class="field-label">{{ t('dashboardEnhance.iframeSnippet') }}</label>
                    <div class="share-url-row">
                      <input readonly :value="embedSnippet" class="field-input share-url-input" />
                      <button class="copy-btn" @click="copyEmbedSnippet" :title="embedCopied ? t('dashboardEnhance.copied') : t('dashboardEnhance.copy')">
                        {{ embedCopied ? '&#10003;' : '&#128203;' }}
                      </button>
                    </div>
                  </div>
                  <div class="field">
                    <label class="field-label">{{ t('dashboardEnhance.allowedReferers') }}</label>
                    <input v-model="embedReferers" class="field-input" :placeholder="t('dashboardEnhance.allowedReferersPlaceholder')" @blur="saveEmbedConfig" />
                  </div>
                  <div class="field">
                    <label class="field-label">{{ t('dashboardEnhance.expiresAt') }}</label>
                    <input v-model="embedExpiresAt" type="date" class="field-input" @change="saveEmbedConfig" />
                  </div>
                </template>
              </template>

              <div class="modal-actions">
                <UButton variant="ghost" @click="showSharePanel = false">{{ t('common.close') }}</UButton>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Settings Panel -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showSettingsPanel" class="modal-overlay" @click.self="showSettingsPanel = false">
          <div class="modal-box modal-small">
            <h2 class="modal-title">{{ t('dashboardEnhance.dashboardSettings') }}</h2>
            <div class="form-fields">
              <div class="field">
                <label class="field-label">{{ t('dashboardEnhance.name') }}</label>
                <input v-model="settingsName" class="field-input" />
              </div>
              <div class="field">
                <label class="field-label">{{ t('dashboardEnhance.description') }}</label>
                <input v-model="settingsDescription" class="field-input" :placeholder="t('dashboardEnhance.optionalDescription')" />
              </div>
              <div class="field">
                <label class="share-pin-label">
                  <input type="checkbox" v-model="settingsIsDefault" />
                  {{ t('dashboardEnhance.setAsDefault') }}
                </label>
              </div>

              <!-- Kiosk Slideshow Section -->
              <div class="settings-section">
                <h3 class="settings-section-title">{{ t('dashboardEnhance.kioskSlideshow') }}</h3>
                <div class="field">
                  <label class="field-label">{{ t('dashboardEnhance.slideshowInterval') }}</label>
                  <select v-model.number="kioskInterval" class="field-input">
                    <option :value="5">5s</option>
                    <option :value="10">10s</option>
                    <option :value="15">15s</option>
                    <option :value="30">30s</option>
                    <option :value="60">60s</option>
                    <option :value="120">120s</option>
                  </select>
                </div>
                <div class="field">
                  <label class="share-pin-label">
                    <input type="checkbox" v-model="kioskShowHeader" />
                    {{ t('dashboardEnhance.showHeader') }}
                  </label>
                </div>
                <div class="field">
                  <label class="share-pin-label">
                    <input type="checkbox" v-model="kioskShowClock" />
                    {{ t('dashboardEnhance.showClock') }}
                  </label>
                </div>
                <UButton variant="ghost" size="sm" @click="openKioskSlideshow">
                  {{ t('dashboardEnhance.launchKiosk') }}
                </UButton>
              </div>

              <div class="modal-actions">
                <button class="delete-db-btn" @click="confirmDeleteDashboard">{{ t('dashboardEnhance.deleteDashboard') }}</button>
                <UButton variant="ghost" @click="showSettingsPanel = false">{{ t('common.cancel') }}</UButton>
                <UButton :loading="savingSettings" @click="saveSettings">{{ t('common.save') }}</UButton>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Delete Dashboard Confirm -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showDeleteDashboard" class="modal-overlay" @click.self="showDeleteDashboard = false">
          <div class="modal-box modal-small">
            <h2 class="modal-title">{{ t('dashboardEnhance.deleteDashboardConfirm') }}</h2>
            <p class="modal-sub">{{ t('dashboardEnhance.deleteDashboardMessage', { name: dashboard?.name }) }}</p>
            <div class="modal-actions">
              <UButton variant="ghost" @click="showDeleteDashboard = false">{{ t('common.cancel') }}</UButton>
              <UButton color="red" :loading="deletingDashboard" @click="submitDeleteDashboard">{{ t('common.delete') }}</UButton>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Loading -->
    <div v-if="loading" class="db-grid loading-grid">
      <div v-for="i in 6" :key="i" class="grid-skel" :style="{ gridColumn: `span 4`, gridRow: 'span 3' }">
        <USkeleton class="h-full w-full rounded-lg" />
      </div>
    </div>

    <!-- Empty dashboard -->
    <div v-else-if="dashboard && !dashboard.widgets.length" class="db-empty">
      <div class="empty-icon">&#128202;</div>
      <p class="empty-title">{{ t('dashboardEnhance.noWidgetsYet') }}</p>
      <p class="empty-sub">{{ t('dashboardEnhance.noWidgetsHint') }}</p>
      <UButton @click="editMode = true; openAddWidget()">{{ t('dashboardEnhance.addWidget') }}</UButton>
    </div>

    <!-- Dashboard grid -->
    <div
      v-else-if="dashboard"
      ref="gridRef"
      class="db-grid"
      @dragover.prevent="onGridDragOver"
      @drop.prevent="onGridDrop"
    >
      <div
        v-for="widget in sortedWidgets"
        :key="widget.id"
        class="db-widget-cell"
        :class="{
          'widget-edit-mode': editMode,
          'widget-drag-over': dragOverWidgetId === widget.id,
        }"
        :style="{
          gridColumn: `${widget.grid_col} / span ${widget.grid_span_w}`,
          gridRow: `${widget.grid_row} / span ${widget.grid_span_h}`,
        }"
        :draggable="editMode"
        @dragstart="onWidgetDragStart($event, widget)"
        @dragend="onWidgetDragEnd"
        @dragover.prevent.stop="onWidgetDragOver($event, widget)"
        @dragleave="onWidgetDragLeave(widget)"
        @drop.prevent.stop="onWidgetDrop($event, widget)"
      >
        <!-- Edit mode controls -->
        <div v-if="editMode" class="widget-edit-controls">
          <span class="drag-handle" :title="t('dashboardEnhance.dragToReorder')">&#10303;</span>
          <div class="widget-edit-actions">
            <button class="we-btn cfg" @click.stop="openWidgetConfig(widget)" :title="t('dashboardEnhance.configure')">&#9881;</button>
            <button class="we-btn del" @click.stop="confirmDeleteWidget(widget)" :title="t('dashboardEnhance.removeTooltip')">&#10005;</button>
          </div>
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
          :display-config="widget.display_config"
          @range-change="(r) => { currentRange = r; reloadWidgetHistory(widget) }"
          @control-change="(v) => handleControlChange(widget, v)"
        />

        <!-- Resize handle (edit mode only) -->
        <div
          v-if="editMode"
          class="resize-handle"
          draggable="true"
          @dragstart.stop="onResizeStart($event, widget)"
          @drag.stop="onResizeDrag($event, widget)"
          @dragend.stop="onResizeEnd($event, widget)"
          :title="t('dashboardEnhance.dragToResize')"
        >&#9698;</div>
      </div>

      <!-- Add widget placeholder (edit mode) -->
      <div v-if="editMode" class="add-widget-cell" @click="openAddWidget()">
        <span class="add-icon">&#65291;</span>
        <span>{{ t('dashboardEnhance.addWidget') }}</span>
      </div>
    </div>

    <!-- Add Widget Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showAddWidget" class="modal-overlay" @click.self="showAddWidget = false">
          <div class="modal-box modal-flex">
            <!-- Header (fixed) -->
            <h2 class="modal-title modal-header-fixed">{{ editingWidgetId ? t('dashboardEnhance.editWidget') : t('dashboardEnhance.addWidget') }}</h2>

            <!-- Body (scrollable) -->
            <div class="modal-body-scroll form-fields">

              <!-- Widget type -->
              <div class="field">
                <label class="field-label">{{ t('dashboardEnhance.widgetType') }}</label>
                <p class="text-[9px] text-[var(--text-muted)] -mt-0.5 mb-1">{{ t('dashboardEnhance.widgetTypeFieldHint') }}</p>
                <select v-model="newWidget.widget_type" class="field-input">
                  <optgroup :label="t('dashboardEnhance.visualizations')">
                    <option value="line_chart">{{ t('dashboardEnhance.lineChart') }}</option>
                    <option value="gauge">{{ t('dashboardEnhance.gauge') }}</option>
                    <option value="sparkline">{{ t('dashboardEnhance.sparkline') }}</option>
                    <option value="bool">{{ t('dashboardEnhance.statusBool') }}</option>
                    <option value="log">{{ t('dashboardEnhance.log') }}</option>
                    <option value="json">{{ t('dashboardEnhance.jsonViewer') }}</option>
                    <option value="map">{{ t('dashboardEnhance.mapGps') }}</option>
                  </optgroup>
                  <optgroup :label="t('dashboardEnhance.controls')">
                    <option value="control_toggle">{{ t('dashboardEnhance.toggleSwitch') }}</option>
                    <option value="control_slider">{{ t('dashboardEnhance.slider') }}</option>
                  </optgroup>
                  <optgroup :label="t('dashboard.htmlTemplate.groupLabel') || 'Custom'">
                    <option value="html_template">{{ t('dashboard.htmlTemplate.name') || 'Custom HTML' }}</option>
                  </optgroup>
                </select>
              </div>

              <!-- Device first, then variable (filtered by device) -->
              <div class="field">
                <UEntitySelect v-model="newWidget.device_uid" entity-type="device" :label="t('dashboardEnhance.selectDevice')" :placeholder="t('dashboardEnhance.chooseDeviceFirst')" :optional="true" />
              </div>

              <div class="field">
                <p class="text-[9px] text-[var(--text-muted)] mb-1">{{ t('dashboardEnhance.variableKeyFieldHint') }}</p>
                <UEntitySelect v-model="newWidget.variable_key" entity-type="variable" :label="t('dashboardEnhance.selectVariable')" :placeholder="newWidget.device_uid ? t('dashboardEnhance.variablesForDevice') : t('dashboardEnhance.selectDeviceOrGlobal')" />
              </div>

              <!-- Label -->
              <div class="field">
                <label class="field-label">{{ t('dashboardEnhance.label') }}</label>
                <input v-model="newWidget.label" class="field-input" :placeholder="t('dashboardEnhance.displayLabel')" />
              </div>

              <!-- Unit (numeric widgets) -->
              <div v-if="isNumericType(newWidget.widget_type)" class="field-row-3">
                <div class="field">
                  <label class="field-label">{{ t('dashboardEnhance.unit') }}</label>
                  <input v-model="newWidget.unit" class="field-input" placeholder="deg C" />
                </div>
                <div class="field">
                  <label class="field-label">{{ t('dashboardEnhance.min') }}</label>
                  <input v-model.number="newWidget.min_value" type="number" class="field-input" placeholder="0" />
                </div>
                <div class="field">
                  <label class="field-label">{{ t('dashboardEnhance.max') }}</label>
                  <input v-model.number="newWidget.max_value" type="number" class="field-input" placeholder="100" />
                </div>
              </div>

              <!-- Grid size -->
              <div class="field-row-2">
                <div class="field">
                  <label class="field-label">{{ t('dashboardEnhance.widthCols') }}</label>
                  <select v-model.number="newWidget.grid_span_w" class="field-input">
                    <option v-for="n in [2,3,4,5,6,8,10,12]" :key="n" :value="n">{{ n }}</option>
                  </select>
                </div>
                <div class="field">
                  <label class="field-label">{{ t('dashboardEnhance.heightRows') }}</label>
                  <select v-model.number="newWidget.grid_span_h" class="field-input">
                    <option v-for="n in [2,3,4,5,6]" :key="n" :value="n">{{ n }}</option>
                  </select>
                </div>
              </div>

              <!-- HTML Template Editor (only for html_template type) -->
              <template v-if="newWidget.widget_type === 'html_template'">
                <div class="field">
                  <div class="html-editor-header">
                    <label class="field-label">{{ t('dashboard.htmlTemplate.editorLabel') || 'HTML Template' }}</label>
                    <div class="html-preview-tabs">
                      <button
                        class="hpt-btn"
                        :class="{ active: htmlEditorMode === 'code' }"
                        @click="htmlEditorMode = 'code'"
                      >{{ t('dashboard.htmlTemplate.code') || 'Code' }}</button>
                      <button
                        class="hpt-btn"
                        :class="{ active: htmlEditorMode === 'split' }"
                        @click="htmlEditorMode = 'split'"
                      >{{ t('dashboard.htmlTemplate.split') || 'Split' }}</button>
                      <button
                        class="hpt-btn"
                        :class="{ active: htmlEditorMode === 'preview' }"
                        @click="htmlEditorMode = 'preview'"
                      >{{ t('dashboard.htmlTemplate.preview') || 'Preview' }}</button>
                    </div>
                  </div>

                  <div class="html-editor-container" :class="{ 'split-mode': htmlEditorMode === 'split' }">
                    <textarea
                      v-if="htmlEditorMode !== 'preview'"
                      v-model="newWidget.html_template"
                      class="html-editor-textarea"
                      :placeholder="htmlDefaultTemplate"
                      spellcheck="false"
                      rows="12"
                    />
                    <div
                      v-if="htmlEditorMode !== 'code'"
                      class="html-preview-frame"
                    >
                      <iframe
                        :srcdoc="htmlPreviewSrcdoc"
                        sandbox="allow-same-origin"
                        class="html-preview-iframe"
                      />
                    </div>
                  </div>

                  <!-- Available variables reference -->
                  <div class="html-vars-ref">
                    <span class="html-vars-title">{{ t('dashboard.htmlTemplate.availableVars') || 'Available variables' }}:</span>
                    <code v-for="v in templateVarsList" :key="v" class="html-var-tag" @click="insertTemplateVar(v)">{{ v }}</code>
                  </div>
                </div>
              </template>

              <p v-if="addError" class="field-error">{{ addError }}</p>

            </div>

            <!-- Footer (fixed) -->
            <div class="modal-footer-fixed">
              <UButton variant="ghost" @click="showAddWidget = false">{{ t('common.cancel') }}</UButton>
              <UButton :loading="adding" @click="submitAddWidget">{{ editingWidgetId ? t('dashboardEnhance.saveChanges') : t('dashboardEnhance.addWidget') }}</UButton>
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
            <h2 class="modal-title">{{ t('dashboardEnhance.removeWidget') }}</h2>
            <p class="modal-sub">{{ t('dashboardEnhance.removeWidgetMessage', { name: deletingWidget.label || deletingWidget.variable_key || 'Widget' }) }}</p>
            <div class="modal-actions">
              <UButton variant="ghost" @click="deletingWidget = null">{{ t('common.cancel') }}</UButton>
              <UButton color="red" :loading="deleting" @click="submitDeleteWidget">{{ t('dashboardEnhance.remove') }}</UButton>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from "vue";
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
  updateDashboard,
  deleteDashboard,
  shareDashboard,
  setDashboardPin,
  unshareDashboard,
  updateEmbedConfig,
  updateKioskConfig,
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
const editingWidgetId = ref<number | null>(null);

// Delete widget
const deletingWidget = ref<DashboardWidget | null>(null);
const deleting = ref(false);

// Inline name editing
const editingName = ref(false);
const editNameValue = ref("");
const nameInputRef = ref<HTMLInputElement | null>(null);

// Share panel
const showSharePanel = ref(false);
const shareTab = ref<"private" | "public" | "embed">("private");
const shareMode = ref<"private" | "public">("private");
const shareUrl = ref("");
const shareToken = ref("");
const copied = ref(false);
const pinEnabled = ref(false);
const pinValue = ref("");

// Embed state
const embedCopied = ref(false);
const embedReferers = ref("");
const embedExpiresAt = ref("");
const embedSnippet = computed(() => {
  if (!shareToken.value) return "";
  return `<iframe src="${window.location.origin}/embed/${shareToken.value}" width="100%" height="600" frameborder="0"></iframe>`;
});

// Kiosk state
const kioskInterval = ref(30);
const kioskShowHeader = ref(true);
const kioskShowClock = ref(true);

// Settings panel
const showSettingsPanel = ref(false);
const settingsName = ref("");
const settingsDescription = ref("");
const settingsIsDefault = ref(false);
const savingSettings = ref(false);

// Delete dashboard
const showDeleteDashboard = ref(false);
const deletingDashboard = ref(false);

// Drag-and-drop state
const dragWidgetId = ref<number | null>(null);
const dragOverWidgetId = ref<number | null>(null);
const gridRef = ref<HTMLElement | null>(null);

// Resize state
const resizeWidgetId = ref<number | null>(null);
const resizeStartX = ref(0);
const resizeStartY = ref(0);
const resizeStartW = ref(0);
const resizeStartH = ref(0);

// HTML Template editor state
const htmlEditorMode = ref<"code" | "split" | "preview">("code");

const htmlDefaultTemplate = `<div style="padding: 16px; font-family: Inter, sans-serif; color: #fff;">
  <h2 style="margin: 0 0 8px; font-size: 14px; opacity: 0.7;">{{device:name}}</h2>
  <div style="font-size: 36px; font-weight: bold;">{{value}} {{unit}}</div>
  <div style="margin-top: 8px; font-size: 12px; opacity: 0.5;">Updated {{timestamp:relative}}</div>
</div>`;

const templateVarsList = [
  "{{value}}", "{{value:key}}", "{{unit}}", "{{unit:key}}",
  "{{device:name}}", "{{device:status}}", "{{label}}",
  "{{timestamp}}", "{{timestamp:relative}}", "{{points:count}}",
];

const htmlPreviewSrcdoc = computed(() => {
  const tpl = newWidget.value.html_template || htmlDefaultTemplate;
  // Replace template vars with sample values for preview
  let preview = tpl
    .replace(/\{\{value\}\}/g, "23.5")
    .replace(/\{\{value:[^}]+\}\}/g, "23.5")
    .replace(/\{\{unit\}\}/g, newWidget.value.unit || "\u00B0C")
    .replace(/\{\{unit:[^}]+\}\}/g, newWidget.value.unit || "\u00B0C")
    .replace(/\{\{device:name\}\}/g, newWidget.value.label || "My Device")
    .replace(/\{\{device:status\}\}/g, "online")
    .replace(/\{\{label\}\}/g, newWidget.value.label || "Widget")
    .replace(/\{\{timestamp\}\}/g, new Date().toLocaleString())
    .replace(/\{\{timestamp:relative\}\}/g, "2m ago")
    .replace(/\{\{points:count\}\}/g, "42");

  return `<!DOCTYPE html><html><head><meta charset="utf-8"><style>*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}html,body{background:transparent;color:#e6edf3;font-family:Inter,-apple-system,BlinkMacSystemFont,sans-serif;font-size:14px;line-height:1.5;overflow:hidden}</style></head><body>${preview}</body></html>`;
});

function insertTemplateVar(v: string) {
  // Insert at cursor or append to template
  newWidget.value.html_template = (newWidget.value.html_template || "") + v;
}

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
    html_template: "",
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
      if (!newWidget.value.label) newWidget.value.label = def.description || def.key;
      if (!newWidget.value.unit && def.unit) newWidget.value.unit = def.unit;
      // Don't auto-switch type if user explicitly chose html_template
      if (newWidget.value.widget_type !== "html_template") {
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
    }
  } catch { /* auto-suggest is best-effort */ }
});

// Auto-populate default template when switching to html_template type
watch(() => newWidget.value.widget_type, (type) => {
  if (type === "html_template" && !newWidget.value.html_template) {
    newWidget.value.html_template = htmlDefaultTemplate;
    htmlEditorMode.value = "split";
  }
});

// ── Dashboard CRUD ───────────────────────────────────────────────────────────

async function loadDashboard() {
  loading.value = true;
  try {
    const id = Number(route.params.id);
    dashboard.value = await getDashboard(id);
    // Sync share state
    shareMode.value = dashboard.value.sharing_mode === "private" ? "private" : "public";
    shareTab.value = shareMode.value;
    if (dashboard.value.public_token) {
      shareToken.value = dashboard.value.public_token;
      shareUrl.value = `${window.location.origin}/dashboards/public/${shareToken.value}`;
    }
    // Sync embed config
    const ec = dashboard.value.embed_config;
    if (ec) {
      embedReferers.value = (ec.allowed_referers || []).join(", ");
      embedExpiresAt.value = ec.expires_at || "";
    }
    // Sync kiosk config
    const kc = dashboard.value.kiosk_config;
    if (kc) {
      kioskInterval.value = kc.slide_interval ?? 30;
      kioskShowHeader.value = kc.show_header ?? true;
      kioskShowClock.value = kc.show_clock ?? true;
    }
    await loadAllHistory();
  } catch {
    dashboard.value = null;
  } finally {
    loading.value = false;
  }
}

function startEditName() {
  if (!dashboard.value) return;
  editNameValue.value = dashboard.value.name;
  editingName.value = true;
  nextTick(() => nameInputRef.value?.focus());
}

async function saveDashboardName() {
  if (!dashboard.value || !editNameValue.value.trim()) {
    editingName.value = false;
    return;
  }
  try {
    const updated = await updateDashboard(dashboard.value.id, { name: editNameValue.value.trim() });
    dashboard.value.name = updated.name;
  } catch { /* silent */ }
  editingName.value = false;
}

function openSettingsPanel() {
  if (!dashboard.value) return;
  settingsName.value = dashboard.value.name;
  settingsDescription.value = dashboard.value.description || "";
  settingsIsDefault.value = dashboard.value.is_default;
  showSettingsPanel.value = true;
}

// Auto-sync settings values when panel opens
watch(showSettingsPanel, (open) => {
  if (open && dashboard.value) {
    settingsName.value = dashboard.value.name;
    settingsDescription.value = dashboard.value.description || "";
    settingsIsDefault.value = dashboard.value.is_default;
  }
});

async function saveSettings() {
  if (!dashboard.value) return;
  savingSettings.value = true;
  try {
    const updated = await updateDashboard(dashboard.value.id, {
      name: settingsName.value.trim() || dashboard.value.name,
      description: settingsDescription.value.trim() || null,
      is_default: settingsIsDefault.value,
    });
    dashboard.value.name = updated.name;
    dashboard.value.description = updated.description;
    dashboard.value.is_default = updated.is_default;
    // Save kiosk config
    await updateKioskConfig(dashboard.value.id, {
      auto_slide: false,
      slide_interval: kioskInterval.value,
      slide_dashboards: [],
      show_header: kioskShowHeader.value,
      show_clock: kioskShowClock.value,
    });
    showSettingsPanel.value = false;
  } catch { /* silent */ }
  savingSettings.value = false;
}

function confirmDeleteDashboard() {
  showSettingsPanel.value = false;
  showDeleteDashboard.value = true;
}

async function submitDeleteDashboard() {
  if (!dashboard.value) return;
  deletingDashboard.value = true;
  try {
    await deleteDashboard(dashboard.value.id);
    router.push("/dashboards");
  } catch { /* silent */ }
  deletingDashboard.value = false;
}

// ── Sharing ──────────────────────────────────────────────────────────────────

async function toggleShareMode(mode: "private" | "public") {
  if (!dashboard.value) return;
  if (mode === "public") {
    try {
      const result = await shareDashboard(dashboard.value.id);
      shareToken.value = result.public_token;
      shareUrl.value = `${window.location.origin}${result.url}`;
      shareMode.value = "public";
      dashboard.value.sharing_mode = "public";
    } catch { /* silent */ }
  } else {
    try {
      await unshareDashboard(dashboard.value.id);
      shareMode.value = "private";
      shareUrl.value = "";
      shareToken.value = "";
      pinEnabled.value = false;
      pinValue.value = "";
      dashboard.value.sharing_mode = "private";
    } catch { /* silent */ }
  }
}

function copyShareUrl() {
  if (!shareUrl.value) return;
  navigator.clipboard.writeText(shareUrl.value);
  copied.value = true;
  setTimeout(() => copied.value = false, 2000);
}

function handlePinToggle() {
  if (!pinEnabled.value) {
    // Unset PIN by re-sharing without pin
    if (dashboard.value) {
      shareDashboard(dashboard.value.id);
    }
    pinValue.value = "";
  }
}

async function savePin() {
  if (!dashboard.value || !pinValue.value || pinValue.value.length < 4) return;
  try {
    await setDashboardPin(dashboard.value.id, pinValue.value);
  } catch { /* silent */ }
}

// ── Embed ──────────────────────────────────────────────────────────────────

function switchShareTab(tab: "private" | "public" | "embed") {
  if (tab === "private") {
    toggleShareMode("private");
  } else if (tab === "public") {
    toggleShareMode("public");
  }
  shareTab.value = tab;
}

function copyEmbedSnippet() {
  if (!embedSnippet.value) return;
  navigator.clipboard.writeText(embedSnippet.value);
  embedCopied.value = true;
  setTimeout(() => embedCopied.value = false, 2000);
}

async function saveEmbedConfig() {
  if (!dashboard.value) return;
  try {
    await updateEmbedConfig(dashboard.value.id, {
      allowed_referers: embedReferers.value ? embedReferers.value.split(",").map(s => s.trim()).filter(Boolean) : [],
      expires_at: embedExpiresAt.value || null,
      max_views: null,
    });
  } catch { /* silent */ }
}

// ── Kiosk ──────────────────────────────────────────────────────────────────

function openKioskSlideshow() {
  if (!dashboard.value) return;
  const params = new URLSearchParams({
    ids: String(dashboard.value.id),
    interval: String(kioskInterval.value),
    header: String(kioskShowHeader.value),
    clock: String(kioskShowClock.value),
  });
  window.open(`/kiosk/slideshow?${params.toString()}`, "_blank");
}

// ── Widget sorting/grid ──────────────────────────────────────────────────────

const sortedWidgets = computed<DashboardWidget[]>(() => {
  if (!dashboard.value) return [];
  return [...dashboard.value.widgets].sort((a, b) => a.sort_order - b.sort_order);
});

// ── Drag-and-Drop (widget swap) ──────────────────────────────────────────────

function onWidgetDragStart(e: DragEvent, widget: DashboardWidget) {
  if (!editMode.value) return;
  dragWidgetId.value = widget.id;
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", String(widget.id));
  }
}

function onWidgetDragEnd() {
  dragWidgetId.value = null;
  dragOverWidgetId.value = null;
}

function onWidgetDragOver(e: DragEvent, widget: DashboardWidget) {
  if (!editMode.value || !dragWidgetId.value || dragWidgetId.value === widget.id) return;
  if (resizeWidgetId.value) return; // Don't interfere with resize
  dragOverWidgetId.value = widget.id;
}

function onWidgetDragLeave(widget: DashboardWidget) {
  if (dragOverWidgetId.value === widget.id) {
    dragOverWidgetId.value = null;
  }
}

function onWidgetDrop(e: DragEvent, targetWidget: DashboardWidget) {
  if (!editMode.value || !dashboard.value || resizeWidgetId.value) return;
  const sourceId = dragWidgetId.value ?? Number(e.dataTransfer?.getData("text/plain"));
  if (!sourceId || sourceId === targetWidget.id) return;

  const widgets = dashboard.value.widgets;
  const source = widgets.find(w => w.id === sourceId);
  const target = targetWidget;
  if (!source) return;

  // Swap grid positions
  const tmpCol = source.grid_col;
  const tmpRow = source.grid_row;
  const tmpOrder = source.sort_order;
  source.grid_col = target.grid_col;
  source.grid_row = target.grid_row;
  source.sort_order = target.sort_order;
  target.grid_col = tmpCol;
  target.grid_row = tmpRow;
  target.sort_order = tmpOrder;

  dragWidgetId.value = null;
  dragOverWidgetId.value = null;
  saveLayout();
}

function onGridDragOver(e: DragEvent) {
  if (!editMode.value) return;
  e.dataTransfer!.dropEffect = "move";
}

function onGridDrop(e: DragEvent) {
  // Grid-level drop only if not handled by a widget
  dragWidgetId.value = null;
  dragOverWidgetId.value = null;
}

// ── Resize ───────────────────────────────────────────────────────────────────

function onResizeStart(e: DragEvent, widget: DashboardWidget) {
  resizeWidgetId.value = widget.id;
  resizeStartX.value = e.clientX;
  resizeStartY.value = e.clientY;
  resizeStartW.value = widget.grid_span_w;
  resizeStartH.value = widget.grid_span_h;
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = "none";
    // Use a transparent drag image so the default ghost doesn't appear
    const img = new Image();
    img.src = "data:image/gif;base64,R0lGODlhAQABAIAAAAUEBAAAACwAAAAAAQABAAACAkQBADs=";
    e.dataTransfer.setDragImage(img, 0, 0);
  }
}

function onResizeDrag(e: DragEvent, widget: DashboardWidget) {
  if (!resizeWidgetId.value || resizeWidgetId.value !== widget.id) return;
  if (e.clientX === 0 && e.clientY === 0) return; // browser sends 0,0 at end

  const grid = gridRef.value;
  if (!grid) return;

  const colWidth = grid.clientWidth / 12;
  const rowHeight = 60; // grid-auto-rows

  const dx = e.clientX - resizeStartX.value;
  const dy = e.clientY - resizeStartY.value;

  const newW = Math.max(2, Math.min(12, resizeStartW.value + Math.round(dx / colWidth)));
  const newH = Math.max(2, Math.min(6, resizeStartH.value + Math.round(dy / rowHeight)));

  // Clamp so widget doesn't exceed grid
  widget.grid_span_w = Math.min(newW, 13 - widget.grid_col);
  widget.grid_span_h = newH;
}

function onResizeEnd(e: DragEvent, widget: DashboardWidget) {
  if (resizeWidgetId.value === widget.id) {
    resizeWidgetId.value = null;
    saveLayout();
  }
}

// ── Layout persistence ───────────────────────────────────────────────────────

async function saveLayout() {
  if (!dashboard.value) return;
  try {
    const items = dashboard.value.widgets.map(w => ({
      id: w.id,
      sort_order: w.sort_order,
      grid_col: w.grid_col,
      grid_row: w.grid_row,
      grid_span_w: w.grid_span_w,
      grid_span_h: w.grid_span_h,
    }));
    await updateLayout(dashboard.value.id, items);
  } catch { /* silent */ }
}

// ── History loading ──────────────────────────────────────────────────────────

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

// ── Add or update widget ─────────────────────────────────────────────────────

async function submitAddWidget() {
  adding.value = true;
  addError.value = "";
  try {
    const dashId = Number(route.params.id);

    // Build display_config for html_template widgets
    const displayConfig: Record<string, unknown> | null =
      newWidget.value.widget_type === "html_template"
        ? { html_template: newWidget.value.html_template || htmlDefaultTemplate }
        : null;

    if (editingWidgetId.value) {
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
        ...(displayConfig ? { display_config: displayConfig } : {}),
      });
      const idx = dashboard.value!.widgets.findIndex((x) => x.id === editingWidgetId.value);
      if (idx >= 0) dashboard.value!.widgets[idx] = w;
      if (w.variable_key) loadWidgetHistory(w);
    } else {
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
        ...(displayConfig ? { display_config: displayConfig } : {}),
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

function getNextGridPosition(): { col: number; row: number } {
  if (!dashboard.value?.widgets.length) return { col: 1, row: 1 };
  const sorted = [...dashboard.value.widgets].sort((a, b) => a.sort_order - b.sort_order);
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
  } catch {
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
    html_template: (widget.display_config?.html_template as string) || "",
  };
  // Reset HTML editor mode when opening config
  if (widget.widget_type === "html_template") {
    htmlEditorMode.value = "split";
  }
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

/* -- Top bar ------------------------------------------------ */
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
.db-name-editable {
  cursor: pointer;
  border-bottom: 1px dashed var(--text-muted);
  padding-bottom: 1px;
}
.db-name-editable:hover { border-bottom-color: var(--primary); }
.db-name-input {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-base);
  background: var(--bg-base);
  border: 1px solid var(--primary);
  border-radius: 4px;
  padding: 2px 8px;
  outline: none;
  width: 240px;
}

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

.share-btn,
.settings-btn {
  padding: 5px 10px;
  font-size: 14px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text-muted);
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}
.share-btn:hover,
.settings-btn:hover { color: var(--text-base); border-color: var(--primary); }

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

/* -- Grid --------------------------------------------------- */
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
  transition: box-shadow 0.15s, border-color 0.15s;
  border-radius: 6px;
}
.db-widget-cell > .viz-widget,
.db-widget-cell > * {
  height: 100%;
}

/* Edit mode: dashed border around widgets */
.widget-edit-mode {
  border: 1px dashed var(--border);
  cursor: grab;
}
.widget-edit-mode:active { cursor: grabbing; }
.widget-drag-over {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary) 30%, transparent);
}

/* Edit controls: top bar on each widget */
.widget-edit-controls {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 6px;
  pointer-events: none;
}
.widget-edit-controls > * { pointer-events: auto; }

.drag-handle {
  font-size: 16px;
  color: var(--text-muted);
  cursor: grab;
  user-select: none;
  opacity: 0.6;
  line-height: 1;
}
.drag-handle:hover { opacity: 1; color: var(--text-base); }

.widget-edit-actions {
  display: flex;
  gap: 3px;
}

.we-btn {
  width: 22px; height: 22px;
  border-radius: 4px;
  border: 1px solid var(--border);
  background: var(--bg-surface);
  color: var(--text-muted);
  font-size: 11px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
.we-btn.del:hover { background: var(--status-bad); color: #fff; border-color: var(--status-bad); }
.we-btn.cfg:hover { background: var(--primary); color: #000; border-color: var(--primary); }

/* Resize handle */
.resize-handle {
  position: absolute;
  bottom: 2px;
  right: 2px;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: var(--text-muted);
  cursor: nwse-resize;
  opacity: 0.5;
  z-index: 10;
  user-select: none;
  transition: opacity 0.15s;
}
.resize-handle:hover { opacity: 1; color: var(--primary); }

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

/* -- Share panel -------------------------------------------- */
.share-modes {
  display: flex;
  gap: 4px;
  margin-bottom: 8px;
}
.share-mode-btn {
  flex: 1;
  padding: 8px 12px;
  font-size: 13px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s;
}
.share-mode-btn.active {
  border-color: var(--primary);
  color: var(--primary);
  background: color-mix(in srgb, var(--primary) 10%, transparent);
}
.share-mode-btn:hover:not(.active) { border-color: var(--text-muted); }

.share-url-row {
  display: flex;
  gap: 4px;
}
.share-url-input {
  flex: 1;
  font-size: 11px;
  font-family: monospace;
}
.copy-btn {
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text-muted);
  cursor: pointer;
  font-size: 14px;
  transition: color 0.15s;
  flex-shrink: 0;
}
.copy-btn:hover { color: var(--primary); }

.share-pin-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-base);
  cursor: pointer;
}
.share-pin-label input[type="checkbox"] {
  accent-color: var(--primary);
}

.share-info {
  font-size: 13px;
  color: var(--text-muted);
  padding: 8px 0;
}

/* -- Settings sections -------------------------------- */
.settings-section {
  border-top: 1px solid var(--border);
  padding-top: 12px;
  margin-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.settings-section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-base);
  margin-bottom: 4px;
}

/* -- Delete dashboard button -------------------------------- */
.delete-db-btn {
  margin-right: auto;
  padding: 6px 12px;
  font-size: 12px;
  border-radius: 6px;
  border: 1px solid var(--status-bad);
  background: transparent;
  color: var(--status-bad);
  cursor: pointer;
  transition: all 0.15s;
}
.delete-db-btn:hover {
  background: var(--status-bad);
  color: #fff;
}

/* -- Modal (reused) ----------------------------------------- */
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
.modal-box.modal-flex {
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}
.modal-header-fixed {
  padding: 24px 24px 0;
  margin-bottom: 0;
  shrink: 0;
}
.modal-body-scroll {
  padding: 16px 24px;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}
.modal-footer-fixed {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 24px;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}
.modal-small { width: min(360px, calc(100vw - 32px)); }
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

/* ── HTML Template Editor ──────────────────────────────── */
.html-editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.html-preview-tabs {
  display: flex;
  gap: 1px;
  background: var(--bg-elevated);
  border-radius: 4px;
  padding: 2px;
}
.hpt-btn {
  padding: 3px 10px;
  font-size: 11px;
  color: var(--text-muted);
  border-radius: 3px;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
}
.hpt-btn:hover { background: var(--bg-base); color: var(--text-base); }
.hpt-btn.active { background: var(--bg-base); color: var(--primary); }

.html-editor-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.html-editor-container.split-mode {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.html-editor-textarea {
  width: 100%;
  min-height: 200px;
  background: #0d1117;
  color: #e6edf3;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px;
  font-family: 'IBM Plex Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.6;
  resize: vertical;
  tab-size: 2;
}
.html-editor-textarea:focus {
  outline: none;
  border-color: var(--primary);
}

.html-preview-frame {
  background: #161b22;
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
  min-height: 200px;
}
.html-preview-iframe {
  width: 100%;
  height: 200px;
  border: none;
  background: transparent;
  display: block;
}

.html-vars-ref {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
}
.html-vars-title {
  font-size: 11px;
  color: var(--text-muted);
  margin-right: 4px;
}
.html-var-tag {
  font-size: 11px;
  background: var(--bg-elevated);
  color: var(--primary);
  padding: 2px 6px;
  border-radius: 3px;
  cursor: pointer;
  transition: background 0.15s;
  font-family: 'IBM Plex Mono', monospace;
}
.html-var-tag:hover {
  background: var(--primary);
  color: var(--bg-base);
}

.modal-enter-active, .modal-leave-active { transition: opacity 0.2s, transform 0.2s; }
.modal-enter-from, .modal-leave-to { opacity: 0; transform: scale(0.97); }
</style>
