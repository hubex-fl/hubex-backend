<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from "vue";
import { useRoute } from "vue-router";
import { hasCap, useCapabilities, refreshCapabilities } from "../lib/capabilities";
import { hasToken } from "../lib/api";
import { useAbortHandle } from "../lib/abort";
import { useThemeStore } from "../stores/theme";
import { useToastStore } from "../stores/toast";
import { useServerHealthStore } from "../stores/serverHealth";
import UToast from "../components/ui/UToast.vue";
import { branding, loadOrgBranding } from "../lib/branding";
import { useAuthStore } from "../stores/auth";
import { useI18n } from "vue-i18n";
import UOfflineBanner from "../components/ui/UOfflineBanner.vue";
import CommandPalette from "../components/CommandPalette.vue";
import NotificationBell from "../components/NotificationBell.vue";
import WelcomeScreen from "../components/WelcomeScreen.vue";
import TourOverlay from "../components/tour/TourOverlay.vue";
import TourLauncher from "../components/tour/TourLauncher.vue";
import AiCoopIndicator from "../components/AiCoopIndicator.vue";
import { useWebSocket } from "../composables/useWebSocket";
import { handleAiCommand } from "../composables/useAiCommands";
import { usePreferencesStore } from "../stores/preferences";
import { useTourStore } from "../stores/tour";
import { registerBuiltinTours } from "../lib/tours/builtin-tours";
import { useLimitsStore } from "../stores/limits";
import { useFeaturesStore } from "../stores/features";

const route = useRoute();
const caps = useCapabilities();
const { signal } = useAbortHandle();
const themeStore = useThemeStore();
const toastStore = useToastStore();
const serverHealth = useServerHealthStore();
const authStore = useAuthStore();
const { t } = useI18n();

const ws = useWebSocket();
const prefsStore = usePreferencesStore();
const tourStore = useTourStore();
const limitsStore = useLimitsStore();
const featuresStore = useFeaturesStore();

// Sprint 3.6 — top-bar title is now locale-aware.
// Routes can provide either:
//   meta.titleKey: 'nav.devices'  (preferred, translated on the fly)
//   meta.title: 'Devices'         (fallback for legacy routes not yet migrated)
// If neither, falls back to path-based pretty-print, then literal "Dashboard".
const topBarTitle = computed(() => {
  const key = (route.meta as { titleKey?: string } | undefined)?.titleKey;
  if (key) {
    const translated = t(key);
    // vue-i18n returns the key verbatim on missing-key; fall through to title/path in that case
    if (translated && translated !== key) return translated;
  }
  const fallback = (route.meta as { title?: string } | undefined)?.title;
  if (fallback) return fallback;
  const fromPath = route.path
    .split("/")
    .filter(Boolean)
    .map((s) => s.replace(/-/g, " "))
    .join(" / ");
  return fromPath || "Dashboard";
});

// Collapsible sidebar groups
const collapsedGroups = ref<Set<string>>(new Set(["Tools", "System"]));
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
// Sprint 10 T5: load user info for the account dropdown
const userDisplayName = ref<string | null>(null);
const userEmail = ref("");

// Org-Switcher state
interface OrgInfo { id: number; name: string; slug: string; }
const userOrgs = ref<OrgInfo[]>([]);
const currentOrgId = ref<number | null>(null);
const currentOrgName = computed(() => {
  const org = userOrgs.value.find(o => o.id === currentOrgId.value);
  return org?.name || "";
});
const showOrgSwitcher = computed(() => userOrgs.value.length > 1);
const switchingOrg = ref(false);

async function switchOrg(orgId: number) {
  if (orgId === currentOrgId.value || switchingOrg.value) return;
  switchingOrg.value = true;
  try {
    const { apiFetch, setToken } = await import("../lib/api");
    const resp = await apiFetch<{ access_token: string }>("/api/v1/auth/switch-org", {
      method: "POST",
      body: JSON.stringify({ org_id: orgId }),
    });
    setToken(resp.access_token);
    currentOrgId.value = orgId;
    showUserMenu.value = false;
    // Reload page to reflect new org context
    window.location.reload();
  } catch (e) {
    console.error("Failed to switch org:", e);
  } finally {
    switchingOrg.value = false;
  }
}

