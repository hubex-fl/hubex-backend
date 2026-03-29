<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from "vue";
import { useRouter } from "vue-router";
import { hasCap } from "../lib/capabilities";

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{ (e: "update:open", v: boolean): void }>();

const router = useRouter();
const query = ref("");
const activeIndex = ref(0);
const inputRef = ref<HTMLInputElement | null>(null);

interface Command {
  id: string;
  label: string;
  description?: string;
  icon: string;
  action: () => void;
  cap?: string;
}

const allCommands: Command[] = [
  { id: "system-stage", label: "System Stage",    description: "View entities and device state", icon: "M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z", action: () => router.push("/system-stage"), cap: "entities.read" },
  { id: "devices",      label: "Devices",          description: "Browse and manage devices",       icon: "M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z", action: () => router.push("/devices"), cap: "devices.read" },
  { id: "events",       label: "Events",            description: "View event stream",               icon: "M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z", action: () => router.push("/events"), cap: "events.read" },
  { id: "effects",      label: "Effects",           description: "Browse effect definitions",       icon: "M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z", action: () => router.push("/effects"), cap: "effects.read" },
  { id: "trace-hub",    label: "Trace Hub",         description: "Trace events and effects",        icon: "M7.5 3.75H6A2.25 2.25 0 003.75 6v1.5M16.5 3.75H18A2.25 2.25 0 0120.25 6v1.5m0 9V18A2.25 2.25 0 0118 20.25h-1.5m-9 0H6A2.25 2.25 0 013.75 18v-1.5M15 12a3 3 0 11-6 0 3 3 0 016 0z", action: () => router.push("/trace-hub"), cap: "events.read" },
  { id: "executions",   label: "Executions",        description: "View task executions",            icon: "M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z", action: () => router.push("/executions"), cap: "tasks.read" },
  { id: "correlation",  label: "Correlation",       description: "Correlate tasks and effects",     icon: "M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0020.25 18V6A2.25 2.25 0 0018 3.75H6A2.25 2.25 0 003.75 6v12A2.25 2.25 0 006 20.25z", action: () => router.push("/correlation"), cap: "tasks.read" },
  { id: "observability",label: "Observability",     description: "Monitor device metrics",          icon: "M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z M15 12a3 3 0 11-6 0 3 3 0 016 0z", action: () => router.push("/observability"), cap: "devices.read" },
  { id: "audit",        label: "Audit Log",         description: "Browse audit trail",              icon: "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z", action: () => router.push("/audit"), cap: "audit.read" },
  { id: "settings",     label: "Auth Settings",     description: "Configure authentication",        icon: "M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75", action: () => router.push("/settings/auth") },
  { id: "token",        label: "Token Inspector",   description: "Inspect JWT token",               icon: "M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z", action: () => router.push("/token") },
];

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase();
  const base = allCommands.filter((c) => c.cap == null || hasCap(c.cap));
  if (!q) return base;
  return base.filter(
    (c) =>
      c.label.toLowerCase().includes(q) ||
      (c.description || "").toLowerCase().includes(q)
  );
});

watch(filtered, () => { activeIndex.value = 0; });

watch(
  () => props.open,
  async (v) => {
    if (v) {
      query.value = "";
      activeIndex.value = 0;
      await nextTick();
      inputRef.value?.focus();
    }
  }
);

function close() { emit("update:open", false); }

function run(cmd: Command) {
  cmd.action();
  close();
}

function onKey(e: KeyboardEvent) {
  if (!props.open) {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      emit("update:open", true);
    }
    return;
  }
  if (e.key === "Escape")    { e.preventDefault(); close(); }
  if (e.key === "ArrowDown") { e.preventDefault(); activeIndex.value = (activeIndex.value + 1) % filtered.value.length; }
  if (e.key === "ArrowUp")   { e.preventDefault(); activeIndex.value = (activeIndex.value - 1 + filtered.value.length) % filtered.value.length; }
  if (e.key === "Enter" && filtered.value[activeIndex.value]) {
    e.preventDefault();
    run(filtered.value[activeIndex.value]);
  }
}

onMounted(()   => window.addEventListener("keydown", onKey));
onUnmounted(() => window.removeEventListener("keydown", onKey));
</script>

<template>
  <Teleport to="body">
    <Transition name="palette">
      <div
        v-if="open"
        class="fixed inset-0 z-[200] flex items-start justify-center pt-[20vh] px-4"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="close" />

        <!-- Panel -->
        <div
          class="relative w-full max-w-xl bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl shadow-2xl overflow-hidden"
          @click.stop
        >
          <!-- Search input -->
          <div class="flex items-center gap-3 px-4 py-3 border-b border-[var(--border)]">
            <svg class="h-4 w-4 text-[var(--text-muted)] shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
            </svg>
            <input
              ref="inputRef"
              v-model="query"
              type="text"
              placeholder="Search commands…"
              class="flex-1 bg-transparent text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none"
            />
            <kbd class="text-[10px] font-mono px-1.5 py-0.5 rounded border border-[var(--border)] bg-[var(--bg-raised)] text-[var(--text-muted)]">
              Esc
            </kbd>
          </div>

          <!-- Results -->
          <ul class="max-h-72 overflow-y-auto py-1" role="listbox">
            <li v-if="filtered.length === 0" class="px-4 py-8 text-center text-sm text-[var(--text-muted)]">
              No results for "{{ query }}"
            </li>
            <li
              v-else
              v-for="(cmd, i) in filtered"
              :key="cmd.id"
              role="option"
              :aria-selected="i === activeIndex"
              :class="[
                'flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors',
                i === activeIndex
                  ? 'bg-[var(--primary)]/10 text-[var(--primary)]'
                  : 'text-[var(--text-primary)] hover:bg-[var(--bg-raised)]',
              ]"
              @mouseenter="activeIndex = i"
              @click="run(cmd)"
            >
              <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" :d="cmd.icon" />
              </svg>
              <div class="flex-1 min-w-0">
                <span class="text-sm font-medium">{{ cmd.label }}</span>
                <span v-if="cmd.description" class="ml-2 text-xs text-[var(--text-muted)]">{{ cmd.description }}</span>
              </div>
              <svg v-if="i === activeIndex" class="h-3 w-3 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path d="M9 18l6-6-6-6" />
              </svg>
            </li>
          </ul>

          <!-- Footer hint -->
          <div class="flex items-center gap-3 px-4 py-2 border-t border-[var(--border)] text-[10px] text-[var(--text-muted)]">
            <span class="flex items-center gap-1">
              <kbd class="font-mono px-1 rounded border border-[var(--border)] bg-[var(--bg-raised)]">↑↓</kbd> navigate
            </span>
            <span class="flex items-center gap-1">
              <kbd class="font-mono px-1 rounded border border-[var(--border)] bg-[var(--bg-raised)]">↵</kbd> select
            </span>
            <span class="flex items-center gap-1">
              <kbd class="font-mono px-1 rounded border border-[var(--border)] bg-[var(--bg-raised)]">Esc</kbd> close
            </span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.palette-enter-active,
.palette-leave-active { transition: all 0.15s ease; }
.palette-enter-from,
.palette-leave-to     { opacity: 0; }
.palette-enter-from .relative,
.palette-leave-to .relative { transform: scale(0.97) translateY(-8px); }
</style>
