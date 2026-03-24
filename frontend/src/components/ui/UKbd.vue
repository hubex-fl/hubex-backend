<script setup lang="ts">
defineProps<{
  keys: string | string[];
}>();
</script>

<template>
  <span class="inline-flex items-center gap-0.5">
    <template v-if="Array.isArray(keys)">
      <template v-for="(k, i) in keys" :key="k">
        <kbd
          class="inline-flex items-center justify-center min-w-[1.4em] h-5 px-1.5 rounded text-[10px] font-mono font-semibold border border-b-2 border-[var(--border)] bg-[var(--bg-raised)] text-[var(--text-muted)]"
        >
          {{ k }}
        </kbd>
        <span v-if="i < keys.length - 1" class="text-[var(--text-muted)] text-[10px]">+</span>
      </template>
    </template>
    <kbd
      v-else
      class="inline-flex items-center justify-center min-w-[1.4em] h-5 px-1.5 rounded text-[10px] font-mono font-semibold border border-b-2 border-[var(--border)] bg-[var(--bg-raised)] text-[var(--text-muted)]"
    >
      {{ keys }}
    </kbd>
  </span>
</template>
