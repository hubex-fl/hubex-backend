<script setup lang="ts">
import { branding } from '@/lib/branding';
defineProps<{ size?: number; showText?: boolean }>();
</script>
<template>
  <div class="inline-flex items-center gap-2">
    <div
      :style="{ width: (size ?? 28) + 'px', height: (size ?? 28) + 'px' }"
      class="text-[var(--primary)]"
      v-html="branding.logoSVG"
    />
    <span
      v-if="showText"
      class="font-semibold tracking-tight text-[var(--text-primary)]"
      :style="{ fontSize: ((size ?? 28) * 0.6) + 'px' }"
    >
      {{ branding.productName }}
    </span>
  </div>
</template>
