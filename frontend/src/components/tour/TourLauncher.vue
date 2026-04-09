<script setup lang="ts">
import { ref, computed } from "vue";
import { useTourStore } from "../../stores/tour";
import { useI18n } from "vue-i18n";

const tourStore = useTourStore();
const { t, te } = useI18n();

/** Resolve a string that may be an i18n key or plain text. */
function resolveText(value: string): string {
  if (!value) return value;
  if (value.includes('.') && !value.includes(' ') && te(value)) {
    return t(value);
  }
  return value;
}

const isOpen = ref(false);

const tours = computed(() => tourStore.availableTours);
const hasTours = computed(() => tours.value.length > 0);

function startTour(tourId: string) {
  isOpen.value = false;
  tourStore.start(tourId);
}
</script>

<template>
  <!-- Only render when tours are registered -->
  <div v-if="hasTours" class="relative">
    <!-- Trigger button -->
    <button
      class="p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--primary)] hover:bg-[var(--primary)]/10 transition-colors"
      :title="t('tour.guidedTours')"
      @click="isOpen = !isOpen"
    >
      <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
      </svg>
    </button>

    <!-- Dropdown panel -->
    <Transition name="tour-panel">
      <div
        v-if="isOpen"
        class="absolute right-0 top-full mt-2 z-50 w-72 rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] shadow-xl overflow-hidden"
      >
        <!-- Header -->
        <div class="px-4 py-3 border-b border-[var(--border)]">
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('tour.guidedTours') }}</h3>
          <p class="text-[10px] text-[var(--text-muted)] mt-0.5">{{ t('tour.selectTour') }}</p>
        </div>

        <!-- Tour list -->
        <div class="max-h-64 overflow-y-auto py-1">
          <button
            v-for="tour in tours"
            :key="tour.id"
            class="w-full flex items-start gap-3 px-4 py-2.5 text-left hover:bg-[var(--bg-raised)] transition-colors"
            @click="startTour(tour.id)"
          >
            <!-- Icon -->
            <div class="shrink-0 mt-0.5 h-7 w-7 rounded-lg bg-[var(--primary)]/10 text-[var(--primary)] flex items-center justify-center">
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
              </svg>
            </div>
            <!-- Text -->
            <div class="min-w-0 flex-1">
              <div class="text-xs font-medium text-[var(--text-primary)] truncate">{{ resolveText(tour.name) }}</div>
              <div class="text-[10px] text-[var(--text-muted)] mt-0.5 line-clamp-2">{{ resolveText(tour.description) }}</div>
              <div class="text-[10px] text-[var(--text-muted)] mt-1 font-mono">
                {{ tour.steps.length }} {{ t('tour.steps') }}
              </div>
            </div>
          </button>
        </div>
      </div>
    </Transition>

    <!-- Click-outside to close -->
    <div
      v-if="isOpen"
      class="fixed inset-0 z-40"
      @click="isOpen = false"
    />
  </div>
</template>

<style scoped>
.tour-panel-enter-active,
.tour-panel-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.tour-panel-enter-from,
.tour-panel-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.97);
}
</style>
