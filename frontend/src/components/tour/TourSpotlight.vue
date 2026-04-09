<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from "vue";
import { resolveTargetRect } from "../../lib/tour-engine";

const props = defineProps<{
  target?: string;
  pulse?: boolean;
}>();

/* ---- Spotlight rect (viewport coordinates) ---- */
const rect = ref<DOMRect | null>(null);

const PADDING = 10; // px around element

/** Viewport dimensions for SVG viewBox (keeps SVG coords = CSS px). */
const vpW = ref(window.innerWidth);
const vpH = ref(window.innerHeight);

function updateRect() {
  rect.value = resolveTargetRect(props.target);
}

function updateViewport() {
  vpW.value = window.innerWidth;
  vpH.value = window.innerHeight;
}

let _raf: number | null = null;
let _resizeObserver: ResizeObserver | null = null;

function startTracking() {
  stopTracking();
  updateRect();
  updateViewport();

  // Continuously track position (handles scroll / layout shifts)
  const tick = () => {
    updateRect();
    _raf = requestAnimationFrame(tick);
  };
  _raf = requestAnimationFrame(tick);

  // Also watch for size changes on the target element
  if (props.target) {
    const el = document.querySelector(props.target);
    if (el) {
      _resizeObserver = new ResizeObserver(updateRect);
      _resizeObserver.observe(el);
    }
  }
}

function stopTracking() {
  if (_raf) {
    cancelAnimationFrame(_raf);
    _raf = null;
  }
  if (_resizeObserver) {
    _resizeObserver.disconnect();
    _resizeObserver = null;
  }
}

onMounted(() => {
  startTracking();
  window.addEventListener("resize", updateViewport);
});

onUnmounted(() => {
  stopTracking();
  window.removeEventListener("resize", updateViewport);
});

watch(() => props.target, () => {
  startTracking();
});

/* ---- SVG mask coordinates ---- */
const holeX = computed(() => (rect.value ? rect.value.x - PADDING : 0));
const holeY = computed(() => (rect.value ? rect.value.y - PADDING : 0));
const holeW = computed(() => (rect.value ? rect.value.width + PADDING * 2 : 0));
const holeH = computed(() => (rect.value ? rect.value.height + PADDING * 2 : 0));
const hasHole = computed(() => rect.value !== null);

/* ---- Pulse ring ---- */
const pulseX = computed(() => (rect.value ? rect.value.x + rect.value.width / 2 : 0));
const pulseY = computed(() => (rect.value ? rect.value.y + rect.value.height / 2 : 0));
const pulseR = computed(() =>
  rect.value ? Math.max(rect.value.width, rect.value.height) / 2 + PADDING + 4 : 0,
);
</script>

<template>
  <!-- viewBox matches the viewport so SVG coords = CSS pixels from getBoundingClientRect -->
  <svg
    class="absolute inset-0 w-full h-full pointer-events-none"
    :viewBox="`0 0 ${vpW} ${vpH}`"
    preserveAspectRatio="xMinYMin meet"
  >
    <defs>
      <mask id="tour-spotlight-mask">
        <!-- White = show (dark overlay visible) -->
        <rect x="0" y="0" :width="vpW" :height="vpH" fill="white" />
        <!-- Black = hide (hole in overlay) -->
        <rect
          v-if="hasHole"
          :x="holeX"
          :y="holeY"
          :width="holeW"
          :height="holeH"
          rx="8"
          ry="8"
          fill="black"
          class="tour-spotlight-hole"
        />
      </mask>
    </defs>

    <!-- Dark overlay with mask hole -->
    <rect
      x="0"
      y="0"
      :width="vpW"
      :height="vpH"
      fill="rgba(0,0,0,0.65)"
      mask="url(#tour-spotlight-mask)"
    />

    <!-- Pulse ring around the spotlight -->
    <circle
      v-if="hasHole && pulse"
      :cx="pulseX"
      :cy="pulseY"
      :r="pulseR"
      fill="none"
      stroke="var(--primary, #F5A623)"
      stroke-width="2"
      class="tour-pulse-ring"
    />
  </svg>
</template>

<style scoped>
.tour-spotlight-hole {
  transition: x 0.4s cubic-bezier(0.4, 0, 0.2, 1),
              y 0.4s cubic-bezier(0.4, 0, 0.2, 1),
              width 0.4s cubic-bezier(0.4, 0, 0.2, 1),
              height 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.tour-pulse-ring {
  animation: tour-pulse 2s ease-in-out infinite;
  transform-origin: center;
}

@keyframes tour-pulse {
  0%   { opacity: 0.7; stroke-width: 2; }
  50%  { opacity: 0.2; stroke-width: 4; }
  100% { opacity: 0.7; stroke-width: 2; }
}
</style>