onMounted(async () => {
  if (hasToken()) {
    try {
      const { apiFetch } = await import("../lib/api");
      const me = await apiFetch<{ email: string; display_name?: string | null }>("/api/v1/users/me");
      userDisplayName.value = me.display_name || null;
      userEmail.value = me.email;

      // Get current org_id from JWT token via auth store
      const authStore = await import("../stores/auth").then(m => m.useAuthStore());
      currentOrgId.value = authStore.orgId;

      // Load user's orgs for the switcher
      const orgs = await apiFetch<OrgInfo[]>("/api/v1/orgs");
      userOrgs.value = orgs;
      // If no current org from token, use first org
      if (!currentOrgId.value && orgs.length > 0) {
        currentOrgId.value = orgs[0].id;
      }
    } catch { /* ignore */ }
  }
});
const userInitial = computed(() => {
  const name = userDisplayName.value || userEmail.value;
  return name ? name.charAt(0).toUpperCase() : "U";
});

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
  // Wire AI Coop command handler
  ws.onUiCommand((cmd) => handleAiCommand(cmd));
  // Register built-in guided tours
  registerBuiltinTours((tour) => tourStore.registerTour(tour));
  // Load org branding on page refresh (when already logged in)
  if (authStore.orgId) loadOrgBranding(authStore.orgId);
  // Load edition limits
  if (hasToken()) limitsStore.load();
  // Load feature flags (runtime subsystem toggles)
  if (hasToken()) featuresStore.load().catch(() => { /* fail-open */ });
  await prefsStore.load();
  // Restore collapsed groups from preferences (default: Daten + System collapsed)
  const saved = prefsStore.get<string[]>("sidebar_collapsed_groups", null);
  if (saved !== null) {
    collapsedGroups.value = new Set(saved);
  } else {
    collapsedGroups.value = new Set(["Tools", "System"]);
  }

  // Auto-start onboarding tour for first-time users
  // BUT only if the Welcome Screen is NOT currently showing —
  // otherwise both overlap and confuse the user.
  if (hasToken() && !localStorage.getItem("hubex_tour_seen") && !showWelcome.value) {
    await nextTick();
    // Small delay to let the dashboard render before starting the tour
    setTimeout(() => {
      tourStore.start("getting-started");
    }, 1200);
  }
});

// When the Welcome Screen is dismissed, start the onboarding tour
// (only if the user hasn't already seen it).
watch(showWelcome, (isVisible, wasVisible) => {
  if (wasVisible && !isVisible && !localStorage.getItem("hubex_tour_seen")) {
    setTimeout(() => {
      tourStore.start("getting-started");
    }, 800);
  }
});

