<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";
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
import UInfoTooltip from "../components/ui/UInfoTooltip.vue";

/* ------------------------------------------------------------------ */
/* State                                                               */
/* ------------------------------------------------------------------ */
const { t, te, tm, rt } = useI18n();

/**
 * Sprint 8 R1-F27 — client-side i18n lookup for backend-seeded
 * built-in semantic type display names. Custom user types fall
 * back to the raw backend `display_name`.
 */
function localizedTypeName(st: SemanticType): string {
  if (!st.is_builtin) return st.display_name;
  const key = `pages.semanticTypes.seedNames.${st.name}`;
  return te(key) ? t(key) : st.display_name;
}

const types = ref<SemanticType[]>([]);
const loading = ref(false);
const error = ref("");

// Filters
const filterBaseType = ref("");
const filterBuiltin = ref<"" | "builtin" | "custom">("");

const baseTypeOptions = computed(() => [
  { value: "", label: t('pages.semanticTypes.allBaseTypes') },
  { value: "bool", label: "bool" },
  { value: "int", label: "int" },
  { value: "float", label: "float" },
  { value: "string", label: "string" },
  { value: "json", label: "json" },
]);

const builtinOptions = computed(() => [
  { value: "", label: t('pages.semanticTypes.allTypes') },
  { value: "builtin", label: t('pages.semanticTypes.builtinOnly') },
  { value: "custom", label: t('pages.semanticTypes.customOnly') },
]);

