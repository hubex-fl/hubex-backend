<script setup lang="ts">
import { computed } from "vue";
import { useTourStore } from "../../stores/tour";

const tourStore = useTourStore();

const segments = computed(() => {
  if (!tourStore.activeTour) return [];
  return tourStore.activeTour.steps.map((_, i) => ({
    index: i,
    completed: i < tourStore.currentStepIndex,
    active: i === tourStore.currentStepIndex,
  }));
});
</script>

<template>
  <div class="fixed bottom-0 left-0 right-0 h-1 z-[10002] flex bg-white/5">
    <button
      v-for="seg in segments"
      :key="seg.index"
      class="relative flex-1 h-full cursor-pointer group transition-colors"
      :class="seg.completed ? 'bg-[var(--primary)]' : 'bg-white/10'"
      :title="`Step ${seg.index + 1}`"
      @click="tourStore.goToStep(seg.index)"
    >
      <!-- Per-step countdown fill (only on active segment) -->
      <div
        v-if="seg.active"
        class="absolute inset-y-0 left-0 bg-[var(--primary)] transition-none"
        :style="{ width: `${tourStore.stepProgress * 100}%` }"
      />
      <!-- Hover highlight -->
      <div class="absolute inset-0 bg-white/0 group-hover:bg-white/10 transition-colors" />
    </button>
  </div>
</template>
