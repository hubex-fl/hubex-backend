<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { mapErrorToUserText, parseApiError } from "../lib/errors";
import {
  type VariableDefinition,
  type VariableScope,
  type VariableValue,
  type VariableDefinitionInput,
  type VariableDefinitionPatchInput,
  type VariableValueInput,
  listDefinitions,
  createDefinition,
  patchDefinition,
  deleteDefinition,
  getValue,
  putValue,
  getDeviceVariables,
  getVariableHistory,
  type VariableHistoryPoint,
} from "../lib/variables";
import { DISPLAY_HINT_OPTIONS } from "../lib/viz-resolve";
import type { VizDataPoint } from "../lib/viz-types";

import UCard   from "../components/ui/UCard.vue";
import UButton from "../components/ui/UButton.vue";
import UInput  from "../components/ui/UInput.vue";
import USelect from "../components/ui/USelect.vue";
import UBadge  from "../components/ui/UBadge.vue";
import UModal  from "../components/ui/UModal.vue";
import UToggle from "../components/ui/UToggle.vue";
import VizSparkline from "../components/viz/VizSparkline.vue";
import VizWidget    from "../components/viz/VizWidget.vue";
import ContextMenu from "../components/ContextMenu.vue";
import UEntitySelect from "../components/ui/UEntitySelect.vue";
import { useConnectPanel } from "../composables/useConnectPanel";
import { useRouter } from "vue-router";
import type { ContextMenuItem } from "../components/ContextMenu.vue";

const router = useRouter();
const { open: openConnectPanel } = useConnectPanel();
const varMenuOpenKey = ref<string | null>(null);

function varMenuItems(def: VariableDefinition): ContextMenuItem[] {
  return [
    {
      label: "Edit Definition",
      icon: "M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z",
      action: () => openEditDef(def),
    },
    {
      label: "Connections",
      icon: "M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1",
      action: () =>
        openConnectPanel({
          type: "variable",
          id: def.key,
          name: def.key,
          variableKey: def.key,
        }),
    },
    { label: "", icon: "", action: () => {}, divider: true },
    {
      label: "Create Alert",
      icon: "M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0",
      action: () => router.push("/alerts"),
    },
    {
      label: "Create Automation",
      icon: "M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z",
      action: () => router.push("/automations"),
    },
    { label: "", icon: "", action: () => {}, divider: true },
    {
      label: "Delete",
      icon: "M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0",
      action: () => openDeleteDef(def),
      destructive: true,
    },
  ];
}

// ── State ──────────────────────────────────────────────────────────────────
type ScopeFilter = "all" | VariableScope;

const definitions   = ref<VariableDefinition[]>([]);
const valuesByKey   = ref<Record<string, VariableValue>>({});
const historyByKey  = ref<Record<string, VizDataPoint[]>>({});
const expandedKey   = ref<string | null>(null);
const error         = ref<string | null>(null);
const errorDetails  = ref<string | null>(null);
const loading       = ref(false);
const rowErrors     = ref<Record<string, string>>({});
const revealKeys    = ref<Set<string>>(new Set());

const search      = ref("");
const scopeFilter = ref<ScopeFilter>("all");
const deviceUid   = ref("");
const showSecrets = ref(true);

// ── Create modal ────────────────────────────────────────────────────────────
const createOpen      = ref(false);
const crKey           = ref("");
const crScope         = ref<VariableScope>("global");
const crDeviceUid     = ref("");
const crValueType     = ref<VariableDefinitionInput["valueType"]>("string");
const crDefaultValue  = ref("");
const crValue         = ref("");
const crIsSecret      = ref(false);
const crIsReadonly    = ref(false);
const crDisplayHint   = ref("auto");
const crCategory      = ref("");
const crDescription   = ref("");
const crUnit          = ref("");
const crMin           = ref("");
const crMax           = ref("");
const crSaving        = ref(false);
const crError         = ref<string | null>(null);

// ── Edit definition modal ──────────────────────────────────────────────────
const editOpen         = ref(false);
const editDef          = ref<VariableDefinition | null>(null);
const editDisplayHint  = ref("auto");
const editCategory     = ref("");
const editDescription  = ref("");
const editUnit         = ref("");
const editMin          = ref("");
const editMax          = ref("");
const editSaving       = ref(false);
const editError        = ref<string | null>(null);

// ── Set value modal ─────────────────────────────────────────────────────────
const setValueOpen    = ref(false);
const setValueDef     = ref<VariableDefinition | null>(null);
const setValueStr     = ref("");
const setValueVersion = ref<number | null>(null);
const setValueSaving  = ref(false);
const setValueError   = ref<string | null>(null);

// ── Conflict ────────────────────────────────────────────────────────────────
const conflictKey      = ref<string | null>(null);
const conflictMessage  = ref<string | null>(null);
const conflictVersion  = ref<number | null>(null);
const conflictScope    = ref<VariableScope | null>(null);
const conflictDuid     = ref<string | null>(null);
const overwritePending = ref(false);

