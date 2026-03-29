<template>
  <div class="ctrl-slider" :class="{ disabled }">
    <div class="slider-header">
      <span class="slider-value">{{ displayValue }}<span v-if="unit" class="slider-unit"> {{ unit }}</span></span>
    </div>
    <div class="slider-track-wrap">
      <input
        type="range"
        class="slider-input"
        :min="min"
        :max="max"
        :step="step"
        :value="modelValue"
        :disabled="disabled || loading"
        @input="onInput"
        @change="onChange"
      />
      <div class="slider-fill" :style="{ width: fillPct + '%' }" />
    </div>
    <div class="slider-bounds">
      <span>{{ min }}<span v-if="unit"> {{ unit }}</span></span>
      <span>{{ max }}<span v-if="unit"> {{ unit }}</span></span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(defineProps<{
  modelValue: number;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  loading?: boolean;
  disabled?: boolean;
}>(), {
  min: 0,
  max: 100,
  step: 1,
  loading: false,
  disabled: false,
});

const emit = defineEmits<{
  "update:modelValue": [value: number];
  change: [value: number];
}>();

const displayValue = computed(() => {
  const v = props.modelValue;
  if (Number.isInteger(v)) return String(v);
  return v.toFixed(1);
});

const fillPct = computed(() => {
  const range = props.max - props.min;
  if (range <= 0) return 0;
  return ((props.modelValue - props.min) / range) * 100;
});

function onInput(e: Event) {
  const val = parseFloat((e.target as HTMLInputElement).value);
  emit("update:modelValue", val);
}

function onChange(e: Event) {
  const val = parseFloat((e.target as HTMLInputElement).value);
  emit("change", val);
}
</script>

<style scoped>
.ctrl-slider { display: flex; flex-direction: column; gap: 8px; }
.ctrl-slider.disabled { opacity: 0.4; }

.slider-header {
  display: flex;
  justify-content: center;
}
.slider-value {
  font-family: monospace;
  font-size: 20px;
  font-weight: 700;
  color: #e6edf3;
}
.slider-unit { font-size: 14px; font-weight: 400; color: #8b949e; }

.slider-track-wrap {
  position: relative;
}
.slider-input {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  background: #30363d;
  border-radius: 3px;
  outline: none;
  cursor: pointer;
  position: relative;
  z-index: 1;
}
.slider-input::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--primary, #2DD4BF);
  cursor: pointer;
  box-shadow: 0 0 0 3px rgba(45,212,191,0.2);
  transition: box-shadow 0.15s;
}
.slider-input::-webkit-slider-thumb:hover {
  box-shadow: 0 0 0 5px rgba(45,212,191,0.3);
}
.slider-input:disabled::-webkit-slider-thumb { cursor: not-allowed; opacity: 0.5; }

.slider-bounds {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #484f58;
  font-family: monospace;
}
</style>
