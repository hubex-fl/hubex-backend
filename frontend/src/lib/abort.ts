import { onUnmounted } from "vue";

type AbortHandle = {
  signal: AbortSignal;
  abort: () => void;
};

export function createAbortHandle(): AbortHandle {
  const controller = new AbortController();
  return {
    signal: controller.signal,
    abort: () => controller.abort(),
  };
}

export function useAbortHandle(): AbortHandle {
  const handle = createAbortHandle();
  onUnmounted(() => {
    handle.abort();
  });
  return handle;
}
