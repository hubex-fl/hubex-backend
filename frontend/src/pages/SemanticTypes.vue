<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import {
  listSemanticTypes,
  createSemanticType,
  updateSemanticType,
  deleteSemanticType,
  getTypeTriggers,
  getTypeConversions,
  type SemanticType,
  type SemanticTypeCreate,
  type TriggerTemplate,
  type UnitConversion,
} from "../lib/semantic-types";
import UCard from "../components/ui/UCard.vue";
import UButton from "../components/ui/UButton.vue";
import UBadge from "../components/ui/UBadge.vue";
import USelect from "../components/ui/USelect.vue";
import UInput from "../components/ui/UInput.vue";
import UModal from "../components/ui/UModal.vue";

/* ------------------------------------------------------------------ */
/* State                                                               */
/* ------------------------------------------------------------------ */
const types = ref<SemanticType[]>([]);
const loading = ref(false);
const error = ref("");

// Filters
const filterBaseType = ref("");
const filterBuiltin = ref<"" | "builtin" | "custom">("");

const baseTypeOptions = [
  { value: "", label: "All base types" },
  { value: "bool", label: "bool" },
  { value: "int", label: "int" },
  { value: "float", label: "float" },
  { value: "string", label: "string" },
  { value: "json", label: "json" },
];

const builtinOptions = [
  { value: "", label: "All types" },
  { value: "builtin", label: "Built-in only" },
  { value: "custom", label: "Custom only" },
];

const filteredTypes = computed(() => {
  let result = types.value;
  if (filterBaseType.value) {
    result = result.filter((t) => t.base_type === filterBaseType.value);
  }
  if (filterBuiltin.value === "builtin") {
    result = result.filter((t) => t.is_builtin);
  } else if (filterBuiltin.value === "custom") {
    result = result.filter((t) => !t.is_builtin);
  }
  return result;
});

// Expanded triggers/conversions
const expandedType = ref<number | null>(null);
const typeTriggers = ref<Record<number, TriggerTemplate[]>>({});
const typeConversions = ref<Record<number, UnitConversion[]>>({});

async function toggleTriggers(id: number) {
  if (expandedType.value === id) {
    expandedType.value = null;
    return;
  }
  expandedType.value = id;
  if (!typeTriggers.value[id]) {
    try {
      const [triggers, conversions] = await Promise.all([
        getTypeTriggers(id),
        getTypeConversions(id),
      ]);
      typeTriggers.value[id] = triggers;
      typeConversions.value[id] = conversions;
    } catch {
      typeTriggers.value[id] = [];
      typeConversions.value[id] = [];
    }
  }
}

/* ------------------------------------------------------------------ */
/* Create / Edit Modal                                                 */
/* ------------------------------------------------------------------ */
const modalOpen = ref(false);
const editingType = ref<SemanticType | null>(null);
const saving = ref(false);

const form = ref<SemanticTypeCreate>({
  name: "",
  display_name: "",
  base_type: "float",
});

const formError = ref("");

const vizOptions = [
  { value: "", label: "None" },
  { value: "sparkline", label: "Sparkline" },
  { value: "line_chart", label: "Line Chart" },
  { value: "gauge", label: "Gauge" },
  { value: "bool", label: "Boolean" },
  { value: "log", label: "Log" },
  { value: "json", label: "JSON" },
  { value: "map", label: "Map" },
  { value: "image", label: "Image" },
];

const formBaseTypeOptions = [
  { value: "bool", label: "bool" },
  { value: "int", label: "int" },
  { value: "float", label: "float" },
  { value: "string", label: "string" },
  { value: "json", label: "json" },
];

const isNumericBase = computed(() =>
  form.value.base_type === "int" || form.value.base_type === "float"
);

function openCreate() {
  editingType.value = null;
  form.value = { name: "", display_name: "", base_type: "float" };
  formError.value = "";
  modalOpen.value = true;
}

function openEdit(t: SemanticType) {
  editingType.value = t;
  form.value = {
    name: t.name,
    display_name: t.display_name,
    base_type: t.base_type,
    unit: t.unit ?? undefined,
    unit_symbol: t.unit_symbol ?? undefined,
    min_value: t.min_value ?? undefined,
    max_value: t.max_value ?? undefined,
    default_viz_type: t.default_viz_type ?? undefined,
    icon: t.icon ?? undefined,
    color: t.color ?? undefined,
  };
  formError.value = "";
  modalOpen.value = true;
}

