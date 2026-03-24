import { useToastStore } from "../stores/toast";
import type { ToastVariant } from "../stores/toast";

/**
 * Thin wrapper around useToastStore that provides a stable API
 * for components to emit toast notifications.
 */
export function useToast() {
  let store: ReturnType<typeof useToastStore> | null = null;

  function _getStore() {
    if (!store) {
      try {
        store = useToastStore();
      } catch {
        // Pinia not available (e.g. in isolated component tests)
        return null;
      }
    }
    return store;
  }

  function add(message: string, variant: ToastVariant = "info", duration?: number): string {
    return _getStore()?.addToast(message, variant, duration) ?? "";
  }

  function success(message: string) { add(message, "success"); }
  function error(message: string)   { add(message, "error"); }
  function warn(message: string)    { add(message, "warn"); }
  function info(message: string)    { add(message, "info"); }

  return { add, success, error, warn, info };
}
