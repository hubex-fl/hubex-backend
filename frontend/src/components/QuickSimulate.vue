<script setup lang="ts">
import { ref, computed, onUnmounted } from "vue";
import { useI18n } from "vue-i18n";
import { putValue } from "../lib/variables";
import type { EffectiveVariable } from "../lib/variables";
import UButton from "./ui/UButton.vue";
import UInput from "./ui/UInput.vue";
import UToggle from "./ui/UToggle.vue";

const props = defineProps<{
  variables: EffectiveVariable[];
  deviceUid: string;
}>();

const emit = defineEmits<{
  (e: "value-sent", key: string, value: any): void;
}>();

const { t } = useI18n();

// Track per-variable simulate state
const simValues = ref<Record<string, any>>({});
const sentFeedback = ref<Record<string, boolean>>({});
const sendingKey = ref<string | null>(null);
const activePatterns = ref<Record<string, number | null>>({});

function getSimValue(v: EffectiveVariable): any {
  if (v.key in simValues.value) return simValues.value[v.key];
  return v.value ?? (resolvedType(v) === "bool" ? false : resolvedType(v) === "int" || resolvedType(v) === "float" ? 0 : "");
}

function setSimValue(key: string, val: any) {
  simValues.value[key] = val;
}

function resolvedType(v: EffectiveVariable): string {
  return v.resolved_type ?? "string";
}

function isNumeric(v: EffectiveVariable): boolean {
  const rt = resolvedType(v);
  return rt === "int" || rt === "float";
}

function isBool(v: EffectiveVariable): boolean {
  return resolvedType(v) === "bool";
}

function getMin(v: EffectiveVariable): number {
  return v.constraints?.min ?? 0;
}

function getMax(v: EffectiveVariable): number {
  if (v.constraints?.max != null) return v.constraints.max;
  // Auto-detect from current value
  const cur = typeof v.value === "number" ? v.value : 0;
  if (cur > 0) return Math.ceil(cur * 2);
  return 100;
}

function getStep(v: EffectiveVariable): number {
  return resolvedType(v) === "int" ? 1 : 0.1;
}

async function sendValue(v: EffectiveVariable) {
  const val = getSimValue(v);
  sendingKey.value = v.key;
  try {
    await putValue({
      key: v.key,
      scope: "device",
      deviceUid: props.deviceUid,
      value: resolvedType(v) === "int" ? Math.round(Number(val)) : resolvedType(v) === "float" ? Number(val) : val,
      expectedVersion: v.version ?? undefined,
    });
    sentFeedback.value[v.key] = true;
    emit("value-sent", v.key, val);
    setTimeout(() => {
      sentFeedback.value[v.key] = false;
    }, 1500);
  } catch (e) {
    // Errors handled silently — UI shows no sent feedback
  } finally {
    sendingKey.value = null;
  }
}

async function sendBoolToggle(v: EffectiveVariable) {
  const current = getSimValue(v);
  const next = !current;
  setSimValue(v.key, next);
  sendingKey.value = v.key;
  try {
    await putValue({
      key: v.key,
      scope: "device",
      deviceUid: props.deviceUid,
      value: next,
      expectedVersion: v.version ?? undefined,
    });
    sentFeedback.value[v.key] = true;
    emit("value-sent", v.key, next);
    setTimeout(() => {
      sentFeedback.value[v.key] = false;
    }, 1500);
  } catch {
    // revert
    setSimValue(v.key, current);
  } finally {
    sendingKey.value = null;
  }
}

function stopPattern(key: string) {
  const timer = activePatterns.value[key];
  if (timer !== null && timer !== undefined) {
    clearInterval(timer);
    activePatterns.value[key] = null;
  }
}

async function runPattern(v: EffectiveVariable, pattern: "ramp_up" | "ramp_down" | "random" | "spike") {
  stopPattern(v.key);

  const min = getMin(v);
  const max = getMax(v);
  const isInt = resolvedType(v) === "int";

  if (pattern === "spike") {
    const current = typeof v.value === "number" ? v.value : (max - min) / 2;
    const spiked = Math.min(current * 3, max * 3);
    const val = isInt ? Math.round(spiked) : Number(spiked.toFixed(1));
    setSimValue(v.key, val);
    await sendValue(v);
    return;
  }

  let step = 0;
  const total = 10;
  const timer = window.setInterval(async () => {
    if (step >= total) {
      stopPattern(v.key);
      return;
    }

    let val: number;
    switch (pattern) {
      case "ramp_up":
        val = min + ((max - min) * step) / (total - 1);
        break;
      case "ramp_down":
        val = max - ((max - min) * step) / (total - 1);
        break;
      case "random":
        val = min + Math.random() * (max - min);
        break;
      default:
        val = 0;
    }

    val = isInt ? Math.round(val) : Number(val.toFixed(1));
    setSimValue(v.key, val);

    try {
      await putValue({
        key: v.key,
        scope: "device",
        deviceUid: props.deviceUid,
        value: val,
      });
      emit("value-sent", v.key, val);
    } catch {
      // continue pattern even on error
    }

    step++;
  }, 1000);

  activePatterns.value[v.key] = timer;
}

