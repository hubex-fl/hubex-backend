<script setup lang="ts">
import { computed } from "vue";

type Variant = "primary" | "secondary" | "danger" | "ghost";
type Size = "sm" | "md" | "lg";

const props = withDefaults(
  defineProps<{
    variant?: Variant;
    size?: Size;
    loading?: boolean;
    disabled?: boolean;
    type?: "button" | "submit" | "reset";
  }>(),
  { variant: "primary", size: "md", loading: false, disabled: false, type: "button" }
);

const classes = computed(() => {
  const base =
    "inline-flex items-center gap-1.5 rounded-lg font-medium font-sans transition-all duration-150 whitespace-nowrap focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-cyan)] focus-visible:ring-offset-1 focus-visible:ring-offset-[var(--bg-base)] disabled:opacity-40 disabled:cursor-not-allowed";

  const sizes: Record<Size, string> = {
    sm: "px-2.5 py-1 text-xs",
    md: "px-3.5 py-1.5 text-sm",
    lg: "px-5 py-2 text-base",
  };

  const variants: Record<Variant, string> = {
    primary:
      "bg-[var(--accent-cyan)] text-[var(--bg-base)] border border-transparent hover:opacity-85 active:opacity-75",
    secondary:
      "bg-[var(--bg-raised)] text-[var(--text-primary)] border border-[var(--border)] hover:bg-[var(--bg-overlay)] hover:border-[var(--border-hover)]",
    danger:
      "bg-[var(--status-bad)] text-white border border-transparent hover:opacity-85",
    ghost:
      "bg-transparent text-[var(--text-secondary)] border border-transparent hover:bg-[var(--bg-raised)] hover:text-[var(--text-primary)]",
  };

  return [base, sizes[props.size], variants[props.variant]];
});
</script>

<template>
  <button
    v-bind="$attrs"
    :class="classes"
    :disabled="disabled || loading"
    :type="type"
  >
    <svg
      v-if="loading"
      class="animate-spin"
      :class="size === 'sm' ? 'h-3 w-3' : 'h-4 w-4'"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
    <slot />
  </button>
</template>