// ── Helpers ─────────────────────────────────────────────────────────────────
function fmtApiError(err: unknown, fallback: string) {
  const info = parseApiError(err);
  const mapped = mapErrorToUserText(info, fallback);
  const status = info.httpStatus ? `HTTP ${info.httpStatus}` : "HTTP ?";
  return `${mapped || fallback} (${status}, ${info.code ?? "?"})`;
}

function parseValueInput(vt: string, raw: string): unknown {
  if (vt === "string") return raw;
  if (vt === "int")    return raw === "" ? null : parseInt(raw, 10);
  if (vt === "float")  return raw === "" ? null : parseFloat(raw);
  if (vt === "bool")   return raw.trim().toLowerCase() === "true";
  if (vt === "json")   { try { return JSON.parse(raw); } catch { return raw; } }
  return raw;
}

function valueDisplay(def: VariableDefinition, val?: VariableValue): string {
  if (def.is_secret && !revealKeys.value.has(def.key)) return "••••••";
  if (!val || val.value === null || val.value === undefined) return "–";
  if (typeof val.value === "string") return val.value.slice(0, 80);
  return JSON.stringify(val.value).slice(0, 80);
}

function updatedAgo(val?: VariableValue): string {
  if (!val?.updated_at) return "–";
  const ago = Math.floor((Date.now() - new Date(val.updated_at).getTime()) / 1000);
  if (ago < 60)    return `${ago}s ago`;
  if (ago < 3600)  return `${Math.floor(ago / 60)}m ago`;
  if (ago < 86400) return `${Math.floor(ago / 3600)}h ago`;
  return new Date(val.updated_at).toLocaleDateString();
}

function scopeStatus(scope: string): "info" | "neutral" {
  return scope === "global" ? "info" : "neutral";
}

function typeStatus(vt: string): "ok" | "warn" | "info" | "neutral" {
  const map: Record<string, "ok" | "warn" | "info" | "neutral"> = {
    int: "ok", float: "ok", bool: "warn", string: "info", json: "neutral",
  };
  return map[vt] ?? "neutral";
}

// ── Data loading ─────────────────────────────────────────────────────────────
async function loadDefinitionsAndValues() {
  error.value = null;
  loading.value = true;
  try {
    const defs = await listDefinitions(scopeFilter.value === "all" ? undefined : scopeFilter.value);
    definitions.value = defs;

    const values: Record<string, VariableValue> = {};
    if (deviceUid.value.trim()) {
      const vars = await getDeviceVariables(deviceUid.value.trim());
      for (const item of [...vars.globals, ...vars.device]) values[item.key] = item;
    } else {
      await Promise.all(
        defs.filter((d) => d.scope === "global").map(async (d) => {
          try { values[d.key] = await getValue({ key: d.key, scope: "global" }); } catch { /* no value yet */ }
        })
      );
    }
    valuesByKey.value = values;
    revealKeys.value = new Set();

    // Load sparkline data for numeric defs (last 1h, max 60 points, no await)
    loadSparklines(defs);
  } catch (e) {
    error.value = fmtApiError(e, "Failed to load variables");
  } finally {
    loading.value = false;
  }
}

async function loadSparklines(defs: VariableDefinition[]) {
  const numeric = defs.filter((d) => d.value_type === "int" || d.value_type === "float");
  const now = Math.floor(Date.now() / 1000);
  await Promise.all(
    numeric.map(async (d) => {
      try {
        const resp = await getVariableHistory({
          key: d.key,
          scope: d.scope,
          deviceUid: d.scope === "device" ? deviceUid.value.trim() || undefined : undefined,
          from: now - 3600,
          to: now,
          limit: 60,
          downsample: 60,
        });
        historyByKey.value = { ...historyByKey.value, [d.key]: resp.points as VizDataPoint[] };
      } catch { /* sparkline fails silently */ }
    })
  );
}

async function loadDetailHistory(def: VariableDefinition) {
  const now = Math.floor(Date.now() / 1000);
  try {
    const resp = await getVariableHistory({
      key: def.key,
      scope: def.scope,
      deviceUid: def.scope === "device" ? deviceUid.value.trim() || undefined : undefined,
      from: now - 86400,
      to: now,
      limit: 500,
      downsample: 300,
    });
    historyByKey.value = { ...historyByKey.value, [def.key]: resp.points as VizDataPoint[] };
  } catch { /* ignore */ }
}

// ── Create ────────────────────────────────────────────────────────────────────
function openCreate() {
  crKey.value = ""; crScope.value = "global"; crDeviceUid.value = "";
  crValueType.value = "string"; crDefaultValue.value = ""; crValue.value = "";
  crIsSecret.value = false; crIsReadonly.value = false;
  crDisplayHint.value = "auto"; crCategory.value = ""; crDescription.value = "";
  crUnit.value = ""; crMin.value = ""; crMax.value = "";
  crError.value = null; createOpen.value = true;
}