// Mark onboarding tour as seen when it finishes or is dismissed
watch(() => tourStore.activeTour, (newTour, oldTour) => {
  if (oldTour?.id === "getting-started" && !newTour) {
    localStorage.setItem("hubex_tour_seen", "true");
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

type NavChild = {
  to: string;
  label: string;
  feature?: string | null;
};
type NavItem = {
  to: string;
  label: string;
  icon: string;
  cap: string | null;
  feature?: string | null;
  comingSoon?: boolean;
  children?: NavChild[];
};
type NavGroup = { label: string; items: NavItem[] };

// Collapsible sub-nav entries (e.g. CMS)
const collapsedSubs = ref<Set<string>>(new Set());
function toggleSubNav(path: string) {
  const next = new Set(collapsedSubs.value);
  if (next.has(path)) next.delete(path);
  else next.add(path);
  collapsedSubs.value = next;
}
function isSubCollapsed(path: string): boolean {
  return collapsedSubs.value.has(path);
}
function isSubActiveForParent(parentPath: string): boolean {
  return route.path === parentPath || route.path.startsWith(parentPath + "/");
}

const navGroups = computed<NavGroup[]>(() => [
  {
    label: t('navGroups.main'),
    items: [
      { to: "/",         label: t('nav.dashboard'), icon: "M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25", cap: null },
      { to: "/devices",  label: t('nav.devices'),   icon: "M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z", cap: "devices.read" },
      { to: "/dashboards", label: t('nav.dashboards'), icon: "M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0112 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375z", cap: "dashboards.read" },
    ],
  },
  {
    label: t('navGroups.data'),
    items: [
      { to: "/variables",  label: t('nav.variables'),    icon: "M4.5 12.75l7.5-7.5 7.5 7.5m-15 6l7.5-7.5 7.5 7.5", cap: "vars.read" },
      { to: "/entities",   label: t('nav.entities'),     icon: "M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z", cap: "entities.read" },
      { to: "/alerts",     label: t('nav.alerts'),       icon: "M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0", cap: "alerts.read" },
      { to: "/automations", label: t('nav.automations'), icon: "M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z", cap: null, feature: "automations" },
    ],
  },
  {
    label: t('navGroups.monitoring'),
    items: [
      { to: "/events",       label: t('nav.events'),      icon: "M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z", cap: "events.read" },
      { to: "/audit",        label: t('nav.audit'),       icon: "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z", cap: "audit.read", feature: "audit_log" },
      { to: "/trace-timeline", label: t('nav.traceTimeline'), icon: "M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z", cap: null },
      { to: "/system-health", label: t('nav.systemHealth'), icon: "M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z", cap: null },
    ],
  },
  {
    label: t('navGroups.tools'),
    items: [
      { to: "/webhooks", label: t('nav.webhooks'), icon: "M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582", cap: null, feature: "webhooks" },
      { to: "/integrations", label: t('nav.integrations'), icon: "M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244", cap: null, feature: "integrations" },
      { to: "/reports", label: t('nav.reports'), icon: "M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z", cap: null, feature: "reports" },
      { to: "/email-templates", label: t('nav.emailTemplates'), icon: "M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75", cap: null, feature: "email_templates" },
      { to: "/cms", label: t('nav.cms'), icon: "M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9zM9 12h6m-6 3h6m-6 3h6", cap: null, feature: "cms", children: [
        { to: "/cms", label: t('nav.cmsPages') },
        { to: "/cms/forms", label: t('nav.cmsForms') },
        { to: "/cms/menus", label: t('nav.cmsMenus') },
        { to: "/cms/media", label: t('nav.cmsMedia') },
        { to: "/cms/redirects", label: t('nav.cmsRedirects') },
        { to: "/cms/settings", label: t('nav.cmsSettings') },
      ] },
      { to: "/custom-api", label: t('nav.customApi'), icon: "M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5", cap: null, feature: "custom_api" },
      { to: "/flow-editor", label: t('nav.flowEditor'), icon: "M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zm9.75 0A2.25 2.25 0 0115.75 3.75H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25A2.25 2.25 0 0113.5 8.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25z", cap: null, feature: "flow_editor" },
      { to: "/hardware", label: t('nav.hardware'), icon: "M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z", cap: null, feature: "hardware" },
      { to: "/plugins", label: t('nav.plugins'), icon: "M14.25 6.087c0-.355.186-.676.401-.959.221-.29.349-.634.349-1.003 0-1.036-1.007-1.875-2.25-1.875s-2.25.84-2.25 1.875c0 .369.128.713.349 1.003.215.283.401.604.401.959v0a.64.64 0 01-.657.643 48.39 48.39 0 01-4.163-.3c.186 1.613.293 3.25.315 4.907a.656.656 0 01-.658.663v0c-.355 0-.676-.186-.959-.401a1.647 1.647 0 00-1.003-.349c-1.036 0-1.875 1.007-1.875 2.25s.84 2.25 1.875 2.25c.369 0 .713-.128 1.003-.349.283-.215.604-.401.959-.401v0c.31 0 .555.26.532.57a48.039 48.039 0 01-.642 5.056c1.518.19 3.058.309 4.616.354a.64.64 0 00.657-.643v0c0-.355-.186-.676-.401-.959a1.647 1.647 0 01-.349-1.003c0-1.035 1.008-1.875 2.25-1.875 1.243 0 2.25.84 2.25 1.875 0 .369-.128.713-.349 1.003-.215.283-.4.604-.4.959v0c0 .333.277.599.61.58a48.1 48.1 0 005.427-.63 48.05 48.05 0 00.582-4.717.532.532 0 00-.533-.57v0c-.355 0-.676.186-.959.401-.29.221-.634.349-1.003.349-1.035 0-1.875-1.007-1.875-2.25s.84-2.25 1.875-2.25c.37 0 .713.128 1.003.349.283.215.604.401.96.401v0a.656.656 0 00.658-.663 48.422 48.422 0 00-.37-5.36c-1.886.342-3.81.574-5.766.689a.578.578 0 01-.61-.58v0z", cap: null, feature: "plugins" },
      { to: "/tours", label: t('nav.tourBuilder'), icon: "M4.26 10.147a60.438 60.438 0 00-.491 6.347A48.62 48.62 0 0112 20.904a48.62 48.62 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.636 50.636 0 00-2.658-.813A59.906 59.906 0 0112 3.493a59.903 59.903 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5", cap: null, feature: "tours" },
      { to: "/sandbox", label: t('nav.sandbox'), icon: "M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 5.607A1.063 1.063 0 0120.18 22H3.82a1.063 1.063 0 01-1.022-1.093L4.2 15.3", cap: null, feature: "sandbox" },
    ],
  },
  {
    label: t('navGroups.system'),
    items: [
      { to: "/settings", label: t('nav.settings'), icon: "M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z M15 12a3 3 0 11-6 0 3 3 0 016 0z", cap: null },
      { to: "/developer", label: t('nav.apiDocs'), icon: "M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z", cap: null },
      { to: "/admin", label: t('nav.adminConsole'), icon: "M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75", cap: "cap.admin" },
      { to: "/settings/types", label: t('nav.semanticTypes'), icon: "M9.568 3H5.25A2.25 2.25 0 003 5.25v4.318c0 .597.237 1.17.659 1.591l9.581 9.581c.699.699 1.78.872 2.607.33a18.095 18.095 0 005.223-5.223c.542-.827.369-1.908-.33-2.607L11.16 3.66A2.25 2.25 0 009.568 3z M6 6h.008v.008H6V6z", cap: null, feature: "semantic_types" },
      { to: "/mcp", label: t('nav.mcpServer'), icon: "M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5", cap: "mcp.read", feature: "mcp" },
    ],
  },
]);

const visibleNavGroups = computed<NavGroup[]>(() =>
  navGroups.value
    .map((g) => ({
      ...g,
      items: g.items.filter((item) => {
        // Cap check (existing behavior)
        if (!item.comingSoon && item.cap !== null && !hasCap(item.cap)) return false;
        // Feature-flag check (new): hide items whose feature is disabled
        if (item.feature && featuresStore.loaded && !featuresStore.isEnabled(item.feature)) {
          return false;
        }
        return true;
      }),
    }))
    .filter((g) => g.items.length > 0)
);

// Collect all nav paths for longest-match active detection
const allNavPaths = computed(() =>
  navGroups.value.flatMap((g) => g.items.map((i) => i.to))
);

function isNavActive(itemTo: string): boolean {
  const p = route.path;
  if (itemTo === "/") return p === "/";
  // Exact match always wins
  if (p === itemTo) return true;
  // Prefix match (e.g. /devices matches /devices/123)
  if (p.startsWith(itemTo + "/")) {
    // Only highlight if no other nav item is a longer (more specific) match
    return !allNavPaths.value.some(
      (other) => other !== itemTo && other.length > itemTo.length && (p === other || p.startsWith(other + "/"))
    );
  }
  return false;
}

/** Map limit resource keys to i18n keys. */
const limitResourceLabels: Record<string, string> = {
  users: 'edition.resourceUsers',
  devices: 'edition.resourceDevices',
  api_keys: 'edition.resourceApiKeys',
  dashboards: 'edition.resourceDashboards',
  automations: 'edition.resourceAutomations',
  custom_endpoints: 'edition.resourceCustomEndpoints',
};

function handleNavClick() {
  mobileOpen.value = false;
}
</script>

<template>
  <div class="min-h-screen bg-[var(--bg-base)] flex">

    <!-- Skip to main content (Sprint 8 R4 A11y-F04) — visually hidden until focused -->
    <a
      href="#main-content"
      class="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[9999] focus:px-4 focus:py-2 focus:rounded-lg focus:bg-[var(--primary)] focus:text-[var(--text-invert)] focus:font-semibold focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:ring-offset-2"
      @click.prevent="() => { const el = document.getElementById('main-content'); if (el) { el.focus(); el.scrollIntoView(); } }"
    >
      {{ t('common.skipToContent') }}
    </a>

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
        'flex flex-col border-r border-[var(--border)] bg-[var(--bg-surface)] transition-all duration-300 shrink-0 sticky top-0 h-screen',
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
          {{ branding.productName }}
        </span>
        <span
          v-if="!collapsed && limitsStore.isCommunity"
          class="ml-1 px-1.5 py-0.5 text-[9px] font-semibold rounded bg-[var(--primary)]/15 text-[var(--primary)] tracking-wide"
        >
          {{ t('edition.badge') }}
        </span>
      </div>

      <!-- + New Button — Sprint 8 R2-F10 i18n fix -->
      <div v-if="!collapsed" class="px-2.5 pt-2 pb-1">
        <div class="relative">
          <button
            class="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)]/10 text-[var(--primary)] hover:bg-[var(--primary)]/20 transition-colors"
            @click="showNewMenu = !showNewMenu"
          >
            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
            {{ t('newMenu.label') }}
          </button>
          <div
            v-if="showNewMenu"
            class="absolute left-0 right-0 top-full mt-1 z-50 rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] shadow-lg py-1"
          >
            <router-link to="/devices?wizard=open" class="flex items-center gap-2 px-3 py-1.5 text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]" @click="showNewMenu = false">
              <span>+ {{ t('newMenu.device') }}</span>
            </router-link>
            <router-link to="/automations?create=true" class="flex items-center gap-2 px-3 py-1.5 text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]" @click="showNewMenu = false">
              <span>+ {{ t('newMenu.automation') }}</span>
            </router-link>
            <router-link to="/alerts?create=true" class="flex items-center gap-2 px-3 py-1.5 text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]" @click="showNewMenu = false">
              <span>+ {{ t('newMenu.alertRule') }}</span>
            </router-link>
            <router-link to="/dashboards?create=true" class="flex items-center gap-2 px-3 py-1.5 text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]" @click="showNewMenu = false">
              <span>+ {{ t('newMenu.dashboard') }}</span>
            </router-link>
          </div>
        </div>
      </div>
      <div v-else class="px-2 pt-2 pb-1">
        <button
          class="w-full flex items-center justify-center p-1.5 rounded-lg text-[var(--primary)] hover:bg-[var(--primary)]/10 transition-colors"
          :title="t('newMenu.createNewTooltip')"
          @click="showNewMenu = !showNewMenu"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
        </button>
      </div>

      <!--
        Nav Items
        Sprint 8 R3-F23/F24 fix:
        - `overflow-x: hidden` + `min-w-0` prevent a horizontal
          scroll bar from ever appearing when long German translations
          push against the sidebar width. Text now gets clipped (with
          `truncate` on the item labels) instead of causing a scroll
          track.
        - `scrollbar-gutter: stable` + browser-native auto-hide
          behavior means the vertical scroll track only appears when
          the nav content actually exceeds the sidebar height. Uses
          the custom `sidebar-nav` class (defined in the <style>
          block below) to apply platform-native auto-hide scrollbars.
      -->
      <nav class="sidebar-nav flex-1 min-w-0 overflow-x-hidden overflow-y-auto py-2">
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
            <!-- Nav item with sub-items (expand/collapse) -->
            <template v-else-if="item.children && item.children.length && !collapsed">
              <button
                v-show="!isGroupCollapsed(group.label)"
                :class="[
                  'w-full flex items-center gap-2.5 px-3.5 py-2.5 mx-1.5 my-0.5 rounded-lg text-sm transition-colors',
                  isSubActiveForParent(item.to)
                    ? 'bg-[var(--primary)]/10 text-[var(--primary)]'
                    : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]',
                ]"
                @click="toggleSubNav(item.to)"
              >
                <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
                </svg>
                <span class="truncate flex-1 text-left">{{ item.label }}</span>
                <svg
                  :class="['h-3 w-3 shrink-0 transition-transform duration-200', isSubCollapsed(item.to) ? '-rotate-90' : '']"
                  fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                </svg>
              </button>
              <div
                v-show="!isGroupCollapsed(group.label) && !isSubCollapsed(item.to)"
                class="ml-5 pl-2 border-l border-[var(--border)]"
              >
                <router-link
                  v-for="child in item.children"
                  :key="child.to"
                  :to="child.to"
                  :class="[
                    'flex items-center gap-2 px-3 py-1.5 mx-1.5 my-0.5 rounded-lg text-[12px] transition-colors',
                    route.path === child.to
                      ? 'bg-[var(--primary)]/10 text-[var(--primary)]'
                      : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]',
                  ]"
                >
                  <span class="truncate">{{ child.label }}</span>
                </router-link>
              </div>
            </template>
            <!-- Normal nav item -->
            <router-link
              v-else
              v-show="!isGroupCollapsed(group.label)"
              :to="item.to"
              :title="item.label"
              :data-tour="'nav-' + (item.to === '/' ? 'dashboard' : item.to.replace('/', ''))"
              :class="[
                'flex items-center gap-2.5 px-3.5 py-2.5 mx-1.5 my-0.5 rounded-lg text-sm transition-colors',
                isNavActive(item.to)
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

        <!-- Nav Items — same Sprint 8 R3-F23/F24 scrollbar fix as desktop -->
        <nav class="sidebar-nav flex-1 min-w-0 overflow-x-hidden overflow-y-auto py-2">
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
              <template v-else>
                <router-link
                  :to="item.to"
                  :data-tour="'nav-' + (item.to === '/' ? 'dashboard' : item.to.replace('/', ''))"
                  :class="[
                    'flex items-center gap-3 px-4 py-3 mx-2 my-0.5 rounded-lg text-sm transition-colors',
                    isNavActive(item.to)
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
                <!-- Sub-items (mobile) -->
                <div v-if="item.children && item.children.length && isSubActiveForParent(item.to)" class="ml-10 border-l border-[var(--border)] pl-2">
                  <router-link
                    v-for="child in item.children"
                    :key="child.to"
                    :to="child.to"
                    :class="[
                      'flex items-center gap-2 px-3 py-2 mx-2 my-0.5 rounded-lg text-xs transition-colors',
                      route.path === child.to
                        ? 'bg-[var(--primary)]/10 text-[var(--primary)]'
                        : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]',
                    ]"
                    @click="handleNavClick"
                  >
                    <span class="truncate">{{ child.label }}</span>
                  </router-link>
                </div>
              </template>
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
            {{ topBarTitle }}
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

          <!-- Guided Tours launcher -->
          <TourLauncher />

          <!-- Theme toggle -->
          <button
            data-tour="theme-toggle"
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
                {{ userInitial }}
              </div>
            </button>
            <div
              v-if="showUserMenu"
              class="absolute right-0 top-full mt-1 z-50 w-52 rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] shadow-xl py-1"
            >
              <!-- User identity header -->
              <div class="px-3 py-2 border-b border-[var(--border)]">
                <p v-if="userDisplayName" class="text-xs font-semibold text-[var(--text-primary)] truncate">{{ userDisplayName }}</p>
                <p class="text-[10px] text-[var(--text-muted)] truncate">{{ userEmail }}</p>
              </div>
              <!-- Org Switcher (only if user is in 2+ orgs) -->
              <div v-if="showOrgSwitcher" class="px-2 py-1.5 border-b border-[var(--border)]">
                <p class="text-[9px] text-[var(--text-muted)] uppercase tracking-wide px-1 mb-1">{{ t('nav.organization') }}</p>
                <button
                  v-for="org in userOrgs"
                  :key="org.id"
                  :class="[
                    'w-full flex items-center gap-2 px-2 py-1.5 rounded text-[11px] transition-colors',
                    org.id === currentOrgId
                      ? 'bg-[var(--primary)]/10 text-[var(--primary)] font-medium'
                      : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]'
                  ]"
                  :disabled="switchingOrg"
                  @click="switchOrg(org.id)"
                >
                  <svg class="h-3 w-3 shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3H21m-3.75 3H21" />
                  </svg>
                  <span class="truncate">{{ org.name }}</span>
                  <svg v-if="org.id === currentOrgId" class="h-3 w-3 ml-auto text-[var(--primary)]" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                </button>
              </div>
              <!-- Profile shortcut -->
              <router-link
                to="/settings?section=account"
                class="flex items-center gap-2 px-3 py-2 text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]"
                @click="showUserMenu = false"
              >
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" /></svg>
                {{ t('nav.profile') }}
              </router-link>
              <router-link
                to="/settings"
                class="flex items-center gap-2 px-3 py-2 text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]"
                @click="showUserMenu = false"
              >
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                {{ t('nav.settings') }}
              </router-link>
              <div class="border-t border-[var(--border)] my-1" />
              <button
                class="w-full flex items-center gap-2 px-3 py-2 text-xs text-red-400 hover:bg-red-500/10"
                @click="handleSignOut"
              >
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" /></svg>
                {{ t('auth.signOut') }}
              </button>
            </div>
          </div>
          <!-- Unauthenticated dot -->
          <div v-else class="h-2 w-2 rounded-full bg-[var(--status-bad)]" title="Not signed in" />
        </div>
      </header>

      <!-- Edition limit warning banner -->
      <div
        v-if="limitsStore.hasExceeded && !limitsStore.dismissed && limitsStore.isCommunity"
        class="flex items-center justify-between gap-3 px-4 py-2 bg-amber-500/10 border-b border-amber-500/20 text-xs"
      >
        <div class="flex items-center gap-2 min-w-0">
          <svg class="h-4 w-4 text-amber-400 shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
          </svg>
          <span class="text-amber-300/90 truncate" v-if="limitsStore.primaryExceeded">
            {{ t('edition.bannerMessage', {
              current: limitsStore.primaryExceeded.entry.current,
              max: limitsStore.primaryExceeded.entry.max,
              resource: t(limitResourceLabels[limitsStore.primaryExceeded.resource] || limitsStore.primaryExceeded.resource),
            }) }}
          </span>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <a
            :href="limitsStore.upgradeUrl"
            target="_blank"
            rel="noopener"
            class="px-2.5 py-1 rounded-md text-[10px] font-semibold bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 transition-colors whitespace-nowrap"
          >
            {{ t('edition.bannerLearnMore') }}
          </a>
          <button
            class="p-0.5 rounded text-amber-400/60 hover:text-amber-400 transition-colors"
            :title="t('edition.bannerDismiss')"
            @click="limitsStore.dismiss()"
          >
            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Camera viewport wrapper for cinematic zoom/pan effects -->
      <div id="camera-viewport" class="flex-1 flex flex-col" style="transform-origin: center center;">
        <main
          id="main-content"
          tabindex="-1"
          :class="[
            'flex-1 relative',
            route.meta?.fullscreen ? 'overflow-hidden' : 'overflow-auto p-3 md:p-6',
          ]"
        >
          <!-- Dim overlay when server is offline -->
          <div
            v-if="!serverHealth.serverOnline"
            class="absolute inset-0 bg-[var(--bg-base)]/60 z-10 pointer-events-none"
          />
          <slot />
        </main>
      </div>
    </div>

    <!-- Toast renderer -->
    <UToast />

    <!-- Command Palette -->
    <CommandPalette v-model:open="paletteOpen" />

    <!-- Welcome Screen (first login only) -->
    <WelcomeScreen v-if="showWelcome" />

    <!-- Tour Overlay (global, teleports to body) -->
    <TourOverlay />

    <!-- AI Coop Indicator (bottom-left floating badge) -->
    <AiCoopIndicator />
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

/*
 * Sprint 8 R3-F23/F24 fix — sidebar scroll behavior.
 *
 * F23 (horizontal): never show a horizontal scroll bar even when
 * long German nav labels push against the sidebar width. The
 * `overflow-x: hidden` on the <nav> element itself prevents the
 * bar from rendering; nav-item labels use `truncate` so long
 * translations clip gracefully at the right edge.
 *
 * F24 (vertical): the vertical scroll track should only appear
 * when the nav content actually exceeds the sidebar height —
 * otherwise it just shows as decoration and wastes space.
 * Modern browsers do this automatically for `overflow-y: auto`,
 * but some reserve scrollbar-gutter space. We use a slim custom
 * scrollbar that auto-hides on idle and overlays the content
 * (Firefox `scrollbar-width: thin`, WebKit `::-webkit-scrollbar`
 * with small width and transparent track).
 */
.sidebar-nav {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.12) transparent;
}
.sidebar-nav::-webkit-scrollbar {
  width: 6px;
}
.sidebar-nav::-webkit-scrollbar-track {
  background: transparent;
}
.sidebar-nav::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
}
.sidebar-nav::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.18);
}
</style>
