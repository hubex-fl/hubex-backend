<script setup lang="ts">
import { computed, onMounted, onUnmounted } from "vue";
import { useTourStore } from "../../stores/tour";
import { useI18n } from "vue-i18n";
import TourSpotlight from "./TourSpotlight.vue";
import TourTooltip from "./TourTooltip.vue";
import TourProgress from "./TourProgress.vue";

const tourStore = useTourStore();
const { t } = useI18n();

const showPulse = computed(() => {
  const action = tourStore.currentStep?.action;
  return action === "spotlight+pulse" || action === "zoom";
});

/* ---- Keyboard shortcuts ---- */
function onKeydown(e: KeyboardEvent) {
  if (!tourStore.activeTour) return;

  switch (e.key) {
    case "Escape":
      e.preventDefault();
      tourStore.stop();
      break;
    case "ArrowRight":
    case " ":
      e.preventDefault();
      tourStore.next();
      break;
    case "ArrowLeft":
      e.preventDefault();
      tourStore.prev();
      break;
    case "p":
      e.preventDefault();
      if (tourStore.isPaused) tourStore.resume();
      else tourStore.pause();
      break;
  }
}

onMounted(() => {
  document.addEventListener("keydown", onKeydown);
});

onUnmounted(() => {
  document.removeEventListener("keydown", onKeydown);
});
</script>

<template>
  <Teleport to="body">
    <div
      v-if="tourStore.activeTour && tourStore.currentStep"
      class="fixed inset-0 z-[9999]"
    >
      <!-- Dark overlay with spotlight hole -->
      <TourSpotlight
        :target="tourStore.currentStep.target"
        :pulse="showPulse"
      />

      <!-- Click-through blocker (prevents interaction outside spotlight) -->
      <div
        class="absolute inset-0 z-[10000]"
        @click.self="tourStore.next()"
      />

      <!-- Loading indicator during page transitions -->
      <div
        v-if="tourStore.isTransitioning"
        class="absolute inset-0 z-[10003] flex items-center justify-center"
      >
        <div class="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--bg-surface)] border border-[var(--border)] shadow-lg">
          <svg class="h-4 w-4 animate-spin text-[var(--primary)]" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span class="text-xs text-[var(--text-muted)]">{{ t('tour.loading') }}</span>
        </div>
      </div>

      <!-- Tooltip bubble -->
      <TourTooltip
        v-if="!tourStore.isTransitioning"
        :step="tourStore.currentStep"
        :step-index="tourStore.currentStepIndex"
        :total-steps="tourStore.activeTour.steps.length"
      />

      <!-- Progress bar at bottom -->
      <TourProgress />
    </div>
  </Teleport>
</template>
