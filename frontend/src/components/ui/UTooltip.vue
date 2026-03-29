<script setup lang="ts">
import { ref } from "vue";

withDefaults(
  defineProps<{
    text: string;
    position?: "top" | "bottom" | "left" | "right";
  }>(),
  { position: "top" }
);

const visible = ref(false);

const posClasses: Record<string, string> = {
  top:    "bottom-full left-1/2 -translate-x-1/2 mb-1.5",
  bottom: "top-full left-1/2 -translate-x-1/2 mt-1.5",
  left:   "right-full top-1/2 -translate-y-1/2 mr-1.5",
  right:  "left-full top-1/2 -translate-y-1/2 ml-1.5",
};
</script>

<template>
  <span
    class="relative inline-flex"
    @mouseenter="visible = true"
    @mouseleave="visible = false"
    @focus="visible = true"
    @blur="visible = false"
  >
    <slot />
    <Transition name="tooltip">
      <span
        v-if="visible"
        :class="[
          'absolute z-50 px-2 py-1 text-xs rounded whitespace-nowrap pointer-events-none',
          'bg-[var(--bg-raised)] text-[var(--text-primary)] border border-[var(--border)] shadow-lg',
          posClasses[position],
        ]"
      >
        {{ text }}
      </span>
    </Transition>
  </span>
</template>

<style scoped>
.tooltip-enter-active,
.tooltip-leave-active { transition: opacity 0.1s ease; }
.tooltip-enter-from,
.tooltip-leave-to    { opacity: 0; }
</style>
