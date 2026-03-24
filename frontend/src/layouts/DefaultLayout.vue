<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { hasCap, useCapabilities, refreshCapabilities } from "../lib/capabilities";
import { hasToken } from "../lib/api";
import { useAbortHandle } from "../lib/abort";
import { useThemeStore } from "../stores/theme";
import { useToastStore } from "../stores/toast";
import UToast from "../components/ui/UToast.vue";
import CommandPalette from "../components/CommandPalette.vue";

const route = useRoute();
const caps = useCapabilities();
const { signal } = useAbortHandle();
const themeStore = useThemeStore();
const toastStore = useToastStore();

onMounted(() => {
  themeStore.initFromStorage();
  refreshCapabilities(signal);
});

const collapsed = ref(false);
const paletteOpen = ref(false);

function toggleSidebar() { collapsed.value = !collapsed.value; }

const navItems = computed(() => [
  { to: "/system-stage", label: "System Stage",  icon: "M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z", cap: "entities.read" },
  { to: "/devices",      label: "Devices",        icon: "M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z", cap: "devices.read" },
  { to: "/events",       label: "Events",         icon: "M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z", cap: "events.read" },
  { to: "/effects",      label: "Effects",        icon: "M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z", cap: "effects.read" },
  { to: "/trace-hub",    label: "Trace Hub",      icon: "M7.5 3.75H6A2.25 2.25 0 003.75 6v1.5M16.5 3.75H18A2.25 2.25 0 0120.25 6v1.5m0 9V18A2.25 2.25 0 0118 20.25h-1.5m-9 0H6A2.25 2.25 0 013.75 18v-1.5M15 12a3 3 0 11-6 0 3 3 0 016 0z", cap: "events.read" },
  { to: "/executions",   label: "Executions",     icon: "M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z", cap: "tasks.read" },
  { to: "/correlation",  label: "Correlation",    icon: "M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0020.25 18V6A2.25 2.25 0 0018 3.75H6A2.25 2.25 0 003.75 6v12A2.25 2.25 0 006 20.25z", cap: "tasks.read" },
  { to: "/observability",label: "Observability",  icon: "M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z M15 12a3 3 0 11-6 0 3 3 0 016 0z", cap: "devices.read" },
  { to: "/audit",        label: "Audit",          icon: "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z", cap: "audit.read" },
  { to: "/settings/auth",label: "Auth Settings",  icon: "M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75", cap: null },
  { to: "/token",        label: "Token Inspector",icon: "M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z", cap: null },
]);

const visibleNav = computed(() =>
  navItems.value.filter((item) => item.cap === null || hasCap(item.cap))
);
</script>

<template>
  <div class="min-h-screen bg-[var(--bg-base)] flex">
    <!-- Sidebar -->
    <aside
      :class="[
        'flex flex-col border-r border-[var(--border)] bg-[var(--bg-surface)] transition-all duration-300 shrink-0',
        collapsed ? 'w-14' : 'w-56',
      ]"
    >
      <!-- Logo -->
      <div class="flex items-center gap-2.5 px-3.5 h-14 border-b border-[var(--border)] shrink-0">
        <svg class="h-6 w-6 text-[var(--accent-cyan)] shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-13.5 0v-1.5m13.5 1.5v-1.5m0 0a3 3 0 00-3-3H7.5a3 3 0 00-3 3m13.5 0v-6.75a3 3 0 00-3-3H7.5a3 3 0 00-3 3v6.75" />
        </svg>
        <span
          v-if="!collapsed"
          class="font-mono font-bold text-sm tracking-widest text-[var(--text-primary)] transition-opacity"
        >
          HUBEX
        </span>
      </div>

      <!-- Nav Items -->
      <nav class="flex-1 overflow-y-auto py-2">
        <router-link
          v-for="item in visibleNav"
          :key="item.to"
          :to="item.to"
          :title="collapsed ? item.label : undefined"
          :class="[
            'flex items-center gap-2.5 px-3.5 py-2 mx-1.5 my-0.5 rounded-lg text-sm transition-colors',
            route.path.startsWith(item.to) && item.to !== '/'
              ? 'bg-[var(--accent-cyan)]/10 text-[var(--accent-cyan)]'
              : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]',
          ]"
        >
          <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
          </svg>
          <span v-if="!collapsed" class="truncate">{{ item.label }}</span>
        </router-link>
      </nav>

      <!-- Status / Collapse -->
      <div class="border-t border-[var(--border)] p-2 shrink-0">
        <button
          :title="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
          class="w-full flex items-center justify-center gap-2 px-2 py-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
          @click="toggleSidebar"
        >
          <svg class="h-4 w-4 shrink-0 transition-transform" :class="collapsed ? 'rotate-180' : ''" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
          </svg>
          <span v-if="!collapsed" class="text-xs">Collapse</span>
        </button>
      </div>
    </aside>

    <!-- Main area -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- Header -->
      <header class="h-14 border-b border-[var(--border)] flex items-center justify-between px-4 shrink-0 bg-[var(--bg-surface)]">
        <div class="flex items-center gap-2 min-w-0">
          <h1 class="text-sm font-semibold text-[var(--text-primary)] truncate">
            {{ route.meta?.title || route.path.split("/").filter(Boolean).map(s => s.replace(/-/g, " ")).join(" / ") || "Dashboard" }}
          </h1>
          <span
            v-if="caps.status !== 'ready'"
            :class="[
              'text-[10px] font-mono px-1.5 py-0.5 rounded',
              caps.status === 'loading' ? 'bg-[var(--status-info-bg)] text-[var(--status-info)]' :
              caps.status === 'error' ? 'bg-[var(--status-bad-bg)] text-[var(--status-bad)]' :
              'bg-[var(--bg-raised)] text-[var(--text-muted)]',
            ]"
          >
            {{ caps.status }}
          </span>
        </div>

        <div class="flex items-center gap-2">
          <!-- Command palette trigger -->
          <button
            class="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[var(--border)] text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:border-[var(--border-hover)] transition-colors bg-[var(--bg-raised)]"
            @click="paletteOpen = true"
          >
            <svg class="h-3 w-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
            </svg>
            <span>Search…</span>
            <span class="flex items-center gap-0.5">
              <kbd class="text-[10px] font-mono px-1 rounded border border-[var(--border)] bg-[var(--bg-surface)]">⌘</kbd>
              <kbd class="text-[10px] font-mono px-1 rounded border border-[var(--border)] bg-[var(--bg-surface)]">K</kbd>
            </span>
          </button>

          <!-- Theme toggle -->
          <button
            class="p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
            :title="themeStore.theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
            @click="themeStore.toggleTheme()"
          >
            <svg v-if="themeStore.theme === 'dark'" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
            </svg>
            <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z" />
            </svg>
          </button>

          <!-- Token status -->
          <div
            :class="[
              'h-2 w-2 rounded-full',
              hasToken() ? 'bg-[var(--status-ok)]' : 'bg-[var(--status-bad)]',
            ]"
            :title="hasToken() ? 'Token present' : 'No token'"
          />
        </div>
      </header>

      <!-- Page content -->
      <main class="flex-1 overflow-auto p-4 md:p-6">
        <slot />
      </main>
    </div>

    <!-- Toast renderer -->
    <UToast />

    <!-- Command Palette -->
    <CommandPalette v-model:open="paletteOpen" />
  </div>
</template>
