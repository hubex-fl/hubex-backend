<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";

export interface DropdownItem {
  label: string;
  icon?: string;
  danger?: boolean;
  disabled?: boolean;
  onClick: () => void;
}

withDefaults(
  defineProps<{
    items: DropdownItem[];
    align?: "left" | "right";
  }>(),
  { align: "right" }
);

const open = ref(false);
const container = ref<HTMLElement | null>(null);

function toggle() { open.value = !open.value; }
function close()  { open.value = false; }

function onClickOutside(e: MouseEvent) {
  if (container.value && !container.value.contains(e.target as Node)) close();
}

onMounted(()   => document.addEventListener("click", onClickOutside));
onUnmounted(() => document.removeEventListener("click", onClickOutside));
</script>

<template>
  <div ref="container" class="relative inline-block">
    <div @click.stop="toggle">
      <slot :open="open" />
    </div>
    <Transition name="dropdown">
      <div
        v-if="open"
        :class="[
          'absolute z-50 mt-1 min-w-[10rem] py-1 rounded-lg border shadow-lg',
          'bg-[var(--bg-surface)] border-[var(--border)]',
          align === 'right' ? 'right-0' : 'left-0',
        ]"
      >
        <button
          v-for="item in items"
          :key="item.label"
          :disabled="item.disabled"
          class="w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors text-left"
          :class="[
            item.danger
              ? 'text-[var(--status-bad)] hover:bg-[var(--status-bad-bg)]'
              : 'text-[var(--text-primary)] hover:bg-[var(--bg-raised)]',
            item.disabled && 'opacity-40 cursor-not-allowed',
          ]"
          @click="() => { item.onClick(); close(); }"
        >
          <span v-if="item.icon" v-html="item.icon" class="h-4 w-4 shrink-0" />
          {{ item.label }}
        </button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.dropdown-enter-active,
.dropdown-leave-active { transition: all 0.1s ease; }
.dropdown-enter-from,
.dropdown-leave-to     { opacity: 0; transform: translateY(-4px); }
</style>