async function saveType() {
  formError.value = "";
  if (!form.value.name || !form.value.display_name) {
    formError.value = "Name and Display Name are required.";
    return;
  }
  saving.value = true;
  try {
    // Clean up empty optional fields
    const payload: Record<string, any> = { ...form.value };
    for (const key of Object.keys(payload)) {
      if (payload[key] === "" || payload[key] === undefined) {
        delete payload[key];
      }
    }
    // Ensure required fields remain
    payload.name = form.value.name;
    payload.display_name = form.value.display_name;
    payload.base_type = form.value.base_type;

    if (editingType.value) {
      await updateSemanticType(editingType.value.id, payload as Partial<SemanticTypeCreate>);
    } else {
      await createSemanticType(payload as SemanticTypeCreate);
    }
    modalOpen.value = false;
    await fetchTypes();
  } catch (e: any) {
    formError.value = e?.message || "Save failed";
  } finally {
    saving.value = false;
  }
}

/* ------------------------------------------------------------------ */
/* Delete                                                              */
/* ------------------------------------------------------------------ */
const deleteTarget = ref<SemanticType | null>(null);
const deleteModalOpen = ref(false);
const deleting = ref(false);

function confirmDelete(t: SemanticType) {
  deleteTarget.value = t;
  deleteModalOpen.value = true;
}

async function doDelete() {
  if (!deleteTarget.value) return;
  deleting.value = true;
  try {
    await deleteSemanticType(deleteTarget.value.id);
    deleteModalOpen.value = false;
    deleteTarget.value = null;
    await fetchTypes();
  } catch (e: any) {
    error.value = e?.message || "Delete failed";
  } finally {
    deleting.value = false;
  }
}

/* ------------------------------------------------------------------ */
/* Fetch                                                               */
/* ------------------------------------------------------------------ */
async function fetchTypes() {
  loading.value = true;
  error.value = "";
  try {
    types.value = await listSemanticTypes();
  } catch (e: any) {
    error.value = e?.message || "Failed to load types";
  } finally {
    loading.value = false;
  }
}

