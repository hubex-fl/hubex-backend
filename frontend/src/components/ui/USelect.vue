<script setup lang="ts">
defineProps<{
  modelValue?: string | number;
  label?: string;
  options?: Array<{ value: string | number; label: string }>;
  placeholder?: string;
  disabled?: boolean;
  id?: string;
}>();

const emit = defineEmits<{ (e: "update:modelValue", v: string): void }>();
</script>

<template>
  <div class="flex flex-col gap-1">
    <label
      v-if="label"
      :for="id"
      class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]"
    >
      {{ label }}
    </label>
    <select
      :id="id"
      v-bind="$attrs"
      :value="modelValue"
      :disabled="disabled"
      class="input"
      @change="emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
    >
      <option v-if="placeholder" value="" disabled>{{ placeholder }}</option>
      <template v-if="options?.length">
        <option
          v-for="opt in options"
          :key="opt.value"
          :value="opt.value"
          :selected="opt.value === modelValue"
        >{{ opt.label }}</option>
      </template>
      <slot v-else />
    </select>
  </div>
</template>
