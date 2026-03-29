import { ref } from "vue";

export type ConnectEntityType = "device" | "variable" | "automation" | "alert";

export interface ConnectContext {
  type: ConnectEntityType;
  id: number | string;
  name: string;
  // device
  deviceUid?: string;
  deviceId?: number;
  // variable
  variableKey?: string;
  deviceName?: string;
}

// Module-level singleton — shared across all composable calls
const isOpen = ref(false);
const context = ref<ConnectContext | null>(null);
let clearTimer: ReturnType<typeof setTimeout> | null = null;

export function useConnectPanel() {
  function open(ctx: ConnectContext) {
    if (clearTimer !== null) {
      clearTimeout(clearTimer);
      clearTimer = null;
    }
    context.value = ctx;
    isOpen.value = true;
  }

  function close() {
    isOpen.value = false;
    clearTimer = setTimeout(() => {
      if (!isOpen.value) context.value = null;
      clearTimer = null;
    }, 300);
  }

  return { isOpen, context, open, close };
}