async function handleCreate() {
  crError.value = null;
  crSaving.value = true;
  try {
    const defInput: VariableDefinitionInput = {
      key: crKey.value.trim(),
      scope: crScope.value,
      valueType: crValueType.value,
      defaultValue: crDefaultValue.value ? parseValueInput(crValueType.value, crDefaultValue.value) : null,
      description: crDescription.value || null,
      isSecret: crIsSecret.value,
      isReadonly: crIsReadonly.value,
      displayHint: crDisplayHint.value !== "auto" ? crDisplayHint.value : null,
      category: crCategory.value || null,
      unit: crUnit.value || null,
      minValue: crMin.value !== "" ? parseFloat(crMin.value) : null,
      maxValue: crMax.value !== "" ? parseFloat(crMax.value) : null,
    } as unknown as VariableDefinitionInput;
    await createDefinition(defInput);
    if (crValue.value) {
      await putValue({
        key: crKey.value.trim(), scope: crScope.value,
        deviceUid: crScope.value === "device" ? crDeviceUid.value.trim() : undefined,
        value: parseValueInput(crValueType.value, crValue.value),
      });
    }
    createOpen.value = false;
    await loadDefinitionsAndValues();
  } catch (e) {
    crError.value = fmtApiError(e, "Failed to create variable");
  } finally {
    crSaving.value = false;
  }
}

// ── Edit definition ────────────────────────────────────────────────────────────
function openEditDef(def: VariableDefinition) {
  editDef.value = def;
  editDisplayHint.value = def.display_hint ?? "auto";
  editCategory.value = def.category ?? "";
  editDescription.value = def.description ?? "";
  editUnit.value = (def as unknown as { unit?: string }).unit ?? "";
  editMin.value = (def as unknown as { min_value?: number | null }).min_value != null
    ? String((def as unknown as { min_value: number }).min_value) : "";
  editMax.value = (def as unknown as { max_value?: number | null }).max_value != null
    ? String((def as unknown as { max_value: number }).max_value) : "";
  editError.value = null;
  editOpen.value = true;
}

async function handleEditSave() {
  if (!editDef.value) return;
  editError.value = null;
  editSaving.value = true;
  try {
    const patch: VariableDefinitionPatchInput = {
      description:  editDescription.value || null,
      displayHint:  editDisplayHint.value !== "auto" ? editDisplayHint.value : null,
      category:     editCategory.value || null,
      unit:         editUnit.value || null,
      minValue:     editMin.value !== "" ? parseFloat(editMin.value) : null,
      maxValue:     editMax.value !== "" ? parseFloat(editMax.value) : null,
    };
    const updated = await patchDefinition(editDef.value.key, patch);
    // Update local definitions list
    definitions.value = definitions.value.map((d) => d.key === updated.key ? updated : d);
    editOpen.value = false;
  } catch (e) {
    editError.value = fmtApiError(e, "Failed to update definition");
  } finally {
    editSaving.value = false;
  }
}

// ── Set value ────────────────────────────────────────────────────────────────
function openSetValue(def: VariableDefinition) {
  setValueDef.value = def;
  const cur = valuesByKey.value[def.key];
  setValueStr.value = cur?.value !== undefined && cur.value !== null ? JSON.stringify(cur.value) : "";
  setValueVersion.value = cur?.version ?? null;
  setValueError.value = null;
  setValueOpen.value = true;
}

async function handleSetValue() {
  if (!setValueDef.value) return;
  setValueError.value = null;
  setValueSaving.value = true;
  try {
    const input: VariableValueInput = {
      key: setValueDef.value.key,
      scope: setValueDef.value.scope,
      deviceUid: setValueDef.value.scope === "device" ? deviceUid.value.trim() || undefined : undefined,
      value: parseValueInput(setValueDef.value.value_type, setValueStr.value),
      expectedVersion: setValueVersion.value ?? undefined,
    };
    await putValue(input);
    setValueOpen.value = false;
    await loadDefinitionsAndValues();
  } catch (e: unknown) {
    const info = parseApiError(e);
    if (info.code === "VAR_VERSION_CONFLICT") {
      conflictKey.value = setValueDef.value.key;
      conflictMessage.value = fmtApiError(e, "Version conflict");
      conflictVersion.value = (info.meta as { current_version?: number })?.current_version ?? null;
      conflictScope.value = setValueDef.value.scope;
      conflictDuid.value = setValueDef.value.scope === "device" ? deviceUid.value.trim() : null;
      return;
    }
    setValueError.value = fmtApiError(e, "Failed to set value");
  } finally {
    setValueSaving.value = false;
  }
}

