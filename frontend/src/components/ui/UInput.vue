<script setup lang="ts">
defineProps<{
  modelValue?: string;
  label?: string;
  placeholder?: string;
  error?: string;
  type?: string;
  disabled?: boolean;
  variant?: "default" | "search";
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
    <div class="relative">
      <span
        v-if="variant === 'search'"
        class="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)]"
        aria-hidden="true"
      >
        <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
      </span>
      <input
        :id="id"
        v-bind="$attrs"
        :value="modelValue"
        :type="type || 'text'"
        :placeholder="placeholder"
        :disabled="disabled"
        :class="[
          'input w-full',
          variant === 'search' && 'pl-8',
          error && 'border-[var(--status-bad)] focus:ring-[var(--status-bad)]',
        ]"
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      />
    </div>
    <p v-if="error" class="text-xs text-[var(--status-bad)]">{{ error }}</p>
  </div>
</template>
