<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { mapErrorToUserText, parseApiError } from "../lib/errors";
import {
  VariableDefinition,
  VariableScope,
  VariableValue,
  VariableDefinitionInput,
  VariableValueInput,
  listDefinitions,
  createDefinition,
  getValue,
  putValue,
  getDeviceVariables,
} from "../lib/variables";

type ScopeFilter = "all" | VariableScope;

const definitions = ref<VariableDefinition[]>([]);
const valuesByKey = ref<Record<string, VariableValue>>({});
const error = ref<string | null>(null);
const loading = ref(false);

const search = ref("");
const scopeFilter = ref<ScopeFilter>("all");
const deviceUid = ref("");
const showSecrets = ref(true);

const editorOpen = ref(false);
const editorMode = ref<"create" | "edit">("create");
const editorKey = ref("");
const editorScope = ref<VariableScope>("global");
const editorDeviceUid = ref("");
const editorValueType = ref<VariableDefinitionInput["valueType"]>("string");
const editorDefaultValue = ref("");
const editorValue = ref("");
const editorIsSecret = ref(false);
const editorIsReadonly = ref(false);
const editorExpectedVersion = ref<number | null>(null);

const isDeviceScope = computed(() => editorScope.value === "device");

const filteredRows = computed(() => {
  const term = search.value.trim().toLowerCase();
  const scopedDefs = definitions.value.filter((d) => {
    if (scopeFilter.value === "all") return true;
    return d.scope === scopeFilter.value;
  });
  return scopedDefs.filter((d) => {
    if (!showSecrets.value && d.is_secret) return false;
    if (!term) return true;
    return d.key.toLowerCase().includes(term);
  });
});

function formatApiError(err: any, fallback: string) {
  const info = parseApiError(err);
  const mapped = mapErrorToUserText(info, fallback);
  const statusLabel = info.httpStatus ? `HTTP ${info.httpStatus}` : "HTTP ?";
  const detailText = (info.message || "").slice(0, 200);
  const codeText = info.code ? ` ${info.code}` : "";
  const suffix = detailText ? `${statusLabel}: ${detailText}` : statusLabel;
  if (mapped !== fallback) return `${mapped} (${suffix}${codeText})`;
  return `${fallback} (${suffix}${codeText})`;
}

function parseValueInput(valueType: VariableDefinitionInput["valueType"], raw: string) {
  if (valueType === "string") return raw;
  if (valueType === "int") return raw === "" ? null : Number.parseInt(raw, 10);
  if (valueType === "float") return raw === "" ? null : Number.parseFloat(raw);
  if (valueType === "bool") return raw.trim().toLowerCase() === "true";
  if (valueType === "json") {
    try {
      return JSON.parse(raw);
    } catch {
      return raw;
    }
  }
  return raw;
}

function openCreate() {
  editorOpen.value = true;
  editorMode.value = "create";
  editorKey.value = "";
  editorScope.value = "global";
  editorDeviceUid.value = "";
  editorValueType.value = "string";
  editorDefaultValue.value = "";
  editorValue.value = "";
  editorIsSecret.value = false;
  editorIsReadonly.value = false;
  editorExpectedVersion.value = null;
}

function openEdit(definition: VariableDefinition, current?: VariableValue) {
  editorOpen.value = true;
  editorMode.value = "edit";
  editorKey.value = definition.key;
  editorScope.value = definition.scope;
  editorDeviceUid.value = deviceUid.value.trim();
  editorValueType.value = definition.value_type;
  editorDefaultValue.value = definition.default_value ? JSON.stringify(definition.default_value) : "";
  editorValue.value = current?.value !== undefined ? JSON.stringify(current.value) : "";
  editorIsSecret.value = definition.is_secret;
  editorIsReadonly.value = definition.is_readonly;
  editorExpectedVersion.value = current?.version ?? null;
}

async function loadDefinitionsAndValues() {
  error.value = null;
  loading.value = true;
  try {
    const defs = await listDefinitions(scopeFilter.value === "all" ? undefined : scopeFilter.value);
    definitions.value = defs;

    const values: Record<string, VariableValue> = {};
    if (deviceUid.value.trim()) {
      const vars = await getDeviceVariables(deviceUid.value.trim());
      const combined = [...vars.globals, ...vars.device];
      for (const item of combined) {
        values[item.key] = item;
      }
    } else {
      await Promise.all(
        defs
          .filter((d) => d.scope === "global")
          .map(async (d) => {
            const v = await getValue({ key: d.key, scope: "global" });
            values[d.key] = v;
          })
      );
    }
    valuesByKey.value = values;
  } catch (e: any) {
    error.value = formatApiError(e, "Failed to load variables");
  } finally {
    loading.value = false;
  }
}

async function handleSave() {
  error.value = null;
  try {
    if (editorMode.value === "create") {
      const defInput: VariableDefinitionInput = {
        key: editorKey.value.trim(),
        scope: editorScope.value,
        valueType: editorValueType.value,
        defaultValue: editorDefaultValue.value
          ? parseValueInput(editorValueType.value, editorDefaultValue.value)
          : null,
        isSecret: editorIsSecret.value,
        isReadonly: editorIsReadonly.value,
      };
      await createDefinition(defInput);
      if (editorValue.value) {
        const valueInput: VariableValueInput = {
          key: editorKey.value.trim(),
          scope: editorScope.value,
          deviceUid: editorScope.value === "device" ? editorDeviceUid.value.trim() : undefined,
          value: parseValueInput(editorValueType.value, editorValue.value),
        };
        await putValue(valueInput);
      }
    } else {
      const valueInput: VariableValueInput = {
        key: editorKey.value.trim(),
        scope: editorScope.value,
        deviceUid: editorScope.value === "device" ? editorDeviceUid.value.trim() : undefined,
        value: parseValueInput(editorValueType.value, editorValue.value),
        expectedVersion: editorExpectedVersion.value ?? undefined,
      };
      await putValue(valueInput);
    }
    editorOpen.value = false;
    await loadDefinitionsAndValues();
  } catch (e: any) {
    error.value = formatApiError(e, "Failed to save variable");
  }
}

