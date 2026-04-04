<script setup lang="ts">
import { onMounted, onUnmounted, watch } from "vue";

type Size = "sm" | "md" | "lg" | "fullscreen";

const props = withDefaults(
  defineProps<{
    open: boolean;
    size?: Size;
    title?: string;
  }>(),
  { size: "md" }
);

const emit = defineEmits<{ (e: "close"): void }>();

const maxWidths: Record<Size, string> = {
  sm: "max-w-sm",
  md: "max-w-2xl",
  lg: "max-w-5xl",
  fullscreen: "max-w-full",
};

function onKey(e: KeyboardEvent) {
  if (e.key === "Escape" && props.open) emit("close");
}

onMounted(() => window.addEventListener("keydown", onKey));
onUnmounted(() => window.removeEventListener("keydown", onKey));

watch(
  () => props.open,
  (v) => {
    document.body.style.overflow = v ? "hidden" : "";
  }
);
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        :aria-label="title"
      >
        <!-- Backdrop -->
        <div
          class="absolute inset-0 bg-black/80 backdrop-blur-sm"
          @click="emit('close')"
        />
        <!-- Panel -->
        <div
          :class="[
            'relative w-full bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl shadow-2xl animate-slide-in',
            maxWidths[size],
            size === 'fullscreen' && 'h-full rounded-none',
          ]"
        >
          <!-- Header -->
          <div v-if="title || $slots.header" class="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
            <slot name="header">
              <h2 class="text-base font-semibold text-[var(--text-primary)]">{{ title }}</h2>
            </slot>
            <button
              class="p-1 rounded text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
              aria-label="Close"
              @click="emit('close')"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
          <!-- Body -->
          <div class="p-5">
            <slot />
          </div>
          <!-- Footer -->
          <div v-if="$slots.footer" class="px-5 pb-5">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.15s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
