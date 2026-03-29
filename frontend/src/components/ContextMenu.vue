<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from "vue";

export interface ContextMenuItem {
  label: string;
  icon?: string;
  action: () => void;
  divider?: boolean;
  destructive?: boolean;
  disabled?: boolean;
}

const props = defineProps<{
  items: ContextMenuItem[];
  open: boolean;
}>();

const emit = defineEmits<{
  (e: "close"): void;
}>();

const menuRef = ref<HTMLElement | null>(null);

function handleOutside(e: MouseEvent) {
  if (props.open && menuRef.value && !menuRef.value.contains(e.target as Node)) {
    emit("close");
  }
}

function handleKey(e: KeyboardEvent) {
  if (props.open && e.key === "Escape") emit("close");
}

onMounted(() => {
  document.addEventListener("mousedown", handleOutside);
  document.addEventListener("keydown", handleKey);
});

onUnmounted(() => {
  document.removeEventListener("mousedown", handleOutside);
  document.removeEventListener("keydown", handleKey);
});

function run(item: ContextMenuItem) {
  if (item.disabled) return;
  emit("close");
  item.action();
}
</script>

<template>
  <div
    v-if="open"
    ref="menuRef"
    class="ctx-menu"
    role="menu"
  >
    <template v-for="(item, i) in items" :key="i">
      <div v-if="item.divider" class="ctx-divider" />
      <button
        v-else
        class="ctx-item"
        :class="{
          'ctx-item--destructive': item.destructive,
          'ctx-item--disabled': item.disabled,
        }"
        role="menuitem"
        :disabled="item.disabled"
        @click="run(item)"
      >
        <svg
          v-if="item.icon"
          class="h-3.5 w-3.5 shrink-0"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
        </svg>
        <span>{{ item.label }}</span>
      </button>
    </template>
  </div>
</template>

<style scoped>
.ctx-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 4px);
  z-index: 200;
  min-width: 180px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: 4px;
  display: flex;
  flex-direction: column;
  gap: 1px;
  animation: ctx-in 0.1s ease;
}

@keyframes ctx-in {
  from { opacity: 0; transform: translateY(-4px) scale(0.97); }
  to   { opacity: 1; transform: translateY(0)   scale(1); }
}

.ctx-divider {
  height: 1px;
  background: var(--border);
  margin: 3px 4px;
}

.ctx-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  text-align: left;
  padding: 6px 10px;
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
}

.ctx-item:hover:not(.ctx-item--disabled) {
  background: var(--bg-raised);
  color: var(--text-primary);
}

.ctx-item--destructive {
  color: var(--status-bad);
}

.ctx-item--destructive:hover:not(.ctx-item--disabled) {
  background: color-mix(in srgb, var(--status-bad) 10%, transparent);
  color: var(--status-bad);
}

.ctx-item--disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