async function handleDelete(definition: VariableDefinition, current?: VariableValue) {
  if (!confirm("Clear value? This will revert to default if set.")) return;
  error.value = null;
  try {
    const valueInput: VariableValueInput = {
      key: definition.key,
      scope: definition.scope,
      deviceUid: definition.scope === "device" ? deviceUid.value.trim() : undefined,
      value: null,
      expectedVersion: current?.version ?? undefined,
    };
    await putValue(valueInput);
    await loadDefinitionsAndValues();
  } catch (e: any) {
    error.value = formatApiError(e, "Failed to clear variable");
  }
}

function valueDisplay(definition: VariableDefinition, value?: VariableValue) {
  if (definition.is_secret) return "***";
  if (!value) return "-";
  if (value.value === null || value.value === undefined) return "-";
  if (typeof value.value === "string") return value.value;
  return JSON.stringify(value.value);
}

function updatedDisplay(value?: VariableValue) {
  if (!value?.updated_at) return "-";
  try { return new Date(value.updated_at).toLocaleString(); } catch { return value.updated_at; }
}

watch([scopeFilter, deviceUid], () => {
  loadDefinitionsAndValues();
});

onMounted(() => {
  loadDefinitionsAndValues();
});
</script>

<template>
  <div class="card">
    <div class="card-header-row">
      <h2>Variables</h2>
      <button class="btn" @click="openCreate">Add variable</button>
    </div>

    <div class="toolbar">
      <input v-model="search" class="input" placeholder="Search key" />
      <select v-model="scopeFilter" class="input">
        <option value="all">all scopes</option>
        <option value="global">global</option>
        <option value="device">device</option>
      </select>
      <input
        v-model="deviceUid"
        class="input"
        placeholder="device UID (optional)"
      />
      <label class="toggle">
        <input type="checkbox" v-model="showSecrets" />
        show secrets
      </label>
    </div>

    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="loading">Loading...</div>

    <table v-if="filteredRows.length" class="table">
      <thead>
        <tr>
          <th>Scope</th>
          <th>Device UID</th>
          <th>Key</th>
          <th>Type</th>
          <th>Value</th>
          <th>Version</th>
          <th>Updated</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="def in filteredRows" :key="def.key">
          <td>{{ def.scope }}</td>
          <td>{{ def.scope === "device" ? (deviceUid || "-") : "-" }}</td>
          <td>{{ def.key }}</td>
          <td>{{ def.value_type }}</td>
          <td>{{ valueDisplay(def, valuesByKey[def.key]) }}</td>
          <td>{{ valuesByKey[def.key]?.version ?? "-" }}</td>
          <td>{{ updatedDisplay(valuesByKey[def.key]) }}</td>
          <td>
            <button class="btn secondary" @click="openEdit(def, valuesByKey[def.key])">
              Edit
            </button>
            <button class="btn secondary" @click="handleDelete(def, valuesByKey[def.key])">
              Delete
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else-if="!loading">No variables found.</div>

    <div v-if="editorOpen" class="modal">
      <div class="modal-card">
        <div class="card-header-row">
          <h3>{{ editorMode === "create" ? "Add variable" : "Edit variable" }}</h3>
          <button class="btn secondary" @click="editorOpen = false">Close</button>
        </div>
        <div class="info-grid">
          <div class="info-item">
            <div class="info-label">Key</div>
            <input v-model="editorKey" class="input" :disabled="editorMode === 'edit'" />
          </div>
          <div class="info-item">
            <div class="info-label">Scope</div>
            <select v-model="editorScope" class="input" :disabled="editorMode === 'edit'">
              <option value="global">global</option>
              <option value="device">device</option>
            </select>
          </div>
          <div class="info-item" v-if="isDeviceScope">
            <div class="info-label">Device UID</div>
            <input v-model="editorDeviceUid" class="input" />
          </div>
          <div class="info-item">
            <div class="info-label">Value type</div>
            <select v-model="editorValueType" class="input" :disabled="editorMode === 'edit'">
              <option value="string">string</option>
              <option value="int">int</option>
              <option value="float">float</option>
              <option value="bool">bool</option>
              <option value="json">json</option>
            </select>
          </div>
          <div class="info-item">
            <div class="info-label">Default value</div>
            <input v-model="editorDefaultValue" class="input" :disabled="editorMode === 'edit'" />
          </div>
          <div class="info-item">
            <div class="info-label">Value</div>
            <textarea v-model="editorValue" class="input" rows="3"></textarea>
          </div>
        </div>
        <div class="toolbar" style="margin-top: 12px;">
          <label class="toggle">
            <input type="checkbox" v-model="editorIsSecret" :disabled="editorMode === 'edit'" />
            secret
          </label>
          <label class="toggle">
            <input type="checkbox" v-model="editorIsReadonly" :disabled="editorMode === 'edit'" />
            readonly
          </label>
          <button class="btn" @click="handleSave">Save</button>
        </div>
      </div>
    </div>
  </div>
</template>
