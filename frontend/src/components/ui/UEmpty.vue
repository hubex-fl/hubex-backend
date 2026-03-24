<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string;
    description?: string;
    icon?: string;
  }>(),
  {
    title: "Nothing here",
    description: "No data to display.",
  }
);
</script>

<template>
  <div class="flex flex-col items-center justify-center py-16 px-4 text-center gap-3">
    <div
      v-if="icon || $slots.icon"
      class="h-12 w-12 rounded-full bg-[var(--bg-raised)] flex items-center justify-center text-[var(--text-muted)]"
    >
      <slot name="icon">
        <svg class="h-6 w-6" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path :d="icon || 'M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4'" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </slot>
    </div>
    <div>
      <p class="text-sm font-semibold text-[var(--text-primary)]">{{ title }}</p>
      <p class="text-xs text-[var(--text-muted)] mt-1">{{ description }}</p>
    </div>
    <slot />
  </div>
</template>