// ── Delete definition ─────────────────────────────────────────────────────────
async function handleDeleteDef(def: VariableDefinition) {
  if (!confirm(`Delete definition "${def.key}" and all its history? This cannot be undone.`)) return;
  try {
    await deleteDefinition(def.key);
    definitions.value = definitions.value.filter((d) => d.key !== def.key);
    const next = { ...valuesByKey.value };
    delete next[def.key];
    valuesByKey.value = next;
  } catch (e) {
    rowErrors.value = { ...rowErrors.value, [def.key]: fmtApiError(e, "Failed to delete") };
  }
}

// ── Conflict resolution ────────────────────────────────────────────────────
function clearConflict() {
  conflictKey.value = null; conflictMessage.value = null;
  conflictVersion.value = null; conflictScope.value = null; conflictDuid.value = null;
  overwritePending.value = false;
}

async function reloadAndRetry() {
  if (!conflictKey.value || !conflictScope.value) return;
  const latest = await getValue({
    key: conflictKey.value,
    scope: conflictScope.value,
    deviceUid: conflictScope.value === "device" ? conflictDuid.value ?? undefined : undefined,
  });
  setValueVersion.value = latest.version ?? null;
  setValueStr.value = JSON.stringify(latest.value ?? "");
  clearConflict();
  await handleSetValue();
}

// ── Expand detail ─────────────────────────────────────────────────────────────
function toggleExpand(def: VariableDefinition) {
  if (expandedKey.value === def.key) {
    expandedKey.value = null;
  } else {
    expandedKey.value = def.key;
    loadDetailHistory(def);
  }
}

// ── Filtered rows ─────────────────────────────────────────────────────────────
const filteredRows = computed(() => {
  const term = search.value.trim().toLowerCase();
  return definitions.value.filter((d) => {
    if (scopeFilter.value !== "all" && d.scope !== scopeFilter.value) return false;
    if (!showSecrets.value && d.is_secret) return false;
    if (!term) return true;
    return d.key.toLowerCase().includes(term)
      || (d.category ?? "").toLowerCase().includes(term)
      || (d.description ?? "").toLowerCase().includes(term);
  });
});

const isNumeric = (vt: string) => vt === "int" || vt === "float";

watch([scopeFilter, deviceUid], loadDefinitionsAndValues);
onMounted(loadDefinitionsAndValues);
</script>

