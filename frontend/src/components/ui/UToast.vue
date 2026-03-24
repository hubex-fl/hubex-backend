<script setup lang="ts">
import { useToastStore } from "../../stores/toast";
import type { Toast, ToastVariant } from "../../stores/toast";
import { TransitionGroup } from "vue";

const store = useToastStore();

const icons: Record<ToastVariant, string> = {
  success: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
  error:   "M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z",
  warn:    "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z",
  info:    "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
};

const colors: Record<ToastVariant, string> = {
  success: "border-[var(--status-ok)]/30 bg-[var(--status-ok-bg)] text-[var(--status-ok)]",
  error:   "border-[var(--status-bad)]/30 bg-[var(--status-bad-bg)] text-[var(--status-bad)]",
  warn:    "border-[var(--status-warn)]/30 bg-[var(--status-warn-bg)] text-[var(--status-warn)]",
  info:    "border-[var(--status-info)]/30 bg-[var(--status-info-bg)] text-[var(--status-info)]",
};
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 w-80 pointer-events-none"
      aria-live="polite"
    >
      <TransitionGroup name="toast">
        <div
          v-for="toast in store.toasts"
          :key="toast.id"
          :class="[
            'pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-lg border shadow-lg',
            'bg-[var(--bg-surface)] border-[var(--border)]',
          ]"
          role="alert"
        >
          <svg
            :class="['h-5 w-5 shrink-0 mt-0.5', colors[toast.variant].split(' ').slice(-1)]"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" :d="icons[toast.variant]" />
          </svg>
          <p class="flex-1 text-sm text-[var(--text-primary)]">{{ toast.message }}</p>
          <button
            class="shrink-0 p-0.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
            aria-label="Dismiss"
            @click="store.removeToast(toast.id)"
          >
            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active { transition: all 0.25s ease; }
.toast-enter-from   { opacity: 0; transform: translateX(100%); }
.toast-leave-to     { opacity: 0; transform: translateX(100%); }
.toast-move         { transition: transform 0.25s ease; }
</style>