const numericVars = computed(() => props.variables.filter(isNumeric));

// Cleanup on unmount
onUnmounted(() => {
  for (const key of Object.keys(activePatterns.value)) {
    stopPattern(key);
  }
});
</script>

<template>
  <div class="space-y-1">
    <div
      v-for="v in variables"
      :key="v.key"
      class="px-4 py-2.5 flex items-start gap-3 border-b border-[var(--border)] last:border-b-0"
    >
      <div class="flex-1 min-w-0 space-y-1.5">
        <!-- Variable name + type badge -->
        <div class="flex items-center gap-2 flex-wrap">
          <span class="text-xs font-mono font-semibold text-[var(--text-primary)] truncate">{{ v.key }}</span>
          <span
            v-if="sentFeedback[v.key]"
            class="text-[10px] text-[var(--status-ok)] font-medium animate-pulse"
          >{{ t('devices.valueSent') }}</span>
        </div>

        <!-- Boolean toggle -->
        <div v-if="isBool(v)" class="flex items-center gap-3">
          <UToggle
            :model-value="!!getSimValue(v)"
            size="sm"
            @update:model-value="sendBoolToggle(v)"
          />
          <span class="text-xs text-[var(--text-muted)] font-mono">{{ getSimValue(v) ? 'ON' : 'OFF' }}</span>
        </div>

        <!-- Numeric slider + input -->
        <div v-else-if="isNumeric(v)" class="space-y-1.5">
          <div class="flex items-center gap-2">
            <input
              type="range"
              :min="getMin(v)"
              :max="getMax(v)"
              :step="getStep(v)"
              :value="getSimValue(v)"
              class="flex-1 h-1.5 accent-[var(--primary)] cursor-pointer"
              @input="setSimValue(v.key, Number(($event.target as HTMLInputElement).value))"
            />
            <input
              type="number"
              :value="getSimValue(v)"
              :min="getMin(v)"
              :max="getMax(v)"
              :step="getStep(v)"
              class="w-20 text-xs font-mono px-2 py-1 rounded border border-[var(--border)] bg-[var(--bg-base)] text-[var(--text-primary)] text-right"
              @input="setSimValue(v.key, Number(($event.target as HTMLInputElement).value))"
            />
            <span v-if="v.constraints?.unit" class="text-[10px] text-[var(--text-muted)]">{{ v.constraints.unit }}</span>
          </div>
          <!-- Quick patterns -->
          <div class="flex gap-1 flex-wrap">
            <button
              v-if="!activePatterns[v.key]"
              class="text-[10px] px-1.5 py-0.5 rounded border border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:border-[var(--primary)]/40 transition-colors"
              :title="t('devices.rampUp')"
              @click="runPattern(v, 'ramp_up')"
            >{{ t('devices.rampUp') }}</button>
            <button
              v-if="!activePatterns[v.key]"
              class="text-[10px] px-1.5 py-0.5 rounded border border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:border-[var(--primary)]/40 transition-colors"
              :title="t('devices.rampDown')"
              @click="runPattern(v, 'ramp_down')"
            >{{ t('devices.rampDown') }}</button>
            <button
              v-if="!activePatterns[v.key]"
              class="text-[10px] px-1.5 py-0.5 rounded border border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:border-[var(--primary)]/40 transition-colors"
              :title="t('devices.randomValues')"
              @click="runPattern(v, 'random')"
            >{{ t('devices.randomValues') }}</button>
            <button
              v-if="!activePatterns[v.key]"
              class="text-[10px] px-1.5 py-0.5 rounded border border-[var(--status-bad)]/30 text-[var(--status-bad)]/70 hover:text-[var(--status-bad)] hover:border-[var(--status-bad)]/60 transition-colors"
              :title="t('devices.spikeValue')"
              @click="runPattern(v, 'spike')"
            >{{ t('devices.spikeValue') }}</button>
            <button
              v-if="activePatterns[v.key]"
              class="text-[10px] px-1.5 py-0.5 rounded border border-[var(--status-bad)]/40 text-[var(--status-bad)] hover:bg-[var(--status-bad)]/10 transition-colors"
              @click="stopPattern(v.key)"
            >Stop</button>
          </div>
        </div>

        <!-- String / JSON input -->
        <div v-else class="flex items-center gap-2">
          <UInput
            :model-value="String(getSimValue(v) ?? '')"
            class="flex-1"
            :placeholder="resolvedType(v) === 'json' ? '{ ... }' : 'value'"
            @update:model-value="setSimValue(v.key, $event)"
          />
        </div>
      </div>

      <!-- Send button (for non-bool types) -->
      <div v-if="!isBool(v)" class="shrink-0 pt-0.5">
        <UButton
          size="sm"
          :disabled="sendingKey === v.key"
          @click="sendValue(v)"
        >
          {{ t('devices.sendValue') }}
        </UButton>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!variables.length" class="px-4 py-3 text-xs text-[var(--text-muted)] italic">
      {{ t('devices.noVariablesDesc') }}
    </div>
  </div>
</template>