<template>
  <div class="vars-page">
    <!-- ── Header ─────────────────────────────────────────────────── -->
    <div class="vars-header">
      <div class="vars-header-left">
        <h1 class="vars-title">Variables</h1>
        <span class="vars-count">{{ filteredRows.length }}</span>
      </div>
      <UButton @click="openCreate" size="sm">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        New Variable
      </UButton>
    </div>

    <!-- ── Toolbar ────────────────────────────────────────────────── -->
    <div class="vars-toolbar">
      <UInput v-model="search" placeholder="Search key, category, description…" class="toolbar-search" />
      <USelect v-model="scopeFilter" class="toolbar-scope">
        <option value="all">All scopes</option>
        <option value="global">Global</option>
        <option value="device">Device</option>
      </USelect>
      <UEntitySelect v-model="deviceUid" entity-type="device" placeholder="Filter by device..." :optional="true" class="toolbar-device" />
      <label class="toolbar-toggle">
        <UToggle v-model="showSecrets" size="sm" />
        <span>Secrets</span>
      </label>
    </div>

    <!-- ── Error ──────────────────────────────────────────────────── -->
    <div v-if="error" class="vars-error">{{ error }}</div>

    <!-- ── Loading ───────────────────────────────────────────────── -->
    <div v-if="loading" class="vars-loading">
      <div v-for="i in 4" :key="i" class="skel-row" :style="{ animationDelay: `${i * 0.08}s` }" />
    </div>

    <!-- ── Enhanced empty state ──────────────────────────────────── -->
    <div v-else-if="!filteredRows.length" class="vars-empty-enhanced">
      <div class="vars-empty-icon">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
        </svg>
      </div>
      <div class="vars-empty-text">
        <h3>No variables yet</h3>
        <p>Variables appear automatically when devices send telemetry. Or create one manually.</p>
      </div>
      <div class="vars-empty-actions">
        <UButton size="sm" @click="openCreate">
          <svg class="h-3.5 w-3.5 mr-1" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Create variable
        </UButton>
        <span class="vars-empty-hint">or connect a device to auto-discover →</span>
        <a href="/devices" class="vars-empty-link">Devices →</a>
      </div>
    </div>

    <!-- ── Table ─────────────────────────────────────────────────── -->
    <div v-else class="vars-table-wrap">
      <table class="vars-table">
        <thead>
          <tr>
            <th class="col-expand"></th>
            <th>Key</th>
            <th>Scope</th>
            <th>Type</th>
            <th>Value</th>
            <th class="col-spark">Trend</th>
            <th>Hint</th>
            <th>Updated</th>
            <th class="col-actions">Actions</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="def in filteredRows" :key="def.key">
            <!-- Main row -->
            <tr
              class="vars-row"
              :class="{ 'row-expanded': expandedKey === def.key }"
              @click="toggleExpand(def)"
            >
              <!-- Expand chevron -->
              <td class="col-expand">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#8b949e" stroke-width="2"
                  :style="{ transform: expandedKey === def.key ? 'rotate(90deg)' : 'none', transition: 'transform 0.15s' }">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </td>

              <!-- Key + category + description -->
              <td class="col-key">
                <div class="key-wrap">
                  <span class="key-name">{{ def.key }}</span>
                  <span v-if="def.category" class="key-cat">{{ def.category }}</span>
                </div>
                <span v-if="def.description" class="key-desc">{{ def.description }}</span>
              </td>

              <!-- Scope -->
              <td><UBadge :status="scopeStatus(def.scope)" size="sm">{{ def.scope }}</UBadge></td>

              <!-- Type -->
              <td>
                <UBadge :status="typeStatus(def.value_type)" size="sm">{{ def.value_type }}</UBadge>
                <span v-if="def.unit" class="type-unit">{{ def.unit }}</span>
              </td>

              <!-- Value -->
              <td class="col-value" @click.stop>
                <span
                  class="value-text"
                  :class="{ 'value-secret': def.is_secret && !revealKeys.has(def.key), 'value-null': !valuesByKey[def.key]?.value && valuesByKey[def.key]?.value !== 0 }"
                >
                  {{ valueDisplay(def, valuesByKey[def.key]) }}
                </span>
                <button
                  v-if="def.is_secret"
                  class="reveal-btn"
                  @click.stop="revealKeys = new Set(revealKeys.has(def.key) ? [...revealKeys].filter(k => k !== def.key) : [...revealKeys, def.key])"
                >
                  {{ revealKeys.has(def.key) ? "hide" : "show" }}
                </button>
              </td>

              <!-- Sparkline -->
              <td class="col-spark" @click.stop>
                <VizSparkline
                  v-if="isNumeric(def.value_type) && historyByKey[def.key]?.length"
                  :points="historyByKey[def.key]"
                  :label="def.key"
                  :width="72"
                  :height="26"
                />
                <span v-else-if="!isNumeric(def.value_type)" class="spark-na">—</span>
              </td>

              <!-- Display hint -->
              <td>
                <span v-if="def.display_hint" class="hint-badge">{{ def.display_hint }}</span>
                <span v-else class="hint-none">auto</span>
              </td>

              <!-- Updated -->
              <td class="col-time">{{ updatedAgo(valuesByKey[def.key]) }}</td>

              <!-- Actions -->
              <td class="col-actions" @click.stop>
                <div class="row-actions">
                  <UButton size="sm" variant="ghost" @click.stop="openSetValue(def)" title="Set value">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                  </UButton>
                  <!-- Context menu "..." -->
                  <div class="relative">
                    <UButton
                      size="sm"
                      variant="ghost"
                      title="More actions"
                      @click.stop="varMenuOpenKey = varMenuOpenKey === def.key ? null : def.key"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                        <circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/>
                      </svg>
                    </UButton>
                    <ContextMenu
                      :items="varMenuItems(def)"
                      :open="varMenuOpenKey === def.key"
                      @close="varMenuOpenKey = null"
                    />
                  </div>
                </div>
                <div v-if="rowErrors[def.key]" class="row-err-text">{{ rowErrors[def.key] }}</div>
              </td>
            </tr>

            <!-- Expanded detail panel -->
            <tr v-if="expandedKey === def.key" class="detail-row">
              <td colspan="9">
                <div class="detail-panel">
                  <div class="detail-meta">
                    <div class="meta-item">
                      <span class="meta-label">Key</span>
                      <code class="meta-val">{{ def.key }}</code>
                    </div>
                    <div class="meta-item">
                      <span class="meta-label">Type</span>
                      <code class="meta-val">{{ def.value_type }}</code>
                    </div>
                    <div v-if="def.unit" class="meta-item">
                      <span class="meta-label">Unit</span>
                      <code class="meta-val">{{ def.unit }}</code>
                    </div>
                    <div v-if="def.display_hint" class="meta-item">
                      <span class="meta-label">Viz</span>
                      <code class="meta-val">{{ def.display_hint }}</code>
                    </div>
                    <div v-if="def.min_value != null || def.max_value != null" class="meta-item">
                      <span class="meta-label">Range</span>
                      <code class="meta-val">{{ def.min_value ?? "–" }} … {{ def.max_value ?? "–" }}</code>
                    </div>
                    <div v-if="def.description" class="meta-item wide">
                      <span class="meta-label">Description</span>
                      <span class="meta-val">{{ def.description }}</span>
                    </div>
                  </div>

                  <!-- VizWidget for the variable -->
                  <VizWidget
                    :variableKey="def.key"
                    :label="def.key"
                    :unit="def.unit ?? undefined"
                    :valueType="def.value_type"
                    :displayHint="def.display_hint"
                    :currentValue="valuesByKey[def.key]?.value"
                    :points="historyByKey[def.key] ?? []"
                    :min="def.min_value"
                    :max="def.max_value"
                    :height="200"
                    :compact="false"
                    :showHeader="true"
                    :timeRange="'24h'"
                  />
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- ── Create Variable Modal ──────────────────────────────────── -->
    <UModal :open="createOpen" title="New Variable" @close="createOpen = false">
      <div class="modal-body">
        <div class="form-grid">
          <div class="form-field">
            <label>Key *</label>
            <UInput v-model="crKey" placeholder="e.g. sensor.temperature" />
          </div>
          <div class="form-field">
            <label>Scope</label>
            <USelect v-model="crScope">
              <option value="global">Global</option>
              <option value="device">Device</option>
            </USelect>
          </div>
          <div v-if="crScope === 'device'" class="form-field">
            <label>Device UID</label>
            <UEntitySelect v-model="crDeviceUid" entity-type="device" placeholder="Select device..." :optional="true" />
          </div>
          <div class="form-field">
            <label>Value type</label>
            <USelect v-model="crValueType">
              <option value="string">string</option>
              <option value="int">int</option>
              <option value="float">float</option>
              <option value="bool">bool</option>
              <option value="json">json</option>
            </USelect>
          </div>
          <div class="form-field">
            <label>Default value</label>
            <UInput v-model="crDefaultValue" :placeholder="crValueType === 'json' ? '{…}' : 'optional'" />
          </div>
          <div class="form-field">
            <label>Initial value</label>
            <UInput v-model="crValue" placeholder="Set immediately (optional)" />
          </div>
          <div class="form-field">
            <label>Description</label>
            <UInput v-model="crDescription" placeholder="Human-readable description" />
          </div>
          <div class="form-field">
            <label>Category</label>
            <UInput v-model="crCategory" placeholder="e.g. sensor.temperature, gps, config" />
          </div>
          <div class="form-field">
            <label>Unit</label>
            <UInput v-model="crUnit" placeholder="°C, %, m/s, …" />
          </div>
          <div class="form-field">
            <label>Visualization</label>
            <USelect v-model="crDisplayHint">
              <option v-for="opt in DISPLAY_HINT_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </USelect>
          </div>
          <div class="form-field" v-if="crValueType === 'int' || crValueType === 'float'">
            <label>Min value</label>
            <UInput v-model="crMin" type="number" placeholder="0" />
          </div>
          <div class="form-field" v-if="crValueType === 'int' || crValueType === 'float'">
            <label>Max value</label>
            <UInput v-model="crMax" type="number" placeholder="100" />
          </div>
        </div>
        <div class="form-toggles">
          <label class="toggle-row">
            <UToggle v-model="crIsSecret" size="sm" />
            <span>Secret <span class="toggle-hint">— value masked in lists</span></span>
          </label>
          <label class="toggle-row">
            <UToggle v-model="crIsReadonly" size="sm" />
            <span>Read-only <span class="toggle-hint">— devices cannot overwrite</span></span>
          </label>
        </div>
        <div v-if="crError" class="modal-error">{{ crError }}</div>
      </div>
      <template #footer>
        <UButton variant="ghost" @click="createOpen = false">Cancel</UButton>
        <UButton @click="handleCreate" :loading="crSaving">Create</UButton>
      </template>
    </UModal>

    <!-- ── Edit Definition Modal ──────────────────────────────────── -->
    <UModal :open="editOpen" :title="`Edit — ${editDef?.key ?? ''}`" @close="editOpen = false">
      <div class="modal-body" v-if="editDef">
        <div class="edit-readonly-info">
          <UBadge :status="scopeStatus(editDef.scope)" size="sm">{{ editDef.scope }}</UBadge>
          <UBadge :status="typeStatus(editDef.value_type)" size="sm">{{ editDef.value_type }}</UBadge>
          <span class="edit-readonly-note">Key and type cannot be changed</span>
        </div>
        <div class="form-grid">
          <div class="form-field wide">
            <label>Description</label>
            <UInput v-model="editDescription" placeholder="Human-readable description" />
          </div>
          <div class="form-field">
            <label>Category</label>
            <UInput v-model="editCategory" placeholder="e.g. sensor.temperature" />
          </div>
          <div class="form-field">
            <label>Unit</label>
            <UInput v-model="editUnit" placeholder="°C, %, m/s, …" />
          </div>
          <div class="form-field">
            <label>Visualization hint</label>
            <USelect v-model="editDisplayHint">
              <option v-for="opt in DISPLAY_HINT_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </USelect>
          </div>
          <div class="form-field" v-if="editDef.value_type === 'int' || editDef.value_type === 'float'">
            <label>Min value</label>
            <UInput v-model="editMin" type="number" />
          </div>
          <div class="form-field" v-if="editDef.value_type === 'int' || editDef.value_type === 'float'">
            <label>Max value</label>
            <UInput v-model="editMax" type="number" />
          </div>
        </div>
        <div v-if="editError" class="modal-error">{{ editError }}</div>
      </div>
      <template #footer>
        <UButton variant="ghost" @click="editOpen = false">Cancel</UButton>
        <UButton @click="handleEditSave" :loading="editSaving">Save changes</UButton>
      </template>
    </UModal>

    <!-- ── Set Value Modal ────────────────────────────────────────── -->
    <UModal :open="setValueOpen" :title="`Set value — ${setValueDef?.key ?? ''}`" @close="setValueOpen = false">
      <div class="modal-body" v-if="setValueDef">
        <div class="edit-readonly-info">
          <UBadge :status="typeStatus(setValueDef.value_type)" size="sm">{{ setValueDef.value_type }}</UBadge>
          <UBadge :status="scopeStatus(setValueDef.scope)" size="sm">{{ setValueDef.scope }}</UBadge>
        </div>
        <div class="form-field">
          <label>Value</label>
          <textarea
            v-model="setValueStr"
            class="value-textarea"
            rows="4"
            :placeholder="setValueDef.value_type === 'json' ? '{ &quot;key&quot;: &quot;value&quot; }' : 'enter value…'"
          />
        </div>
        <!-- Conflict banner -->
        <div v-if="conflictKey === setValueDef.key" class="conflict-banner">
          <span>⚠ {{ conflictMessage }}</span>
          <div class="conflict-actions">
            <UButton size="sm" variant="ghost" @click="reloadAndRetry">Reload &amp; retry</UButton>
            <UButton size="sm" variant="ghost" @click="clearConflict">Cancel</UButton>
          </div>
        </div>
        <div v-if="setValueError" class="modal-error">{{ setValueError }}</div>
      </div>
      <template #footer>
        <UButton variant="ghost" @click="setValueOpen = false">Cancel</UButton>
        <UButton @click="handleSetValue" :loading="setValueSaving">Set value</UButton>
      </template>
    </UModal>
  </div>