const filteredTypes = computed(() => {
  let result = types.value;
  if (filterBaseType.value) {
    result = result.filter((st) => st.base_type === filterBaseType.value);
  }
  if (filterBuiltin.value === "builtin") {
    result = result.filter((st) => st.is_builtin);
  } else if (filterBuiltin.value === "custom") {
    result = result.filter((st) => !st.is_builtin);
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

const vizOptions = computed(() => [
  { value: "", label: t('pages.semanticTypes.vizNone') },
  { value: "sparkline", label: t('pages.semanticTypes.vizSparkline') },
  { value: "line_chart", label: t('pages.semanticTypes.vizLineChart') },
  { value: "gauge", label: t('pages.semanticTypes.vizGauge') },
  { value: "bool", label: t('pages.semanticTypes.vizBoolean') },
  { value: "log", label: t('pages.semanticTypes.vizLog') },
  { value: "json", label: t('pages.semanticTypes.vizJson') },
  { value: "map", label: t('pages.semanticTypes.vizMap') },
  { value: "image", label: t('pages.semanticTypes.vizImage') },
]);

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

function openEdit(st: SemanticType) {
  editingType.value = st;
  form.value = {
    name: st.name,
    display_name: st.display_name,
    base_type: st.base_type,
    unit: st.unit ?? undefined,
    unit_symbol: st.unit_symbol ?? undefined,
    min_value: st.min_value ?? undefined,
    max_value: st.max_value ?? undefined,
    default_viz_type: st.default_viz_type ?? undefined,
    icon: st.icon ?? undefined,
    color: st.color ?? undefined,
  };
  formError.value = "";
  modalOpen.value = true;
}

async function saveType() {
  formError.value = "";
  if (!form.value.name || !form.value.display_name) {
    formError.value = t('pages.semanticTypes.formRequiredError');
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
    formError.value = e?.message || t('pages.semanticTypes.saveFailed');
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

function confirmDelete(st: SemanticType) {
  deleteTarget.value = st;
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
    error.value = e?.message || t('pages.semanticTypes.deleteFailed');
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
    error.value = e?.message || t('pages.semanticTypes.loadError');
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
        <div class="flex items-center">
          <h2 class="text-lg font-semibold text-[var(--text-primary)]">{{ t('pages.semanticTypes.title') }}</h2>
          <UInfoTooltip
            :title="t('infoTooltips.semanticTypes.title')"
            :items="tm('infoTooltips.semanticTypes.items').map((i: any) => rt(i))"
          />
        </div>
        <p class="text-sm text-[var(--text-muted)] mt-0.5">
          {{ t('pages.semanticTypes.subtitle') }}
        </p>
      </div>
      <UButton @click="openCreate">{{ t('pages.semanticTypes.createCustomType') }}</UButton>
    </div>

    <!-- Filter bar -->
    <div class="flex flex-wrap items-end gap-3">
      <USelect
        v-model="filterBaseType"
        :label="t('pages.semanticTypes.baseTypeLabel')"
        :options="baseTypeOptions"
      />
      <USelect
        v-model="filterBuiltin"
        :label="t('pages.semanticTypes.originLabel')"
        :options="builtinOptions"
      />
      <span class="text-xs text-[var(--text-muted)] self-end pb-2">
        {{ t('pages.semanticTypes.typeCount', { count: filteredTypes.length }, filteredTypes.length) }}
      </span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-sm text-[var(--text-muted)]">{{ t('pages.semanticTypes.loading') }}</div>

    <!-- Error -->
    <div v-if="error" class="text-sm text-[var(--status-bad)]">{{ error }}</div>

    <!-- Type Cards Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <UCard
        v-for="st in filteredTypes"
        :key="st.id"
        padding="md"
        class="relative group"
      >
        <!-- Icon + Name -->
        <div class="flex items-center gap-3 mb-3">
          <span class="text-2xl leading-none">{{ st.icon || '📦' }}</span>
          <div class="min-w-0 flex-1">
            <h3 class="font-semibold text-[var(--text-primary)] truncate">{{ localizedTypeName(st) }}</h3>
            <p class="text-xs text-[var(--text-muted)] truncate">{{ st.name }} &middot; {{ st.base_type }}</p>
          </div>
          <UBadge v-if="st.is_builtin" status="info" class="shrink-0">{{ t('pages.semanticTypes.builtin') }}</UBadge>
          <UBadge v-else status="neutral" class="shrink-0">{{ t('pages.semanticTypes.custom') }}</UBadge>
        </div>

        <!-- Properties -->
        <div class="grid grid-cols-2 gap-2 text-sm">
          <div v-if="st.unit">
            <span class="text-[var(--text-muted)]">{{ t('pages.semanticTypes.fieldUnit') }}</span>
            <span class="text-[var(--text-primary)] ml-1">{{ st.unit_symbol || st.unit }}</span>
          </div>
          <div v-if="st.min_value != null || st.max_value != null">
            <span class="text-[var(--text-muted)]">{{ t('pages.semanticTypes.fieldRange') }}</span>
            <span class="text-[var(--text-primary)] ml-1">
              {{ st.min_value ?? '\u2212\u221E' }} \u2013 {{ st.max_value ?? '\u221E' }}
            </span>
          </div>
          <div v-if="st.default_viz_type">
            <span class="text-[var(--text-muted)]">{{ t('pages.semanticTypes.fieldViz') }}</span>
            <span class="text-[var(--text-primary)] ml-1">{{ st.default_viz_type }}</span>
          </div>
          <div v-if="st.color" class="flex items-center">
            <span class="text-[var(--text-muted)]">{{ t('pages.semanticTypes.fieldColor') }}</span>
            <span
              class="inline-block w-3 h-3 rounded-full ml-1 border border-[var(--border)]"
              :style="{ backgroundColor: st.color }"
            />
          </div>
        </div>

        <!-- Trigger toggle + Edit/Delete -->
        <div class="mt-3 pt-3 border-t border-[var(--border)] flex items-center justify-between">
          <button
            @click="toggleTriggers(st.id)"
            class="text-xs text-[var(--primary)] hover:underline"
          >
            {{ expandedType === st.id ? t('pages.semanticTypes.hideTriggers') : t('pages.semanticTypes.showTriggers') }}
          </button>
          <div v-if="!st.is_builtin" class="flex gap-2">
            <button
              @click="openEdit(st)"
              class="text-xs text-[var(--text-muted)] hover:text-[var(--primary)] transition-colors"
            >{{ t('pages.semanticTypes.edit') }}</button>
            <button
              @click="confirmDelete(st)"
              class="text-xs text-[var(--text-muted)] hover:text-[var(--status-bad)] transition-colors"
            >{{ t('pages.semanticTypes.delete') }}</button>
          </div>
        </div>

        <!-- Expanded: Triggers + Conversions -->
        <div v-if="expandedType === st.id" class="mt-3 space-y-1">
          <div
            v-if="!typeTriggers[st.id]?.length && !typeConversions[st.id]?.length"
            class="text-xs text-[var(--text-muted)] italic"
          >
            {{ t('pages.semanticTypes.noTriggersOrConversions') }}
          </div>
          <div
            v-for="tr in typeTriggers[st.id]"
            :key="'tr-' + tr.id"
            class="flex items-center gap-2 text-sm px-2 py-1 rounded bg-[var(--bg-raised)]"
          >
            <span>{{ tr.icon || '\u26A1' }}</span>
            <span class="text-[var(--text-primary)]">{{ tr.display_name }}</span>
            <span class="text-[var(--text-muted)] text-xs ml-auto font-mono">{{ tr.trigger_name }}</span>
          </div>
          <div
            v-for="c in typeConversions[st.id]"
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
      <p class="text-lg mb-1">{{ t('pages.semanticTypes.emptyTitle') }}</p>
      <p class="text-sm">{{ t('pages.semanticTypes.emptyHint') }}</p>
    </div>

    <!-- Create / Edit Modal -->
    <UModal :open="modalOpen" :title="editingType ? t('pages.semanticTypes.modalEditTitle') + ': ' + localizedTypeName(editingType) : t('pages.semanticTypes.modalCreateTitle')" @close="modalOpen = false">
      <template #header>
        <h2 class="text-base font-semibold text-[var(--text-primary)]">
          {{ editingType ? t('pages.semanticTypes.modalEditTitle') : t('pages.semanticTypes.modalCreateTitle') }}
        </h2>
      </template>

      <div class="space-y-4">
        <div v-if="formError" class="text-sm text-[var(--status-bad)]">{{ formError }}</div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <UInput
            v-model="form.name"
            :label="t('pages.semanticTypes.formName')"
            :placeholder="t('pages.semanticTypes.formNamePlaceholder')"
            :disabled="!!editingType"
          />
          <UInput
            v-model="form.display_name"
            :label="t('pages.semanticTypes.formDisplayName')"
            :placeholder="t('pages.semanticTypes.formDisplayNamePlaceholder')"
          />
        </div>

        <USelect
          v-model="form.base_type"
          :label="t('pages.semanticTypes.formBaseType')"
          :options="formBaseTypeOptions"
          :disabled="!!editingType"
        />

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <UInput v-model="form.unit" :label="t('pages.semanticTypes.formUnit')" :placeholder="t('pages.semanticTypes.formUnitPlaceholder')" />
          <UInput v-model="form.unit_symbol" :label="t('pages.semanticTypes.formUnitSymbol')" :placeholder="t('pages.semanticTypes.formUnitSymbolPlaceholder')" />
        </div>

        <div v-if="isNumericBase" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <UInput v-model="form.min_value as any" :label="t('pages.semanticTypes.formMinValue')" type="number" :placeholder="t('pages.semanticTypes.formMinValuePlaceholder')" />
          <UInput v-model="form.max_value as any" :label="t('pages.semanticTypes.formMaxValue')" type="number" :placeholder="t('pages.semanticTypes.formMaxValuePlaceholder')" />
        </div>

        <USelect
          v-model="form.default_viz_type as any"
          :label="t('pages.semanticTypes.formDefaultViz')"
          :options="vizOptions"
        />

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <UInput v-model="form.icon" :label="t('pages.semanticTypes.formIcon')" :placeholder="t('pages.semanticTypes.formIconPlaceholder')" />
          <UInput v-model="form.color" :label="t('pages.semanticTypes.formColor')" :placeholder="t('pages.semanticTypes.formColorPlaceholder')" />
        </div>
      </div>

      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton variant="ghost" @click="modalOpen = false">{{ t('common.cancel') }}</UButton>
          <UButton :loading="saving" @click="saveType">
            {{ editingType ? t('pages.semanticTypes.saveChanges') : t('pages.semanticTypes.createType') }}
          </UButton>
        </div>
      </template>
    </UModal>

    <!-- Delete Confirmation Modal -->
    <UModal :open="deleteModalOpen" :title="t('pages.semanticTypes.deleteModalTitle')" @close="deleteModalOpen = false">
      <p class="text-sm text-[var(--text-secondary)]">
        {{ t('pages.semanticTypes.deleteConfirmPrefix') }}
        <strong class="text-[var(--text-primary)]">{{ deleteTarget ? localizedTypeName(deleteTarget) : '' }}</strong>{{ t('pages.semanticTypes.deleteConfirmSuffix') }}
      </p>
      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton variant="ghost" @click="deleteModalOpen = false">{{ t('common.cancel') }}</UButton>
          <UButton variant="danger" :loading="deleting" @click="doDelete">{{ t('common.delete') }}</UButton>
        </div>
      </template>
    </UModal>
  </div>
</template>
