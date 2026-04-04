<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { useRoute } from "vue-router";
import { hasCap, useCapabilities, refreshCapabilities } from "../lib/capabilities";
import { hasToken } from "../lib/api";
import { useAbortHandle } from "../lib/abort";
import { useThemeStore } from "../stores/theme";
import { useToastStore } from "../stores/toast";
import { useServerHealthStore } from "../stores/serverHealth";
import UToast from "../components/ui/UToast.vue";
import UOfflineBanner from "../components/ui/UOfflineBanner.vue";
import CommandPalette from "../components/CommandPalette.vue";
import NotificationBell from "../components/NotificationBell.vue";
import WelcomeScreen from "../components/WelcomeScreen.vue";
import { useWebSocket } from "../composables/useWebSocket";
import { usePreferencesStore } from "../stores/preferences";

const route = useRoute();
const caps = useCapabilities();
const { signal } = useAbortHandle();
const themeStore = useThemeStore();
const toastStore = useToastStore();
const serverHealth = useServerHealthStore();

const ws = useWebSocket();
const prefsStore = usePreferencesStore();

// Collapsible sidebar groups
const collapsedGroups = ref<Set<string>>(new Set());
const showNewMenu = ref(false);

function toggleGroup(label: string) {
  if (label === "Haupt") return; // Haupt always open
  const next = new Set(collapsedGroups.value);
  if (next.has(label)) next.delete(label);
  else next.add(label);
  collapsedGroups.value = next;
  prefsStore.update("sidebar_collapsed_groups", [...next]);
}

function isGroupCollapsed(label: string): boolean {
  return collapsedGroups.value.has(label);
}

// User menu in header
const showUserMenu = ref(false);

function handleSignOut() {
  showUserMenu.value = false;
  import("../lib/api").then(({ clearToken }) => {
    clearToken();
    window.location.href = "/login";
  });
}

// Welcome screen
const showWelcome = computed(() =>
  hasToken() && prefsStore.loaded && prefsStore.get("onboarding_completed", false) === false
);

onMounted(async () => {
  themeStore.initFromStorage();
  refreshCapabilities(signal);
  ws.start();
  await prefsStore.load();
  // Restore collapsed groups from preferences (default: Daten + System collapsed)
  const saved = prefsStore.get<string[]>("sidebar_collapsed_groups", null);
  if (saved !== null) {
    collapsedGroups.value = new Set(saved);
  } else {
    collapsedGroups.value = new Set(["Daten", "System"]);
  }
});

// Show "reconnected" toast when server comes back online
watch(() => serverHealth.serverOnline, (online, wasOnline) => {
  if (online && wasOnline === false) {
    toastStore.addToast("Server reconnected", "success", 3000);
  }
});

const collapsed = ref(false);
const mobileOpen = ref(false);
const paletteOpen = ref(false);

function toggleSidebar() { collapsed.value = !collapsed.value; }
function openMobileSidebar() { mobileOpen.value = true; }
function closeMobileSidebar() { mobileOpen.value = false; }

type NavItem = {
  to: string;
  label: string;
  icon: string;
  cap: string | null;
  comingSoon?: boolean;
};
type NavGroup = { label: string; items: NavItem[] };

const navGroups: NavGroup[] = [
  {
    label: "Haupt",
    items: [
      { to: "/",         label: "Dashboard", icon: "M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25", cap: null },
      { to: "/devices",  label: "Devices",   icon: "M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z", cap: "devices.read" },
      { to: "/dashboards", label: "Dashboards", icon: "M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0112 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375z", cap: "dashboards.read" },
    ],
  },
  {
    label: "Daten",
    items: [
      { to: "/variables",  label: "Variables",    icon: "M4.5 12.75l7.5-7.5 7.5 7.5m-15 6l7.5-7.5 7.5 7.5", cap: "vars.read" },
      { to: "/entities",   label: "Entities",     icon: "M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z", cap: "entities.read" },
      { to: "/alerts",     label: "Alerts",       icon: "M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0", cap: "alerts.read" },
      { to: "/automations", label: "Automations", icon: "M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z", cap: null },
    ],
  },
  {
    label: "System",
    items: [
      { to: "/settings", label: "Settings", icon: "M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z M15 12a3 3 0 11-6 0 3 3 0 016 0z", cap: null },
      { to: "/developer", label: "API Docs", icon: "M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z", cap: null },
      { to: "/events",       label: "Events",      icon: "M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z", cap: "events.read" },
      { to: "/audit",        label: "Audit",       icon: "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z", cap: "audit.read" },
      { to: "/system-health", label: "System Health", icon: "M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z", cap: null },
      { to: "/settings/types", label: "Semantic Types", icon: "M9.568 3H5.25A2.25 2.25 0 003 5.25v4.318c0 .597.237 1.17.659 1.591l9.581 9.581c.699.699 1.78.872 2.607.33a18.095 18.095 0 005.223-5.223c.542-.827.369-1.908-.33-2.607L11.16 3.66A2.25 2.25 0 009.568 3z M6 6h.008v.008H6V6z", cap: null },
    ],
  },
];

