<script setup lang="ts">
/**
 * UEntitySelect — Searchable dropdown for selecting entities (devices, variables, etc.)
 *
 * Replaces ALL manual ID/UID/Key input fields across the app.
 * Fetches options from the API and provides a filterable dropdown.
 */
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../../lib/api";

const { t } = useI18n();

export interface EntityOption {
  value: string;
  label: string;
  sublabel?: string;
}

const props = defineProps<{
  modelValue?: string;
  /** Entity type to fetch: 'device' | 'variable' | 'entity' | 'stream' */
  entityType: "device" | "variable" | "entity" | "stream";
  label?: string;
  placeholder?: string;
  optional?: boolean;
  disabled?: boolean;
  /** Pre-loaded options (skip API fetch) */
  staticOptions?: EntityOption[];
  /** When entityType is 'variable', filter to variables belonging to this device */
  deviceUid?: string;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", v: string): void;
}>();

const query = ref("");
const open = ref(false);
const options = ref<EntityOption[]>([]);
const loading = ref(false);
const wrapperRef = ref<HTMLDivElement | null>(null);
const highlightIndex = ref(0);

const displayValue = computed(() => {
  if (!props.modelValue) return "";
  const opt = options.value.find((o) => o.value === props.modelValue);
  return opt ? opt.label : props.modelValue;
});

const filtered = computed(() => {
  const q = query.value.toLowerCase().trim();
  if (!q) return options.value;
  return options.value.filter(
    (o) =>
      o.label.toLowerCase().includes(q) ||
      o.value.toLowerCase().includes(q) ||
      (o.sublabel || "").toLowerCase().includes(q)
  );
});

async function fetchOptions() {
  if (props.staticOptions) {
    options.value = props.staticOptions;
    return;
  }
  loading.value = true;
  try {
    if (props.entityType === "device") {
      const devices = await apiFetch<Array<{ id: number; device_uid: string; name: string | null; device_type: string }>>("/api/v1/devices");
      options.value = devices.map((d) => ({
        value: String(d.device_uid),
        label: d.name || d.device_uid,
        sublabel: `${d.device_type} · ${d.device_uid}`,
      }));
    } else if (props.entityType === "variable") {
      if (props.deviceUid) {
        // Fetch variables scoped to a specific device (globals + device-scoped)
        const res = await apiFetch<{ device_uid: string; globals: Array<{ key: string; scope: string }>; device: Array<{ key: string; scope: string }> }>(`/api/v1/variables/device/${encodeURIComponent(props.deviceUid)}`);
        const all = [
          ...res.globals.map((v) => ({ value: v.key, label: v.key, sublabel: `global` })),
          ...res.device.map((v) => ({ value: v.key, label: v.key, sublabel: `device · ${props.deviceUid}` })),
        ];
        options.value = all;
      } else {
        const vars = await apiFetch<Array<{ key: string; scope: string; value_type: string; description?: string }>>("/api/v1/variables/definitions");
        options.value = vars.map((v) => ({
          value: v.key,
          label: v.key,
          sublabel: `${v.scope} · ${v.value_type}${v.description ? " · " + v.description : ""}`,
        }));
      }
    } else if (props.entityType === "entity") {
      const entities = await apiFetch<Array<{ entity_id: string; name?: string; type?: string }>>("/api/v1/entities");
      options.value = entities.map((e) => ({
        value: e.entity_id,
        label: e.name || e.entity_id,
        sublabel: e.type || "",
      }));
    } else if (props.entityType === "stream") {
      options.value = [
        { value: "system", label: "system", sublabel: "System events" },
        { value: "tenant.system", label: "tenant.system", sublabel: "Tenant system events" },
        { value: "tenant.telemetry", label: "tenant.telemetry", sublabel: "Telemetry data" },
        { value: "tenant.alerts", label: "tenant.alerts", sublabel: "Alert events" },
        { value: "tenant.automations", label: "tenant.automations", sublabel: "Automation events" },
      ];
    }
  } catch {
    // Fallback to empty
  } finally {
    loading.value = false;
  }
}

