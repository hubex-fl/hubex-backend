<script setup lang="ts">
defineProps<{
  modelValue: boolean;
  label?: string;
  disabled?: boolean;
  size?: "sm" | "md";
}>();

const emit = defineEmits<{ (e: "update:modelValue", v: boolean): void }>();
</script>

<template>
  <label
    :class="[
      'inline-flex items-center gap-2',
      disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer',
    ]"
  >
    <button
      type="button"
      role="switch"
      :aria-checked="modelValue"
      :disabled="disabled"
      :class="[
        'relative shrink-0 rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:ring-offset-2 focus:ring-offset-[var(--bg-base)]',
        size === 'sm' ? 'h-4 w-7' : 'h-5 w-9',
        modelValue ? 'bg-[var(--primary)]' : 'bg-[var(--bg-raised)]',
      ]"
      @click="!disabled && emit('update:modelValue', !modelValue)"
    >
      <span
        :class="[
          'absolute top-0.5 block rounded-full bg-white shadow transition-transform duration-200',
          size === 'sm' ? 'h-3 w-3' : 'h-4 w-4',
          modelValue
            ? (size === 'sm' ? 'translate-x-3.5' : 'translate-x-4')
            : 'translate-x-0.5',
        ]"
      />
    </button>
    <span v-if="label" class="text-sm text-[var(--text-primary)]">{{ label }}</span>
  </label>
</template>
