import { defineStore } from "pinia";
import { ref } from "vue";
import { useServerHealthStore } from "./serverHealth";

export type ToastVariant = "success" | "error" | "info" | "warn";

export interface Toast {
  id: string;
  variant: ToastVariant;
  message: string;
  duration?: number;
}

let _counter = 0;

export const useToastStore = defineStore("toast", () => {
  const toasts = ref<Toast[]>([]);

  function addToast(
    message: string,
    variant: ToastVariant = "info",
    duration = 5000
  ): string {
    // Suppress error toasts while server is offline — the banner already explains it
    if (variant === "error" && !useServerHealthStore().serverOnline) {
      return "";
    }
    const id = `toast-${++_counter}`;
    toasts.value.push({ id, message, variant, duration });
    if (duration > 0) {
      setTimeout(() => removeToast(id), duration);
    }
    return id;
  }

  function removeToast(id: string): void {
    const idx = toasts.value.findIndex((t) => t.id === id);
    if (idx !== -1) toasts.value.splice(idx, 1);
  }

  return { toasts, addToast, removeToast };
});
