export type PollerOptions = {
  pauseWhenHidden?: boolean;
};

type PollerState = {
  running: boolean;
  timer: number | null;
  paused: boolean;
  inflight: boolean;
};

export function createPoller(
  fn: () => Promise<void>,
  intervalMs: number,
  options: PollerOptions = {}
) {
  const state: PollerState = { running: false, timer: null, paused: false, inflight: false };
  const pauseWhenHidden = options.pauseWhenHidden !== false;

  const onVisibility = () => {
    if (!pauseWhenHidden) {
      return;
    }
    if (document.visibilityState === "hidden") {
      state.paused = true;
      stopTimer();
      return;
    }
    if (state.running) {
      state.paused = false;
      if (!state.inflight) {
        runOnce();
      }
    }
  };

  const stopTimer = () => {
    if (state.timer !== null) {
      window.clearTimeout(state.timer);
      state.timer = null;
    }
  };

  const schedule = () => {
    if (!state.running) return;
    // Pause subsequent polls when tab is hidden
    state.paused = pauseWhenHidden && document.visibilityState === "hidden";
    if (state.paused) return;
    stopTimer();
    state.timer = window.setTimeout(runOnce, intervalMs);
  };

  const runOnce = async () => {
    if (!state.running || state.paused || state.inflight) {
      return;
    }
    state.inflight = true;
    try {
      await fn();
    } finally {
      state.inflight = false;
      schedule();
    }
  };

  const start = () => {
    if (state.running) {
      return;
    }
    state.running = true;
    document.addEventListener("visibilitychange", onVisibility);
    // Always run the first fetch immediately, even if tab is hidden.
    // Only subsequent polls respect visibility pause.
    runOnce();
  };

  const stop = () => {
    if (!state.running) {
      return;
    }
    state.running = false;
    stopTimer();
    document.removeEventListener("visibilitychange", onVisibility);
  };

  return { start, stop };
}
