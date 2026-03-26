<script setup lang="ts">
import { inject, computed } from "vue";
import type { Ref, ComputedRef } from "vue";

const props = defineProps<{
  value: string | number;
  label?: string;
  disabled?: boolean;
}>();

const active = inject<ComputedRef<string | number | undefined>>("tabs-active");
const setActive = inject<(v: string | number) => void>("tabs-set-active");
const variant = inject<ComputedRef<string>>("tabs-variant");

const isActive = computed(() => active?.value === props.value);

function select() {
  if (!props.disabled) setActive?.(props.value);
}
</script>

<template>
  <button
    role="tab"
    :aria-selected="isActive"
    :disabled="disabled"
    @click="select"
    :class="[
      variant === 'pills'
        ? [
            'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
            isActive
              ? 'bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-sm'
              : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]',
          ]
        : [
            'relative px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px',
            isActive
              ? 'border-[var(--accent-cyan)] text-[var(--accent-cyan)]'
              : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:border-[var(--border)]',
          ],
      disabled && 'opacity-40 cursor-not-allowed',
    ]"
  >
    <slot>{{ label }}</slot>
  </button>
</template>
