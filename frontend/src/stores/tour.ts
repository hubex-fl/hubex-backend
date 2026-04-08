import { defineStore } from "pinia";
import { ref, computed, watch, type Ref } from "vue";
import { useRouter } from "vue-router";
import type { TourDefinition, TourStep } from "../lib/tour-engine";
import { calcStepDuration, waitForElement } from "../lib/tour-engine";

export const useTourStore = defineStore("tour", () => {
  /* ---- state ---- */
  const availableTours: Ref<TourDefinition[]> = ref([]);
  const activeTour: Ref<TourDefinition | null> = ref(null);
  const currentStepIndex = ref(0);
  const isPlaying = ref(false);
  const isPaused = ref(false);
  /** Progress 0-1 within the current step (for the countdown bar). */
  const stepProgress = ref(0);
  /** Whether the overlay is still waiting for a page/element to load. */
  const isTransitioning = ref(false);

  /* ---- timer internals ---- */
  let _timer: ReturnType<typeof setTimeout> | null = null;
  let _progressRaf: number | null = null;
  let _progressStart = 0;
  let _progressDuration = 0;

  /* ---- computed ---- */
  const currentStep = computed<TourStep | null>(() => {
    if (!activeTour.value) return null;
    return activeTour.value.steps[currentStepIndex.value] ?? null;
  });

  const totalSteps = computed(() => activeTour.value?.steps.length ?? 0);

  /* ---- registry ---- */
  function registerTour(tour: TourDefinition) {
    // Replace existing tour with same id, or append
    const idx = availableTours.value.findIndex((t) => t.id === tour.id);
    if (idx >= 0) {
      availableTours.value.splice(idx, 1, tour);
    } else {
      availableTours.value.push(tour);
    }
  }

  function unregisterTour(id: string) {
    const idx = availableTours.value.findIndex((t) => t.id === id);
    if (idx >= 0) availableTours.value.splice(idx, 1);
    // Stop if the running tour got removed
    if (activeTour.value?.id === id) stop();
  }

  /* ---- autoplay timer ---- */
  function _clearTimers() {
    if (_timer) {
      clearTimeout(_timer);
      _timer = null;
    }
    if (_progressRaf) {
      cancelAnimationFrame(_progressRaf);
      _progressRaf = null;
    }
    stepProgress.value = 0;
  }

  function _tickProgress() {
    const elapsed = performance.now() - _progressStart;
    stepProgress.value = Math.min(1, elapsed / _progressDuration);
    if (stepProgress.value < 1) {
      _progressRaf = requestAnimationFrame(_tickProgress);
    }
  }

  function _scheduleAutoAdvance() {
    _clearTimers();
    if (!isPlaying.value || isPaused.value || !currentStep.value) return;

    const dur = calcStepDuration(currentStep.value);
    _progressDuration = dur;
    _progressStart = performance.now();
    _progressRaf = requestAnimationFrame(_tickProgress);

    _timer = setTimeout(() => {
      if (currentStepIndex.value < totalSteps.value - 1) {
        next();
      } else {
        stop(); // tour finished
      }
    }, dur);
  }

  /* ---- navigation helpers ---- */

  /**
   * Performs page navigation (if needed) and waits for the target element.
   * Sets `isTransitioning` while waiting so the overlay can show a loading state.
   */
  async function _navigateAndWait(step: TourStep) {
    const router = useRouter();
    const currentPath = router.currentRoute.value.path;

    if (step.page && step.page !== currentPath) {
      isTransitioning.value = true;
      await router.push(step.page);
      // Give Vue a tick to render the new page
      await new Promise((r) => setTimeout(r, 100));
    }

    // Wait for the target element
    if (step.target) {
      isTransitioning.value = true;
      await waitForElement(step.target, 5000);
    }

    // Honour per-step delay
    if (step.delay) {
      await new Promise((r) => setTimeout(r, step.delay));
    }

    isTransitioning.value = false;
  }

  /* ---- actions ---- */

  async function start(tourId: string) {
    const tour = availableTours.value.find((t) => t.id === tourId);
    if (!tour || tour.steps.length === 0) return;

    _clearTimers();
    activeTour.value = tour;
    currentStepIndex.value = 0;
    isPlaying.value = tour.autoplay;
    isPaused.value = false;

    const step = tour.steps[0];
    await _navigateAndWait(step);
    step.onEnter?.();
    if (isPlaying.value) _scheduleAutoAdvance();
  }

  async function next() {
    if (!activeTour.value) return;
    if (currentStepIndex.value >= totalSteps.value - 1) {
      stop();
      return;
    }

    _clearTimers();
    currentStep.value?.onLeave?.();
    currentStepIndex.value++;
    const step = activeTour.value.steps[currentStepIndex.value];
    await _navigateAndWait(step);
    step.onEnter?.();
    if (isPlaying.value && !isPaused.value) _scheduleAutoAdvance();
  }

  async function prev() {
    if (!activeTour.value || currentStepIndex.value <= 0) return;

    _clearTimers();
    currentStep.value?.onLeave?.();
    currentStepIndex.value--;
    const step = activeTour.value.steps[currentStepIndex.value];
    await _navigateAndWait(step);
    step.onEnter?.();
    if (isPlaying.value && !isPaused.value) _scheduleAutoAdvance();
  }

  async function goToStep(index: number) {
    if (!activeTour.value) return;
    if (index < 0 || index >= totalSteps.value) return;
    if (index === currentStepIndex.value) return;

    _clearTimers();
    currentStep.value?.onLeave?.();
    currentStepIndex.value = index;
    const step = activeTour.value.steps[index];
    await _navigateAndWait(step);
    step.onEnter?.();
    if (isPlaying.value && !isPaused.value) _scheduleAutoAdvance();
  }

  function pause() {
    isPaused.value = true;
    _clearTimers();
  }

  function resume() {
    if (!activeTour.value) return;
    isPaused.value = false;
    isPlaying.value = true;
    _scheduleAutoAdvance();
  }

  function stop() {
    _clearTimers();
    currentStep.value?.onLeave?.();
    activeTour.value = null;
    currentStepIndex.value = 0;
    isPlaying.value = false;
    isPaused.value = false;
    stepProgress.value = 0;
    isTransitioning.value = false;
  }

  /* ---- restart autoplay when step changes externally ---- */
  watch(currentStepIndex, () => {
    if (isPlaying.value && !isPaused.value && activeTour.value) {
      // timer already managed in next/prev/goToStep — no-op guard
    }
  });

  /* ---- expose plugin bridge on window ---- */
  if (typeof window !== "undefined") {
    (window as any).__hubexTourEngine = {
      register: registerTour,
      start,
      stop,
    };
  }

  return {
    // state
    availableTours,
    activeTour,
    currentStepIndex,
    isPlaying,
    isPaused,
    stepProgress,
    isTransitioning,
    // computed
    currentStep,
    totalSteps,
    // actions
    registerTour,
    unregisterTour,
    start,
    next,
    prev,
    goToStep,
    pause,
    resume,
    stop,
  };
});
