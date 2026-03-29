<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string;
    padding?: "none" | "sm" | "md" | "lg";
    hoverable?: boolean;
  }>(),
  { padding: "md", hoverable: false }
);

const padMap: Record<string, string> = {
  none: "",
  sm:   "p-3",
  md:   "p-5",
  lg:   "p-6",
};
</script>

<template>
  <div
    :class="[
      'rounded-xl border bg-[var(--bg-surface)] border-[var(--border)]',
      hoverable && 'transition-all hover:border-[var(--border-hover)] hover:shadow-[var(--shadow-glow-primary)] cursor-pointer',
    ]"
  >
    <div
      v-if="title || $slots.header"
      class="flex items-center justify-between px-5 py-3 border-b border-[var(--border)]"
    >
      <slot name="header">
        <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ title }}</h3>
      </slot>
      <slot name="actions" />
    </div>
    <div :class="padMap[padding]">
      <slot />
    </div>
    <div v-if="$slots.footer" class="px-5 py-3 border-t border-[var(--border)]">
      <slot name="footer" />
    </div>
  </div>
</template>
