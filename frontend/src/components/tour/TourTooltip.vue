<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import type { TourStep } from "../../lib/tour-engine";
import { resolveTargetRect } from "../../lib/tour-engine";
import { useTourStore } from "../../stores/tour";
import { useI18n } from "vue-i18n";

const props = defineProps<{
  step: TourStep;
  stepIndex: number;
  totalSteps: number;
}>();

const tourStore = useTourStore();
const { t } = useI18n();

/* ---- Positioning ---- */
const tooltipRef = ref<HTMLElement | null>(null);
const posStyle = ref<Record<string, string>>({});
const arrowStyle = ref<Record<string, string>>({});
const visible = ref(false);

const GAP = 16; // px between target and tooltip

function reposition() {
  const targetRect = resolveTargetRect(props.step.target);
  const el = tooltipRef.value;
  if (!el) return;

  const tooltipRect = el.getBoundingClientRect();
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  let pos = props.step.position;

  let top = 0;
  let left = 0;

  if (!targetRect || pos === "center") {
    // Center on screen
    top = vh / 2 - tooltipRect.height / 2;
    left = vw / 2 - tooltipRect.width / 2;
    posStyle.value = { top: `${top}px`, left: `${left}px` };
    arrowStyle.value = { display: "none" };
    return;
  }

  // Calculate ideal position
  switch (pos) {
    case "bottom":
      top = targetRect.bottom + GAP;
      left = targetRect.left + targetRect.width / 2 - tooltipRect.width / 2;
      break;
    case "top":
      top = targetRect.top - tooltipRect.height - GAP;
      left = targetRect.left + targetRect.width / 2 - tooltipRect.width / 2;
      break;
    case "right":
      top = targetRect.top + targetRect.height / 2 - tooltipRect.height / 2;
      left = targetRect.right + GAP;
      break;
    case "left":
      top = targetRect.top + targetRect.height / 2 - tooltipRect.height / 2;
      left = targetRect.left - tooltipRect.width - GAP;
      break;
  }

  // Clamp to viewport
  const MARGIN = 12;
  if (left < MARGIN) left = MARGIN;
  if (left + tooltipRect.width > vw - MARGIN) left = vw - MARGIN - tooltipRect.width;
  if (top < MARGIN) top = MARGIN;
  if (top + tooltipRect.height > vh - MARGIN) top = vh - MARGIN - tooltipRect.height;

  posStyle.value = { top: `${top}px`, left: `${left}px` };

  // Arrow pointing toward target center
  const targetCenterX = targetRect.left + targetRect.width / 2;
  const targetCenterY = targetRect.top + targetRect.height / 2;

  const arrowPos: Record<string, string> = { display: "block" };
  switch (pos) {
    case "bottom":
      arrowPos.top = "-6px";
      arrowPos.left = `${Math.min(Math.max(targetCenterX - left, 16), tooltipRect.width - 16)}px`;
      arrowPos.transform = "translateX(-50%) rotate(45deg)";
      break;
    case "top":
      arrowPos.bottom = "-6px";
      arrowPos.left = `${Math.min(Math.max(targetCenterX - left, 16), tooltipRect.width - 16)}px`;
      arrowPos.transform = "translateX(-50%) rotate(45deg)";
      break;
    case "right":
      arrowPos.left = "-6px";
      arrowPos.top = `${Math.min(Math.max(targetCenterY - top, 16), tooltipRect.height - 16)}px`;
      arrowPos.transform = "translateY(-50%) rotate(45deg)";
      break;
    case "left":
      arrowPos.right = "-6px";
      arrowPos.top = `${Math.min(Math.max(targetCenterY - top, 16), tooltipRect.height - 16)}px`;
      arrowPos.transform = "translateY(-50%) rotate(45deg)";
      break;
  }
  arrowStyle.value = arrowPos;
}

/* ---- Entrance animation ---- */
const slideClass = computed(() => {
  switch (props.step.position) {
    case "top":    return "tour-slide-from-bottom";
    case "bottom": return "tour-slide-from-top";
    case "left":   return "tour-slide-from-right";
    case "right":  return "tour-slide-from-left";
    default:       return "tour-slide-from-bottom";
  }
});

/* ---- Track position continuously ---- */
let _raf: number | null = null;

function startTracking() {
  visible.value = false;
  // Let DOM settle, then position + fade in
  requestAnimationFrame(() => {
    reposition();
    requestAnimationFrame(() => {
      reposition();
      visible.value = true;
    });
  });

  const tick = () => {
    reposition();
    _raf = requestAnimationFrame(tick);
  };
  _raf = requestAnimationFrame(tick);
}

function stopTracking() {
  if (_raf) {
    cancelAnimationFrame(_raf);
    _raf = null;
  }
}

onMounted(startTracking);
onUnmounted(stopTracking);

watch(() => [props.step.id, props.step.target], () => {
  visible.value = false;
  requestAnimationFrame(() => {
    reposition();
    requestAnimationFrame(() => {
      visible.value = true;
    });
  });
});
</script>

<template>
  <div
    ref="tooltipRef"
    :class="[
      'tour-tooltip absolute z-[10001] max-w-sm w-80 rounded-xl shadow-2xl border border-[var(--border)] bg-[var(--bg-surface)]',
      'transition-all duration-300',
      visible ? 'opacity-100 translate-y-0' : `opacity-0 ${slideClass}`,
    ]"
    :style="posStyle"
  >
    <!-- Arrow -->
    <div
      class="absolute w-3 h-3 bg-[var(--bg-surface)] border border-[var(--border)] z-[-1]"
      :style="arrowStyle"
    />

    <!-- Close button (top-right, small) -->
    <button
      class="absolute top-2 right-2 p-1 rounded text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
      :title="t('tour.close')"
      @click="tourStore.stop()"
    >
      <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>

    <!-- Content -->
    <div class="px-4 pt-4 pb-3">
      <h3 class="text-sm font-semibold text-[var(--text-primary)] pr-6">{{ step.title }}</h3>
      <p class="mt-1 text-xs text-[var(--text-muted)] leading-relaxed">{{ step.text }}</p>
    </div>

    <!-- Footer: controls + step counter -->
    <div class="flex items-center justify-between px-4 pb-3 pt-1">
      <!-- Step counter -->
      <span class="text-[10px] font-mono text-[var(--text-muted)]">
        {{ stepIndex + 1 }} / {{ totalSteps }}
      </span>

      <!-- Controls -->
      <div class="flex items-center gap-1">
        <button
          class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          :disabled="stepIndex <= 0"
          :title="t('tour.prev')"
          @click="tourStore.prev()"
        >
          <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
          </svg>
        </button>

        <button
          class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--primary)] hover:bg-[var(--primary)]/10 transition-colors"
          :title="tourStore.isPaused ? t('tour.resume') : t('tour.pause')"
          @click="tourStore.isPaused ? tourStore.resume() : tourStore.pause()"
        >
          <!-- Pause icon -->
          <svg v-if="!tourStore.isPaused" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 5.25v13.5m-7.5-13.5v13.5" />
          </svg>
          <!-- Play icon -->
          <svg v-else class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
          </svg>
        </button>

        <button
          class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          :disabled="stepIndex >= totalSteps - 1"
          :title="t('tour.next')"
          @click="tourStore.next()"
        >
          <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tour-slide-from-top    { transform: translateY(-8px); }
.tour-slide-from-bottom { transform: translateY(8px); }
.tour-slide-from-left   { transform: translateX(-8px); }
.tour-slide-from-right  { transform: translateX(8px); }
</style>