</template>

<style scoped>
/* ── Page shell ─────────────────────────────────────────── */
.vars-page {
  display: flex; flex-direction: column; gap: 16px;
  padding: 0 0 40px;
}

/* ── Header ─────────────────────────────────────────────── */
.vars-header {
  display: flex; align-items: center; justify-content: space-between;
}
.vars-header-left { display: flex; align-items: baseline; gap: 10px; }
.vars-title { font-size: 20px; font-weight: 600; color: #e6edf3; margin: 0; }
.vars-count {
  font-size: 12px; color: #8b949e;
  background: #21262d; border-radius: 10px; padding: 1px 8px;
}

/* ── Toolbar ─────────────────────────────────────────────── */
.vars-toolbar {
  display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
}
.toolbar-search { flex: 1; min-width: 180px; }
.toolbar-scope  { width: 140px; }
.toolbar-device { width: 220px; }
.toolbar-toggle { display: flex; align-items: center; gap: 6px; font-size: 13px; color: #8b949e; cursor: pointer; }

/* ── Error / loading ─────────────────────────────────────── */
.vars-error {
  background: #3d1f1f; border: 1px solid #6e2020; border-radius: 6px;
  color: #f85149; font-size: 13px; padding: 10px 14px;
}
.vars-loading { display: flex; flex-direction: column; gap: 6px; }
.skel-row {
  height: 44px; background: linear-gradient(90deg, #21262d 25%, #30363d 50%, #21262d 75%);
  background-size: 200% 100%; border-radius: 6px; animation: shimmer 1.4s infinite;
}
@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }

/* ── Empty state ─────────────────────────────────────────── */
.vars-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; padding: 60px 20px; color: #8b949e; font-size: 14px;
}

.vars-empty-enhanced {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 64px 20px;
  text-align: center;
}

.vars-empty-icon {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: var(--bg-raised);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.vars-empty-text h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.vars-empty-text p {
  font-size: 13px;
  color: var(--text-muted);
  max-width: 320px;
  margin: 0;
}

.vars-empty-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
}

.vars-empty-hint {
  font-size: 12px;
  color: var(--text-muted);
}

.vars-empty-link {
  font-size: 12px;
  color: var(--primary);
  text-decoration: none;
  transition: opacity 0.15s;
}
.vars-empty-link:hover { opacity: 0.8; text-decoration: underline; }

/* ── Table ───────────────────────────────────────────────── */
.vars-table-wrap { overflow-x: auto; }
.vars-table {
  width: 100%; border-collapse: collapse; font-size: 13px;
}
.vars-table th {
  padding: 8px 12px; text-align: left;
  font-size: 11px; font-weight: 500; letter-spacing: 0.05em; text-transform: uppercase;
  color: #8b949e; border-bottom: 1px solid #30363d;
  white-space: nowrap;
}
.vars-table td {
  padding: 10px 12px; border-bottom: 1px solid #21262d; vertical-align: middle;
}
.vars-row { cursor: pointer; transition: background 0.1s; }
.vars-row:hover { background: #161b22; }
.vars-row.row-expanded { background: #161b22; }

/* Col widths */
.col-expand { width: 28px; }
.col-spark  { width: 90px; }
.col-actions{ width: 110px; }
.col-time   { white-space: nowrap; color: #8b949e; font-size: 12px; }
.col-value  { max-width: 200px; overflow: hidden; }

/* Key cell */
.key-wrap   { display: flex; align-items: baseline; gap: 6px; }
.key-name   { font-family: monospace; color: #e6edf3; font-size: 13px; }
.key-cat    { font-size: 10px; color: #58a6ff; background: #58a6ff11; padding: 1px 5px; border-radius: 10px; }
.key-desc   { display: block; font-size: 11px; color: #8b949e; margin-top: 2px; }

/* Value cell */
.value-text { font-family: monospace; font-size: 12px; color: #c9d1d9; }
.value-secret { letter-spacing: 2px; color: #8b949e; }
.value-null { color: #484f58; font-style: italic; }
.reveal-btn {
  margin-left: 6px; font-size: 10px; color: #8b949e;
  background: none; border: none; cursor: pointer; padding: 0 4px;
  border-radius: 3px;
}
.reveal-btn:hover { color: #58a6ff; background: #58a6ff11; }

/* Type unit */
.type-unit { font-size: 11px; color: #8b949e; margin-left: 4px; }

/* Sparkline placeholder */
.spark-na { color: #484f58; font-size: 11px; }

/* Hint badge */
.hint-badge {
  font-size: 10px; color: #8b949e; background: #21262d;
  padding: 2px 6px; border-radius: 10px; font-family: monospace;
}
.hint-none { color: #484f58; font-size: 11px; }

/* Row actions */
.row-actions { display: flex; gap: 2px; align-items: center; }
.danger-btn { color: #f85149 !important; }
.danger-btn:hover { background: #f8514911 !important; }
.row-err-text { font-size: 10px; color: #f85149; margin-top: 3px; }

/* ── Detail panel ─────────────────────────────────────────── */
.detail-row td { padding: 0; background: #0d1117; }
.detail-panel { padding: 16px 20px 20px; border-bottom: 1px solid #30363d; }
.detail-meta {
  display: flex; flex-wrap: wrap; gap: 12px 24px;
  margin-bottom: 16px;
}
.meta-item { display: flex; flex-direction: column; gap: 2px; }
.meta-item.wide { flex: 1; min-width: 200px; }
.meta-label { font-size: 10px; text-transform: uppercase; color: #484f58; letter-spacing: 0.06em; }
.meta-val { font-family: monospace; font-size: 12px; color: #c9d1d9; }

/* ── Modals ───────────────────────────────────────────────── */
.modal-body { padding: 4px 0 8px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px; }
.form-field { display: flex; flex-direction: column; gap: 4px; }
.form-field.wide { grid-column: 1 / -1; }
.form-field label { font-size: 11px; color: #8b949e; }
.form-toggles { display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px; }
.toggle-row { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #c9d1d9; cursor: pointer; }
.toggle-hint { color: #8b949e; font-size: 11px; }
.modal-error {
  margin-top: 10px; background: #3d1f1f; border: 1px solid #6e2020;
  border-radius: 4px; color: #f85149; font-size: 12px; padding: 8px 12px;
}

.edit-readonly-info { display: flex; align-items: center; gap: 6px; margin-bottom: 14px; }
.edit-readonly-note { font-size: 11px; color: #484f58; margin-left: 4px; }

.value-textarea {
  width: 100%; font-family: monospace; font-size: 13px;
  background: #0d1117; border: 1px solid #30363d; border-radius: 4px;
  color: #e6edf3; padding: 8px 10px; resize: vertical;
  box-sizing: border-box;
}
.value-textarea:focus { outline: none; border-color: #58a6ff; }

.conflict-banner {
  background: #332a00; border: 1px solid #6e4f00;
  border-radius: 4px; padding: 10px 12px; margin-top: 10px;
  font-size: 12px; color: #e3b341;
  display: flex; flex-direction: column; gap: 8px;
}
.conflict-actions { display: flex; gap: 6px; }
</style>