onMounted(fetchTypes);
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold text-[var(--text-primary)]">Semantic Types</h2>
        <p class="text-sm text-[var(--text-muted)] mt-0.5">
          Manage data types that define how variables are interpreted, validated, and visualized.
        </p>
      </div>
      <UButton @click="openCreate">Create Custom Type</UButton>
    </div>

    <!-- Filter bar -->
    <div class="flex flex-wrap items-end gap-3">
      <USelect
        v-model="filterBaseType"
        label="Base Type"
        :options="baseTypeOptions"
      />
      <USelect
        v-model="filterBuiltin"
        label="Origin"
        :options="builtinOptions"
      />
      <span class="text-xs text-[var(--text-muted)] self-end pb-2">
        {{ filteredTypes.length }} type{{ filteredTypes.length === 1 ? '' : 's' }}
      </span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-sm text-[var(--text-muted)]">Loading types...</div>

    <!-- Error -->
    <div v-if="error" class="text-sm text-[var(--status-bad)]">{{ error }}</div>

    <!-- Type Cards Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <UCard
        v-for="t in filteredTypes"
        :key="t.id"
        padding="md"
        class="relative group"
      >
        <!-- Icon + Name -->
        <div class="flex items-center gap-3 mb-3">
          <span class="text-2xl leading-none">{{ t.icon || '📦' }}</span>
          <div class="min-w-0 flex-1">
            <h3 class="font-semibold text-[var(--text-primary)] truncate">{{ t.display_name }}</h3>
            <p class="text-xs text-[var(--text-muted)] truncate">{{ t.name }} &middot; {{ t.base_type }}</p>
          </div>
          <UBadge v-if="t.is_builtin" status="info" class="shrink-0">Built-in</UBadge>
          <UBadge v-else status="neutral" class="shrink-0">Custom</UBadge>
        </div>

        <!-- Properties -->
        <div class="grid grid-cols-2 gap-2 text-sm">
          <div v-if="t.unit">
            <span class="text-[var(--text-muted)]">Unit:</span>
            <span class="text-[var(--text-primary)] ml-1">{{ t.unit_symbol || t.unit }}</span>
          </div>
          <div v-if="t.min_value != null || t.max_value != null">
            <span class="text-[var(--text-muted)]">Range:</span>
            <span class="text-[var(--text-primary)] ml-1">
              {{ t.min_value ?? '\u2212\u221E' }} \u2013 {{ t.max_value ?? '\u221E' }}
            </span>
          </div>
          <div v-if="t.default_viz_type">
            <span class="text-[var(--text-muted)]">Viz:</span>
            <span class="text-[var(--text-primary)] ml-1">{{ t.default_viz_type }}</span>
          </div>
          <div v-if="t.color" class="flex items-center">
            <span class="text-[var(--text-muted)]">Color:</span>
            <span
              class="inline-block w-3 h-3 rounded-full ml-1 border border-[var(--border)]"
              :style="{ backgroundColor: t.color }"
            />
          </div>
        </div>

        <!-- Trigger toggle + Edit/Delete -->
        <div class="mt-3 pt-3 border-t border-[var(--border)] flex items-center justify-between">
          <button
            @click="toggleTriggers(t.id)"
            class="text-xs text-[var(--primary)] hover:underline"
          >
            {{ expandedType === t.id ? 'Hide' : 'Show' }} Triggers &amp; Conversions
          </button>
          <div v-if="!t.is_builtin" class="flex gap-2">
            <button
              @click="openEdit(t)"
              class="text-xs text-[var(--text-muted)] hover:text-[var(--primary)] transition-colors"
            >Edit</button>
            <button
              @click="confirmDelete(t)"
              class="text-xs text-[var(--text-muted)] hover:text-[var(--status-bad)] transition-colors"
            >Delete</button>
          </div>
        </div>

        <!-- Expanded: Triggers + Conversions -->
        <div v-if="expandedType === t.id" class="mt-3 space-y-1">
          <div
            v-if="!typeTriggers[t.id]?.length && !typeConversions[t.id]?.length"
            class="text-xs text-[var(--text-muted)] italic"
          >
            No triggers or conversions defined.
          </div>
          <div
            v-for="tr in typeTriggers[t.id]"
            :key="'tr-' + tr.id"
            class="flex items-center gap-2 text-sm px-2 py-1 rounded bg-[var(--bg-raised)]"
          >
            <span>{{ tr.icon || '\u26A1' }}</span>
            <span class="text-[var(--text-primary)]">{{ tr.display_name }}</span>
            <span class="text-[var(--text-muted)] text-xs ml-auto font-mono">{{ tr.trigger_name }}</span>
          </div>
          <div
            v-for="c in typeConversions[t.id]"
            :key="'cv-' + c.id"
            class="flex items-center gap-2 text-sm px-2 py-1 rounded bg-[var(--bg-raised)]"
          >
            <span>\uD83D\uDD04</span>
            <span class="text-[var(--text-primary)]">{{ c.from_unit }} \u2192 {{ c.to_unit }}</span>
            <span class="text-[var(--text-muted)] text-xs ml-auto font-mono">{{ c.formula }}</span>
          </div>
        </div>
      </UCard>
    </div>

    <!-- Empty state -->
    <div
      v-if="!loading && !error && filteredTypes.length === 0"
      class="text-center py-12 text-[var(--text-muted)]"
    >
      <p class="text-lg mb-1">No types found</p>
      <p class="text-sm">Try adjusting the filters or create a custom type.</p>
    </div>

    <!-- Create / Edit Modal -->
    <UModal :open="modalOpen" title="editingType ? 'Edit Type: ' + editingType.display_name : 'Create Custom Type'" @close="modalOpen = false">
      <template #header>
        <h2 class="text-base font-semibold text-[var(--text-primary)]">
          {{ editingType ? 'Edit Type' : 'Create Custom Type' }}
        </h2>
      </template>

      <div class="space-y-4">
        <div v-if="formError" class="text-sm text-[var(--status-bad)]">{{ formError }}</div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <UInput
            v-model="form.name"
            label="Name"
            placeholder="e.g. temperature_celsius"
            :disabled="!!editingType"
          />
          <UInput
            v-model="form.display_name"
            label="Display Name"
            placeholder="e.g. Temperature (Celsius)"
          />
        </div>

        <USelect
          v-model="form.base_type"
          label="Base Type"
          :options="formBaseTypeOptions"
          :disabled="!!editingType"
        />

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <UInput v-model="form.unit" label="Unit" placeholder="e.g. celsius" />
          <UInput v-model="form.unit_symbol" label="Unit Symbol" placeholder="e.g. \u00B0C" />
        </div>

        <div v-if="isNumericBase" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <UInput v-model="form.min_value as any" label="Min Value" type="number" placeholder="No minimum" />
          <UInput v-model="form.max_value as any" label="Max Value" type="number" placeholder="No maximum" />
        </div>

        <USelect
          v-model="form.default_viz_type as any"
          label="Default Visualization"
          :options="vizOptions"
        />

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <UInput v-model="form.icon" label="Icon (emoji)" placeholder="e.g. \uD83C\uDF21\uFE0F" />
          <UInput v-model="form.color" label="Color (hex)" placeholder="e.g. #FF6B35" />
        </div>
      </div>

      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton variant="ghost" @click="modalOpen = false">Cancel</UButton>
          <UButton :loading="saving" @click="saveType">
            {{ editingType ? 'Save Changes' : 'Create Type' }}
          </UButton>
        </div>
      </template>
    </UModal>

    <!-- Delete Confirmation Modal -->
    <UModal :open="deleteModalOpen" title="Delete Type" @close="deleteModalOpen = false">
      <p class="text-sm text-[var(--text-secondary)]">
        Are you sure you want to delete
        <strong class="text-[var(--text-primary)]">{{ deleteTarget?.display_name }}</strong>?
        This action cannot be undone.
      </p>
      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton variant="ghost" @click="deleteModalOpen = false">Cancel</UButton>
          <UButton variant="danger" :loading="deleting" @click="doDelete">Delete</UButton>
        </div>
      </template>
    </UModal>
  </div>
</template>
