<template>
  <div class="ctrl-toggle" :class="{ disabled }">
    <div class="toggle-track" :class="{ on: modelValue, loading }" @click="toggle">
      <div class="toggle-thumb" />
    </div>
    <span class="toggle-label">{{ modelValue ? onLabel : offLabel }}</span>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  modelValue: boolean;
  loading?: boolean;
  disabled?: boolean;
  onLabel?: string;
  offLabel?: string;
}>(), {
  loading: false,
  disabled: false,
  onLabel: "ON",
  offLabel: "OFF",
});

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  change: [value: boolean];
}>();

function toggle() {
  if (props.disabled || props.loading) return;
  const next = !props.modelValue;
  emit("update:modelValue", next);
  emit("change", next);
}
</script>

<style scoped>
.ctrl-toggle {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}
.ctrl-toggle.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.toggle-track {
  position: relative;
  width: 48px;
  height: 26px;
  border-radius: 13px;
  background: #30363d;
  transition: background 0.2s;
  cursor: pointer;
  flex-shrink: 0;
}
.toggle-track.on   { background: var(--primary, #2DD4BF); }
.toggle-track.loading { opacity: 0.6; }
.toggle-thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #e6edf3;
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow: 0 1px 3px rgba(0,0,0,0.4);
}
.toggle-track.on .toggle-thumb {
  transform: translateX(22px);
}
.toggle-label {
  font-size: 13px;
  font-weight: 600;
  font-family: monospace;
  color: #c9d1d9;
  min-width: 28px;
}
</style>