const visibleNavGroups = computed<NavGroup[]>(() =>
  navGroups
    .map((g) => ({
      ...g,
      items: g.items.filter((item) => item.comingSoon || item.cap === null || hasCap(item.cap)),
    }))
    .filter((g) => g.items.length > 0)
);

function handleNavClick() {
  mobileOpen.value = false;
}
</script>

<template>
  <div class="min-h-screen bg-[var(--bg-base)] flex">

    <!-- Offline banner -->
    <UOfflineBanner />

    <!-- Mobile backdrop -->
    <Transition name="backdrop">
      <div
        v-if="mobileOpen"
        class="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm md:hidden"
        @click="closeMobileSidebar"
      />
    </Transition>

    <!-- Sidebar — desktop: static, mobile: overlay -->
    <aside
      :class="[
        'flex flex-col border-r border-[var(--border)] bg-[var(--bg-surface)] transition-all duration-300 shrink-0',
        // Desktop: normal sidebar (collapsed / expanded)
        'hidden md:flex',
        collapsed ? 'md:w-14' : 'md:w-56',
      ]"
    >
      <!-- Logo -->
      <div class="flex items-center gap-2.5 px-3.5 h-14 border-b border-[var(--border)] shrink-0">
        <svg class="h-6 w-6 text-[var(--primary)] shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-13.5 0v-1.5m13.5 1.5v-1.5m0 0a3 3 0 00-3-3H7.5a3 3 0 00-3 3m13.5 0v-6.75a3 3 0 00-3-3H7.5a3 3 0 00-3 3v6.75" />
        </svg>
        <span
          v-if="!collapsed"
          class="font-mono font-bold text-sm tracking-widest text-[var(--text-primary)] transition-opacity"
        >
          HUBEX
        </span>
      </div>

      <!-- + New Button -->
      <div v-if="!collapsed" class="px-2.5 pt-2 pb-1">
        <div class="relative">
          <button
            class="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)]/10 text-[var(--primary)] hover:bg-[var(--primary)]/20 transition-colors"
            @click="showNewMenu = !showNewMenu"
          >
            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
            New
          </button>
          <div
            v-if="showNewMenu"
            class="absolute left-0 right-0 top-full mt-1 z-50 rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] shadow-lg py-1"
          >
            <router-link to="/devices?wizard=open" class="flex items-center gap-2 px-3 py-1.5 text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]" @click="showNewMenu = false">
              <span>+ Device</span>
            </router-link>
            <router-link to="/automations?create=true" class="flex items-center gap-2 px-3 py-1.5 text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]" @click="showNewMenu = false">
              <span>+ Automation</span>
            </router-link>
            <router-link to="/alerts?create=true" class="flex items-center gap-2 px-3 py-1.5 text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]" @click="showNewMenu = false">
              <span>+ Alert Rule</span>
            </router-link>
            <router-link to="/dashboards?create=true" class="flex items-center gap-2 px-3 py-1.5 text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]" @click="showNewMenu = false">
              <span>+ Dashboard</span>
            </router-link>
          </div>
        </div>
      </div>
      <div v-else class="px-2 pt-2 pb-1">
        <button
          class="w-full flex items-center justify-center p-1.5 rounded-lg text-[var(--primary)] hover:bg-[var(--primary)]/10 transition-colors"
          title="Create new..."
          @click="showNewMenu = !showNewMenu"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
        </button>
      </div>

      <!-- Nav Items -->
      <nav class="flex-1 overflow-y-auto py-2">
        <template v-for="group in visibleNavGroups" :key="group.label">
          <!-- Section label — clickable to collapse (except Core) -->
          <button
            v-if="!collapsed"
            :class="[
              'w-full flex items-center justify-between text-[10px] uppercase tracking-widest font-semibold text-[var(--text-muted)] px-3.5 pb-1 mt-3 first:mt-1',
              group.label !== 'Haupt' ? 'cursor-pointer hover:text-[var(--text-primary)]' : 'cursor-default',
            ]"
            @click="toggleGroup(group.label)"
          >
            <span>{{ group.label }}</span>
            <svg
              v-if="group.label !== 'Haupt'"
              :class="['h-3 w-3 transition-transform duration-200', isGroupCollapsed(group.label) ? '-rotate-90' : '']"
              fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
            </svg>
          </button>
          <!-- Collapsed sidebar: subtle divider between groups -->
          <div v-else class="my-1 mx-2 border-t border-[var(--border)] opacity-40 first:hidden" />

          <template v-for="item in group.items" :key="item.to">
            <!-- Coming Soon item (non-interactive) -->
            <div
              v-if="item.comingSoon"
              v-show="!isGroupCollapsed(group.label)"
              :title="collapsed ? item.label + ' — Coming Soon' : undefined"
              class="flex items-center gap-2.5 px-3.5 py-2.5 mx-1.5 my-0.5 rounded-lg text-sm opacity-40 cursor-not-allowed select-none"
            >
              <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
              </svg>
              <span v-if="!collapsed" class="truncate flex-1 text-[var(--text-muted)]">{{ item.label }}</span>
              <span v-if="!collapsed" class="text-[9px] font-semibold px-1 py-0.5 rounded bg-[var(--bg-raised)] text-[var(--text-muted)] shrink-0">Soon</span>
            </div>
            <!-- Normal nav item -->
            <router-link
              v-else
              v-show="!isGroupCollapsed(group.label)"
              :to="item.to"
              :title="item.label"
              :class="[
                'flex items-center gap-2.5 px-3.5 py-2.5 mx-1.5 my-0.5 rounded-lg text-sm transition-colors',
                (item.to === '/' ? route.path === '/' : route.path.startsWith(item.to))
                  ? 'bg-[var(--primary)]/10 text-[var(--primary)]'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]',
              ]"
            >
              <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
              </svg>
              <span v-if="!collapsed" class="truncate">{{ item.label }}</span>
            </router-link>
          </template>
        </template>
      </nav>

      <!-- Collapse button -->
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

    <!-- Mobile Sidebar (overlay) -->
    <Transition name="slide">
      <aside
        v-if="mobileOpen"
        class="fixed inset-y-0 left-0 z-40 w-64 flex flex-col border-r border-[var(--border)] bg-[var(--bg-surface)] md:hidden"
      >
        <!-- Logo + close -->
        <div class="flex items-center justify-between px-3.5 h-14 border-b border-[var(--border)] shrink-0">
          <div class="flex items-center gap-2.5">
            <svg class="h-6 w-6 text-[var(--primary)] shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-13.5 0v-1.5m13.5 1.5v-1.5m0 0a3 3 0 00-3-3H7.5a3 3 0 00-3 3m13.5 0v-6.75a3 3 0 00-3-3H7.5a3 3 0 00-3 3v6.75" />
            </svg>
            <span class="font-mono font-bold text-sm tracking-widest text-[var(--text-primary)]">HUBEX</span>
          </div>
          <button
            class="p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
            @click="closeMobileSidebar"
            aria-label="Close menu"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Nav Items -->
        <nav class="flex-1 overflow-y-auto py-2">
          <template v-for="group in visibleNavGroups" :key="group.label">
            <div class="text-[10px] uppercase tracking-widest font-semibold text-[var(--text-muted)] px-4 pb-1 mt-3 first:mt-1">
              {{ group.label }}
            </div>
            <template v-for="item in group.items" :key="item.to">
              <!-- Coming Soon (mobile) -->
              <div
                v-if="item.comingSoon"
                class="flex items-center gap-3 px-4 py-3 mx-2 my-0.5 rounded-lg text-sm opacity-40 cursor-not-allowed select-none"
              >
                <svg class="h-5 w-5 shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
                </svg>
                <span class="truncate flex-1 text-[var(--text-muted)]">{{ item.label }}</span>
                <span class="text-[9px] font-semibold px-1 py-0.5 rounded bg-[var(--bg-raised)] text-[var(--text-muted)] shrink-0">Soon</span>
              </div>
              <!-- Normal link (mobile) -->
              <router-link
                v-else
                :to="item.to"
                :class="[
                  'flex items-center gap-3 px-4 py-3 mx-2 my-0.5 rounded-lg text-sm transition-colors',
                  (item.to === '/' ? route.path === '/' : route.path.startsWith(item.to))
                    ? 'bg-[var(--primary)]/10 text-[var(--primary)]'
                    : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]',
                ]"
                @click="handleNavClick"
              >
                <svg class="h-5 w-5 shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
                </svg>
                <span class="truncate">{{ item.label }}</span>
              </router-link>
            </template>
          </template>
        </nav>
      </aside>
    </Transition>

    <!-- Main area -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- Header -->
      <header class="h-14 border-b border-[var(--border)] flex items-center justify-between px-4 shrink-0 bg-[var(--bg-surface)]">
        <div class="flex items-center gap-2 min-w-0">
          <!-- Hamburger (mobile only) -->
          <button
            class="md:hidden p-2 -ml-1 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
            aria-label="Open menu"
            @click="openMobileSidebar"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>

          <h1 class="text-sm font-semibold text-[var(--text-primary)] truncate">
            {{ route.meta?.title || route.path.split("/").filter(Boolean).map(s => s.replace(/-/g, " ")).join(" / ") || "Dashboard" }}
          </h1>
          <span
            v-if="caps.status !== 'ready'"
            :class="[
              'text-[10px] font-mono px-1.5 py-0.5 rounded hidden sm:inline',
              caps.status === 'loading' ? 'bg-[var(--status-info-bg)] text-[var(--status-info)]' :
              caps.status === 'error' ? 'bg-[var(--status-bad-bg)] text-[var(--status-bad)]' :
              'bg-[var(--bg-raised)] text-[var(--text-muted)]',
            ]"
          >
            {{ caps.status }}
          </span>
        </div>

        <div class="flex items-center gap-2">
          <!-- Command palette trigger (desktop only) -->
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

          <!-- Notification Bell -->
          <NotificationBell v-if="hasToken()" />

          <!-- User menu with Sign Out -->
          <div v-if="hasToken()" class="relative">
            <button
              class="flex items-center gap-1 p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
              title="Account"
              @click="showUserMenu = !showUserMenu"
            >
              <div class="h-6 w-6 rounded-full bg-[var(--primary)]/20 text-[var(--primary)] flex items-center justify-center text-[10px] font-bold">
                {{ hasToken() ? 'U' : '?' }}
              </div>
            </button>
            <div
              v-if="showUserMenu"
              class="absolute right-0 top-full mt-1 z-50 w-44 rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] shadow-xl py-1"
            >
              <router-link
                to="/settings"
                class="flex items-center gap-2 px-3 py-2 text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]"
                @click="showUserMenu = false"
              >
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                Settings
              </router-link>
              <div class="border-t border-[var(--border)] my-1" />
              <button
                class="w-full flex items-center gap-2 px-3 py-2 text-xs text-red-400 hover:bg-red-500/10"
                @click="handleSignOut"
              >
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" /></svg>
                Sign out
              </button>
            </div>
          </div>
          <!-- Unauthenticated dot -->
          <div v-else class="h-2 w-2 rounded-full bg-[var(--status-bad)]" title="Not signed in" />
        </div>
      </header>

      <!-- Page content -->
      <main class="flex-1 overflow-auto p-3 md:p-6 relative">
        <!-- Dim overlay when server is offline -->
        <div
          v-if="!serverHealth.serverOnline"
          class="absolute inset-0 bg-[var(--bg-base)]/60 z-10 pointer-events-none"
        />
        <slot />
      </main>
    </div>

    <!-- Toast renderer -->
    <UToast />

    <!-- Command Palette -->
    <CommandPalette v-model:open="paletteOpen" />

    <!-- Welcome Screen (first login only) -->
    <WelcomeScreen v-if="showWelcome" />
  </div>
</template>

<style scoped>
.backdrop-enter-active,
.backdrop-leave-active { transition: opacity 0.2s ease; }
.backdrop-enter-from,
.backdrop-leave-to     { opacity: 0; }

.slide-enter-active,
.slide-leave-active { transition: transform 0.25s ease; }
.slide-enter-from,
.slide-leave-to     { transform: translateX(-100%); }
</style>