function select(opt: EntityOption) {
  emit("update:modelValue", opt.value);
  query.value = "";
  open.value = false;
}

function clear() {
  emit("update:modelValue", "");
  query.value = "";
}

function handleFocus() {
  open.value = true;
  highlightIndex.value = 0;
  if (!options.value.length) fetchOptions();
}

function handleKey(e: KeyboardEvent) {
  if (e.key === "Escape") {
    open.value = false;
    return;
  }
  if (e.key === "ArrowDown") {
    e.preventDefault();
    highlightIndex.value = Math.min(highlightIndex.value + 1, filtered.value.length - 1);
  }
  if (e.key === "ArrowUp") {
    e.preventDefault();
    highlightIndex.value = Math.max(highlightIndex.value - 1, 0);
  }
  if (e.key === "Enter" && filtered.value[highlightIndex.value]) {
    e.preventDefault();
    select(filtered.value[highlightIndex.value]);
  }
}

function handleClickOutside(e: MouseEvent) {
  if (wrapperRef.value && !wrapperRef.value.contains(e.target as Node)) {
    open.value = false;
  }
}

onMounted(() => {
  document.addEventListener("mousedown", handleClickOutside);
  if (props.staticOptions) options.value = props.staticOptions;
  else fetchOptions();
});

onUnmounted(() => {
  document.removeEventListener("mousedown", handleClickOutside);
});

watch(() => props.staticOptions, (v) => { if (v) options.value = v; });
watch(() => props.deviceUid, () => { if (props.entityType === "variable") fetchOptions(); });
</script>

<template>
  <div ref="wrapperRef" class="relative flex flex-col gap-1">
    <label
      v-if="label"
      class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]"
    >
      {{ label }}
    </label>

    <div class="relative">
      <!-- Selected value display / search input -->
      <input
        :value="open ? query : displayValue"
        :placeholder="placeholder || `Select ${entityType}...`"
        :disabled="disabled"
        class="input w-full pr-8"
        autocomplete="off"
        @input="query = ($event.target as HTMLInputElement).value"
        @focus="handleFocus"
        @keydown="handleKey"
      />

      <!-- Clear button -->
      <button
        v-if="modelValue && optional"
        class="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
        type="button"
        @click.stop="clear"
      >
        <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      <!-- Chevron -->
      <svg
        v-else
        class="absolute right-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[var(--text-muted)] pointer-events-none"
        fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
      </svg>
    </div>

    <!-- Dropdown -->
    <div
      v-if="open"
      class="absolute left-0 right-0 top-full mt-1 z-50 max-h-48 overflow-y-auto rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] shadow-xl"
    >
      <div v-if="loading" class="px-3 py-2 text-xs text-[var(--text-muted)]">
        {{ t('common.loading') }}
      </div>
      <div v-else-if="filtered.length === 0" class="px-3 py-2 text-xs text-[var(--text-muted)]">
        {{ query ? t('common.noMatches') : t('common.noOptionsAvailable') }}
      </div>
      <button
        v-for="(opt, i) in filtered"
        :key="opt.value"
        type="button"
        :class="[
          'w-full text-left px-3 py-2 flex flex-col gap-0.5 transition-colors',
          i === highlightIndex ? 'bg-[var(--primary)]/10' : 'hover:bg-[var(--bg-raised)]',
          opt.value === modelValue ? 'text-[var(--primary)]' : 'text-[var(--text-primary)]',
        ]"
        @mouseenter="highlightIndex = i"
        @click="select(opt)"
      >
        <span class="text-xs font-medium truncate">{{ opt.label }}</span>
        <span v-if="opt.sublabel" class="text-[10px] text-[var(--text-muted)] truncate">{{ opt.sublabel }}</span>
      </button>
    </div>
  </div>
</template>
