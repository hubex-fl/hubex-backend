<script setup lang="ts">
withDefaults(
  defineProps<{
    width?: string;
    height?: string;
    rounded?: "sm" | "md" | "lg" | "full";
    lines?: number;
  }>(),
  { rounded: "md", lines: 1 }
);
</script>

<template>
  <div v-if="lines > 1" class="flex flex-col gap-2">
    <div
      v-for="i in lines"
      :key="i"
      :class="[
        'animate-pulse bg-[var(--bg-raised)]',
        rounded === 'sm' ? 'rounded-sm' :
        rounded === 'lg' ? 'rounded-lg' :
        rounded === 'full' ? 'rounded-full' : 'rounded',
        i === lines && lines > 1 ? 'w-3/4' : 'w-full',
      ]"
      :style="{ height: height || '1rem' }"
    />
  </div>
  <div
    v-else
    :class="[
      'animate-pulse bg-[var(--bg-raised)]',
      rounded === 'sm' ? 'rounded-sm' :
      rounded === 'lg' ? 'rounded-lg' :
      rounded === 'full' ? 'rounded-full' : 'rounded',
    ]"
    :style="{ width: width || '100%', height: height || '1rem' }"
  />
</template>
