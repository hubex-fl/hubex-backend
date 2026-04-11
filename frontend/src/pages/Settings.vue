<script setup lang="ts">
import { computed, onMounted, ref, nextTick } from "vue";
import { useI18n } from "vue-i18n";
import { apiFetch, getToken, clearToken } from "../lib/api";
import { useCapabilities, hasCap } from "../lib/capabilities";
import { useRouter, useRoute } from "vue-router";
import { usePreferencesStore } from "../stores/preferences";
import { setLocale, getCurrentLocale, type SupportedLocale } from "../i18n";
import UCard from "../components/ui/UCard.vue";
import UButton from "../components/ui/UButton.vue";
import UInput from "../components/ui/UInput.vue";
import UBadge from "../components/ui/UBadge.vue";
import USkeleton from "../components/ui/USkeleton.vue";
import UEmpty from "../components/ui/UEmpty.vue";
import ApiKeyManager from "../components/ApiKeyManager.vue";
import { applyBranding, resetBranding } from "../lib/branding";
import { useToastStore } from "../stores/toast";
const toast = useToastStore();
import SessionManager from "../components/SessionManager.vue";
import MfaSetup from "../components/MfaSetup.vue";
import UInfoTooltip from "../components/ui/UInfoTooltip.vue";
import { listDashboards, type DashboardSummary } from "../lib/dashboards";
import { useLimitsStore, type LimitResource } from "../stores/limits";
import { useFeaturesStore } from "../stores/features";
import UToggle from "../components/ui/UToggle.vue";

const router = useRouter();
const featuresStore = useFeaturesStore();
const { t, tm, rt } = useI18n();
const limitsStore = useLimitsStore();
const caps = useCapabilities();
const currentLocale = ref(getCurrentLocale());
const languageOptions: { code: SupportedLocale; label: string }[] = [
  { code: 'en', label: 'English' },
  { code: 'de', label: 'Deutsch' },
  { code: 'fr', label: 'Fran\u00e7ais' },
  { code: 'es', label: 'Espa\u00f1ol' },
  { code: 'it', label: 'Italiano' },
  { code: 'nl', label: 'Nederlands' },
  { code: 'pl', label: 'Polski' },
  { code: 'pt', label: 'Portugu\u00eas' },
];
function switchLocale(locale: SupportedLocale) {
  setLocale(locale);
  currentLocale.value = locale;
}
const prefs = usePreferencesStore();

// ── Demo Data ────────────────────────────────────────────────────────────────
const demoLoading = ref(false);
const demoDeleting = ref(false);
const demoResult = ref("");
const importResult = ref("");

// Branding
const brandName = ref("HubEx");
const brandPrimary = ref("#F5A623");
const brandAccent = ref("#2DD4BF");
const brandLogo = ref("");

async function saveBranding() {
  applyBranding({
    product_name: brandName.value || null,
    primary_color: brandPrimary.value || null,
    accent_color: brandAccent.value || null,
    logo_url: brandLogo.value || null,
  });
  // Try to save to backend (if org exists)
  if (orgs.value.length) {
    try {
      await apiFetch(`/api/v1/orgs/${orgs.value[0].id}/branding`, {
        method: "PUT",
        body: JSON.stringify({
          product_name: brandName.value || null,
          primary_color: brandPrimary.value || null,
          accent_color: brandAccent.value || null,
          logo_url: brandLogo.value || null,
        }),
      });
    } catch { /* apply locally anyway */ }
  }
  toast.addToast(t('branding.applied'), "success");
}

function resetBrandingForm() {
  brandName.value = "HubEx";
  brandPrimary.value = "#F5A623";
  brandAccent.value = "#2DD4BF";
  brandLogo.value = "";
  resetBranding();
  toast.addToast(t('branding.reset'), "success");
}

async function handleImport(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  importResult.value = "Importing...";
  try {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch("/api/v1/export/import", {
      method: "POST",
      headers: { Authorization: `Bearer ${getToken()}` },
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Import failed");
    const parts = [];
    if (data.dashboards_imported) parts.push(`${data.dashboards_imported} dashboards`);
    if (data.automations_imported) parts.push(`${data.automations_imported} automations`);
    if (data.variable_definitions_imported) parts.push(`${data.variable_definitions_imported} variables`);
    if (data.alert_rules_imported) parts.push(`${data.alert_rules_imported} alerts`);
    if (data.semantic_types_imported) parts.push(`${data.semantic_types_imported} types`);
    importResult.value = parts.length ? `Imported: ${parts.join(", ")}` : "Nothing new to import";
    if (data.errors?.length) importResult.value += ` (${data.errors.length} errors)`;
  } catch (err: unknown) {
    importResult.value = err instanceof Error ? err.message : "Import failed";
  }
  input.value = "";
}

async function loadDemoData() {
  demoLoading.value = true;
  demoResult.value = "";
  try {
    const r = await apiFetch<{ created: Record<string, number> }>("/api/v1/system/demo-data", { method: "POST" });
    demoResult.value = `Created: ${JSON.stringify(r.created)}`;
  } catch (e: unknown) {
    demoResult.value = "Failed to load demo data";
  } finally {
    demoLoading.value = false;
  }
}

async function deleteDemoData() {
  demoDeleting.value = true;
  demoResult.value = "";
  try {
    const r = await apiFetch<{ deleted: Record<string, number> }>("/api/v1/system/demo-data", { method: "DELETE" });
    demoResult.value = `Deleted: ${JSON.stringify(r.deleted)}`;
  } catch {
    demoResult.value = "Failed to delete demo data";
  } finally {
    demoDeleting.value = false;
  }
}

async function resetOnboarding() {
  await prefs.update("onboarding_completed", false);
  router.push("/");
}

function resetActionBars() {
  // Clear all localStorage action bar dismiss state
  const keys = Object.keys(localStorage).filter((k) => k.startsWith("hubex_actionbar_"));
  keys.forEach((k) => localStorage.removeItem(k));
  demoResult.value = `Reset ${keys.length} action bar preferences`;
}

// ── Homepage preference ──────────────────────────────────────────────────────
const userDashboards = ref<DashboardSummary[]>([]);
const dashboardsLoading = ref(false);
const homepageDashboardId = ref<number | null>(null);

async function loadDashboards() {
  dashboardsLoading.value = true;
  try {
    userDashboards.value = await listDashboards();
  } catch { /* ignore */ }
  dashboardsLoading.value = false;
}

function initHomepagePref() {
  const val = prefs.get<number | null>("homepage_dashboard_id", null);
  homepageDashboardId.value = val;
}

async function setHomepageDashboard(id: number | null) {
  homepageDashboardId.value = id;
  await prefs.update("homepage_dashboard_id", id);
  toast.addToast(t('settings.homepageSaved'), "success");
}

// ── Notification preferences ─────────────────────────────────────────────────
interface NotificationPrefs {
  email_enabled: boolean;
  email_alerts: boolean;
  email_digest: "off" | "daily" | "weekly";
  email_device_offline: boolean;
  email_automation_errors: boolean;
}

const notifPrefs = ref<NotificationPrefs>({
  email_enabled: false,
  email_alerts: true,
  email_digest: "off",
  email_device_offline: true,
  email_automation_errors: false,
});
const notifSaving = ref(false);

function initNotificationPrefs() {
  const saved = prefs.get<Partial<NotificationPrefs>>("notifications", {});
  notifPrefs.value = {
    email_enabled: saved.email_enabled ?? false,
    email_alerts: saved.email_alerts ?? true,
    email_digest: saved.email_digest ?? "off",
    email_device_offline: saved.email_device_offline ?? true,
    email_automation_errors: saved.email_automation_errors ?? false,
  };
}

async function saveNotificationPrefs() {
  notifSaving.value = true;
  try {
    await prefs.update("notifications", { ...notifPrefs.value });
    toast.addToast(t('settings.notificationsSaved'), "success");
  } catch {
    toast.addToast("Failed to save", "error");
  }
  notifSaving.value = false;
}

// ── Accordion sections ────────────────────────────────────────────────────────
type SectionKey = "edition" | "account" | "features" | "notifications" | "organization" | "developer" | "system";
const expandedSection = ref<SectionKey | null>(null);

// Features section state
const featuresToggling = ref<Set<string>>(new Set());

// Sprint 3.6 — client-side translation of backend FEATURE registry
// labels. The backend ships English in app/core/features.py; until
// backend i18n lands, we look up settings.featureNames.<key> and
// settings.featureDescs.<key> and fall back to the raw string.
function featureNameI18n(key: string, raw: string): string {
  const i18nKey = `settings.featureNames.${key}`;
  const translated = t(i18nKey);
  if (translated && translated !== i18nKey) return translated;
  return raw;
}
function featureDescriptionI18n(key: string, raw: string): string {
  const i18nKey = `settings.featureDescs.${key}`;
  const translated = t(i18nKey);
  if (translated && translated !== i18nKey) return translated;
  return raw;
}
// Sprint 3.2 — deep-link highlight support: when navigated to
// /settings?section=features&highlight=<key> (e.g. from the Plugins page
// "Enable Orchestrator →" CTA), auto-expand the section, scroll to the row,
// and pulse it for a few seconds so the user can't miss it.
const highlightedFeatureKey = ref<string | null>(null);
const route = useRoute();
async function toggleFeature(key: string, next: boolean) {
  if (featuresToggling.value.has(key)) return;
  featuresToggling.value.add(key);
  try {
    await featuresStore.setEnabled(key, next);
    toast.addToast(
      next ? `Feature "${key}" aktiviert` : `Feature "${key}" deaktiviert`,
      "success",
      3000
    );
  } catch (e: any) {
    toast.addToast(e?.message || "Toggle failed", "error");
  } finally {
    featuresToggling.value.delete(key);
  }
}

function toggleSection(key: SectionKey) {
  expandedSection.value = expandedSection.value === key ? null : key;
}

type Section = { key: SectionKey; labelKey: string; descKey: string; icon: string };
const sectionDefs: Section[] = [
  { key: "edition", labelKey: 'edition.settingsTitle', descKey: 'edition.settingsSubtitle', icon: "M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" },
  { key: "account", labelKey: 'settings.sections.account', descKey: 'settings.sections.accountDesc', icon: "M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" },
  { key: "features", labelKey: 'settings.sections.features', descKey: 'settings.sections.featuresDesc', icon: "M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" },
  { key: "notifications", labelKey: 'settings.sections.notifications', descKey: 'settings.sections.notificationsDesc', icon: "M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" },
  { key: "organization", labelKey: 'settings.sections.organization', descKey: 'settings.sections.organizationDesc', icon: "M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 4.5H21m-3.75 4.5H21" },
  { key: "developer", labelKey: 'settings.sections.developer', descKey: 'settings.sections.developerDesc', icon: "M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" },
  { key: "system", labelKey: 'settings.sections.system', descKey: 'settings.sections.systemDesc', icon: "M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z M15 12a3 3 0 11-6 0 3 3 0 016 0z" },
];
const sections = computed(() => sectionDefs.map(s => ({ ...s, label: t(s.labelKey), description: t(s.descKey) })));

/** Map resource keys to i18n keys for the edition limits table. */
const editionResourceLabels: Record<LimitResource, string> = {
  users: 'edition.resourceUsers',
  devices: 'edition.resourceDevices',
  api_keys: 'edition.resourceApiKeys',
  dashboards: 'edition.resourceDashboards',
  automations: 'edition.resourceAutomations',
  custom_endpoints: 'edition.resourceCustomEndpoints',
};
const editionResourceKeys: LimitResource[] = ['users', 'devices', 'api_keys', 'dashboards', 'automations', 'custom_endpoints'];

// ── Account tab ───────────────────────────────────────────────────────────────
type UserInfo = { id: number; email: string };
const userInfo = ref<UserInfo | null>(null);
const userLoading = ref(true);

async function loadUser() {
  userLoading.value = true;
  try {
    userInfo.value = await apiFetch<UserInfo>("/api/v1/users/me");
  } catch { /* ignore */ }
  userLoading.value = false;
}

function handleLogout() {
  clearToken();
  router.push("/login");
}

// ── Organization tab ──────────────────────────────────────────────────────────
type OrgInfo = { id: number; name: string; plan: string; max_devices: number; created_at: string };
type OrgMember = { user_id: number; email: string; role: string; joined_at: string };
const orgs = ref<OrgInfo[]>([]);
const orgsLoading = ref(true);
const selectedOrg = ref<OrgInfo | null>(null);
const orgMembers = ref<OrgMember[]>([]);
const orgMembersLoading = ref(false);

async function loadOrgs() {
  orgsLoading.value = true;
  try {
    orgs.value = await apiFetch<OrgInfo[]>("/api/v1/orgs");
    if (orgs.value.length && !selectedOrg.value) {
      selectedOrg.value = orgs.value[0];
      loadOrgMembers(orgs.value[0].id);
      // Load saved branding into form
      try {
        const b = await apiFetch<{ product_name: string | null; primary_color: string | null; accent_color: string | null; logo_url: string | null }>(`/api/v1/orgs/${orgs.value[0].id}/branding`);
        if (b.product_name) brandName.value = b.product_name;
        if (b.primary_color) brandPrimary.value = b.primary_color;
        if (b.accent_color) brandAccent.value = b.accent_color;
        if (b.logo_url) brandLogo.value = b.logo_url;
      } catch { /* ignore */ }
    }
  } catch { /* ignore */ }
  orgsLoading.value = false;
}

async function loadOrgMembers(orgId: number) {
  orgMembersLoading.value = true;
  try {
    orgMembers.value = await apiFetch<OrgMember[]>(`/api/v1/orgs/${orgId}/members`);
  } catch { /* ignore */ }
  orgMembersLoading.value = false;
}

function selectOrg(org: OrgInfo) {
  selectedOrg.value = org;
  loadOrgMembers(org.id);
}

// ── Developer tab ─────────────────────────────────────────────────────────────
const tokenPresent = computed(() => !!getToken());
const capList = computed(() => Array.from(caps.caps).sort());

// ── Init ──────────────────────────────────────────────────────────────────────
onMounted(async () => {
  loadUser();
  loadOrgs();
  loadDashboards();
  limitsStore.load();
  await featuresStore.load().catch(() => { /* fail-open */ });
  await prefs.load();
  initHomepagePref();
  initNotificationPrefs();

  // Deep-link section expand + feature highlight from query params.
  // Used by the Plugins page "Enable Orchestrator →" CTA.
  const sectionParam = route.query.section as string | undefined;
  const highlightParam = route.query.highlight as string | undefined;
  if (sectionParam && ["edition","account","features","notifications","organization","developer","system"].includes(sectionParam)) {
    expandedSection.value = sectionParam as SectionKey;
  }
  if (highlightParam) {
    // Delay so the section body has rendered before we scroll + highlight
    await nextTick();
    setTimeout(() => {
      highlightedFeatureKey.value = highlightParam;
      const el = document.querySelector(`[data-feature-row="${highlightParam}"]`) as HTMLElement | null;
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      }
      // Clear the highlight class after the pulse animation finishes
      setTimeout(() => { highlightedFeatureKey.value = null; }, 4500);
    }, 100);
  }
});
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <div class="flex items-center">
          <h1 class="text-xl font-semibold text-[var(--text-primary)]">{{ t('settings.title') }}</h1>
          <UInfoTooltip :title="t('infoTooltips.settings.title')" :items="tm('infoTooltips.settings.items').map((i: any) => rt(i))" />
        </div>
        <p class="text-sm text-[var(--text-muted)] mt-1">{{ t('settings.subtitle') }}</p>
      </div>
    </div>

    <!-- Accordion sections -->
    <div class="space-y-2">
      <!-- ── Profile & Account ─────────────────────────────────────────── -->
      <template v-for="section in sections" :key="section.key">
        <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] overflow-hidden">
          <!-- Section header (always visible, clickable) -->
          <button
            class="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-[var(--bg-raised)]/50 transition-colors"
            @click="toggleSection(section.key)"
          >
            <svg
              :class="['h-3.5 w-3.5 text-[var(--text-muted)] shrink-0 transition-transform duration-200', expandedSection === section.key ? 'rotate-90' : '']"
              fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
            </svg>
            <svg class="h-4 w-4 text-[var(--text-muted)] shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" :d="section.icon" />
            </svg>
            <div class="flex-1 min-w-0">
              <span class="text-sm font-semibold text-[var(--text-primary)]">{{ section.label }}</span>
              <span class="text-xs text-[var(--text-muted)] ml-2">{{ section.description }}</span>
            </div>
          </button>

          <!-- Section content -->
          <div v-if="expandedSection === section.key" class="border-t border-[var(--border)] px-4 py-4 space-y-4">

            <!-- Edition & Limits content -->
            <template v-if="section.key === 'edition'">
              <UCard>
                <template #header>
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                      <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('edition.currentEdition') }}</h3>
                      <span class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-[var(--primary)]/15 text-[var(--primary)] uppercase tracking-wider">
                        {{ limitsStore.edition }}
                      </span>
                    </div>
                    <a
                      v-if="limitsStore.isCommunity"
                      :href="limitsStore.upgradeUrl"
                      target="_blank"
                      rel="noopener"
                      class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)]/10 text-[var(--primary)] hover:bg-[var(--primary)]/20 transition-colors inline-flex items-center gap-1.5"
                    >
                      <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                      </svg>
                      {{ t('edition.upgradeButton') }}
                    </a>
                  </div>
                </template>
                <div v-if="limitsStore.loading" class="space-y-3">
                  <USkeleton height="1rem" width="100%" />
                  <USkeleton height="1rem" width="80%" />
                  <USkeleton height="1rem" width="90%" />
                </div>
                <div v-else-if="limitsStore.limits" class="space-y-3">
                  <!-- Limits table -->
                  <div class="overflow-x-auto">
                    <table class="w-full text-xs">
                      <thead>
                        <tr class="border-b border-[var(--border)]">
                          <th class="text-left py-2 pr-4 text-[var(--text-muted)] font-medium">{{ t('edition.limitHeader') }}</th>
                          <th class="text-left py-2 pr-4 text-[var(--text-muted)] font-medium">{{ t('edition.usageHeader') }}</th>
                          <th class="text-left py-2 text-[var(--text-muted)] font-medium">{{ t('edition.statusHeader') }}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="key in editionResourceKeys" :key="key" class="border-b border-[var(--border)]/50">
                          <td class="py-2.5 pr-4 text-[var(--text-primary)] font-medium">{{ t(editionResourceLabels[key]) }}</td>
                          <td class="py-2.5 pr-4">
                            <div class="flex items-center gap-2">
                              <div class="flex-1 max-w-[120px] h-1.5 rounded-full bg-[var(--bg-raised)] overflow-hidden">
                                <div
                                  :class="[
                                    'h-full rounded-full transition-all',
                                    limitsStore.limits![key].exceeded ? 'bg-amber-500' : 'bg-[var(--primary)]',
                                  ]"
                                  :style="{ width: limitsStore.limits![key].max > 0 ? Math.min(100, (limitsStore.limits![key].current / limitsStore.limits![key].max) * 100) + '%' : '0%' }"
                                />
                              </div>
                              <span class="text-[var(--text-secondary)] whitespace-nowrap">
                                {{ limitsStore.limits![key].max > 0
                                  ? t('edition.usageLabel', { current: limitsStore.limits![key].current, max: limitsStore.limits![key].max })
                                  : t('edition.usageUnlimited')
                                }}
                              </span>
                            </div>
                          </td>
                          <td class="py-2.5">
                            <UBadge
                              :status="limitsStore.limits![key].exceeded ? 'warn' : 'ok'"
                            >
                              {{ limitsStore.limits![key].exceeded ? t('edition.exceeded') : t('edition.withinLimits') }}
                            </UBadge>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
                <p v-else class="text-xs text-[var(--text-muted)]">Could not load edition info.</p>
              </UCard>
            </template>

            <!-- Account content -->
            <template v-if="section.key === 'account'">
              <UCard>
                <template #header>
                  <h3 class="text-sm font-semibold text-[var(--text-primary)]">Profile</h3>
                </template>
                <div v-if="userLoading" class="space-y-3">
                  <USkeleton height="1rem" width="60%" />
                  <USkeleton height="1rem" width="40%" />
                </div>
                <div v-else-if="userInfo" class="space-y-4">
                  <div class="flex items-center gap-4">
                    <div class="h-14 w-14 rounded-full bg-[var(--primary)]/10 border border-[var(--primary)]/30 flex items-center justify-center shrink-0">
                      <span class="text-xl font-bold text-[var(--primary)]">{{ userInfo.email.charAt(0).toUpperCase() }}</span>
                    </div>
                    <div>
                      <p class="text-sm font-semibold text-[var(--text-primary)]">{{ userInfo.email }}</p>
                      <p class="text-xs text-[var(--text-muted)]">User ID: {{ userInfo.id }}</p>
                    </div>
                  </div>
                  <div class="border-t border-[var(--border)] pt-4 flex items-center gap-3">
                    <UBadge :status="tokenPresent ? 'ok' : 'bad'">
                      {{ tokenPresent ? 'Authenticated' : 'Not authenticated' }}
                    </UBadge>
                    <span class="text-xs text-[var(--text-muted)]">{{ capList.length }} capabilities</span>
                  </div>
                </div>
                <div v-else class="text-xs text-[var(--text-muted)]">Could not load user info. Please log in.</div>
              </UCard>
              <UCard>
                <template #header>
                  <h3 class="text-sm font-semibold text-[var(--text-primary)]">Session</h3>
                </template>
                <div class="flex items-center gap-3">
                  <UButton variant="secondary" size="sm" class="border-[var(--status-bad)]/40 text-[var(--status-bad)] hover:bg-[var(--status-bad)]/10" @click="handleLogout">
                    Sign Out
                  </UButton>
                  <span class="text-xs text-[var(--text-muted)]">Clears your local token and redirects to login.</span>
                </div>
              </UCard>
              <UCard>
                <MfaSetup />
              </UCard>
              <UCard>
                <SessionManager />
              </UCard>
              <UCard>
                <template #header>
                  <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('settings.homepage') }}</h3>
                  <span class="text-xs text-[var(--text-muted)]">{{ t('settings.homepageDescription') }}</span>
                </template>
                <div class="space-y-3">
                  <div v-if="dashboardsLoading" class="space-y-2">
                    <USkeleton height="2.5rem" />
                  </div>
                  <div v-else>
                    <select
                      :value="homepageDashboardId ?? ''"
                      class="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--primary)]/50 transition-colors"
                      @change="setHomepageDashboard(($event.target as HTMLSelectElement).value ? Number(($event.target as HTMLSelectElement).value) : null)"
                    >
                      <option value="">{{ t('settings.systemDashboard') }}</option>
                      <option
                        v-for="db in userDashboards"
                        :key="db.id"
                        :value="db.id"
                      >
                        {{ db.name }}
                      </option>
                    </select>
                  </div>
                </div>
              </UCard>
            </template>

            <!-- Features content -->
            <template v-if="section.key === 'features'">
              <UCard>
                <template #header>
                  <div class="flex items-center justify-between">
                    <div>
                      <h3 class="text-sm font-semibold text-[var(--text-primary)]">
                        {{ t('settings.runtimeFeatureFlags') }}
                      </h3>
                      <span class="text-xs text-[var(--text-muted)]">
                        {{ t('settings.toggleSubsystems', { enabled: featuresStore.enabledCount, total: featuresStore.total }) }}
                      </span>
                    </div>
                    <UButton variant="secondary" size="sm" @click="router.push('/setup')">
                      {{ t('settings.openSetupWizard') }}
                    </UButton>
                  </div>
                </template>
                <div v-if="!featuresStore.loaded" class="text-sm text-[var(--text-muted)] py-4">
                  {{ t('settings.loadingFeatures') }}
                </div>
                <div v-else class="space-y-6">
                  <div
                    v-for="category in featuresStore.categories"
                    :key="category"
                    class="space-y-2"
                  >
                    <div
                      class="font-mono text-[11px] uppercase tracking-[0.1em] text-[var(--primary)]"
                    >
                      {{ t(`settings.featureCategory.${category}`) !== `settings.featureCategory.${category}` ? t(`settings.featureCategory.${category}`) : category }}
                    </div>
                    <div class="space-y-2">
                      <div
                        v-for="feat in featuresStore.byCategory[category] || []"
                        :key="feat.key"
                        :data-feature-row="feat.key"
                        :class="[
                          'flex items-start gap-3 p-3 rounded-lg border border-[var(--border)] bg-[var(--bg-raised)] transition-all',
                          highlightedFeatureKey === feat.key ? 'feature-row-pulse' : '',
                        ]"
                      >
                        <UToggle
                          :model-value="feat.enabled"
                          :disabled="featuresToggling.has(feat.key)"
                          @update:model-value="(v: boolean) => toggleFeature(feat.key, v)"
                        />
                        <div class="flex-1 min-w-0">
                          <div class="text-sm font-semibold text-[var(--text-primary)]">
                            {{ featureNameI18n(feat.key, feat.name) }}
                            <span class="ml-2 font-mono text-[11px] text-[var(--text-muted)]">
                              {{ feat.key }}
                            </span>
                          </div>
                          <div class="text-xs text-[var(--text-muted)] mt-0.5 leading-relaxed">
                            {{ featureDescriptionI18n(feat.key, feat.description) }}
                          </div>
                          <div
                            v-if="feat.requires.length"
                            class="text-[11px] text-[var(--text-muted)] mt-1 font-mono"
                          >
                            {{ t('settings.featureRequires') }} {{ feat.requires.join(", ") }}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </UCard>
            </template>

            <!-- Notifications content -->
            <template v-if="section.key === 'notifications'">
              <UCard>
                <template #header>
                  <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('settings.notifications') }}</h3>
                  <span class="text-xs text-[var(--text-muted)]">{{ t('settings.notificationsDescription') }}</span>
                </template>
                <div class="space-y-4">
                  <!-- Master switch -->
                  <div class="flex items-center justify-between">
                    <div>
                      <p class="text-sm font-medium text-[var(--text-primary)]">{{ t('settings.emailNotifications') }}</p>
                      <p class="text-xs text-[var(--text-muted)]">{{ t('settings.emailNotificationsHint') }}</p>
                    </div>
                    <button
                      class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors"
                      :class="notifPrefs.email_enabled ? 'bg-[var(--primary)]' : 'bg-[var(--bg-raised)] border border-[var(--border)]'"
                      @click="notifPrefs.email_enabled = !notifPrefs.email_enabled; saveNotificationPrefs()"
                    >
                      <span
                        class="inline-block h-4 w-4 rounded-full bg-white shadow transform transition-transform"
                        :class="notifPrefs.email_enabled ? 'translate-x-6' : 'translate-x-1'"
                      />
                    </button>
                  </div>

                  <!-- Sub-toggles (only visible when master is on) -->
                  <div v-if="notifPrefs.email_enabled" class="space-y-3 pl-1 border-l-2 border-[var(--primary)]/20 ml-1">
                    <!-- Alert Events -->
                    <div class="flex items-center justify-between pl-3">
                      <div>
                        <p class="text-sm text-[var(--text-primary)]">{{ t('settings.alertEvents') }}</p>
                        <p class="text-xs text-[var(--text-muted)]">{{ t('settings.alertEventsHint') }}</p>
                      </div>
                      <button
                        class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors"
                        :class="notifPrefs.email_alerts ? 'bg-[var(--primary)]' : 'bg-[var(--bg-raised)] border border-[var(--border)]'"
                        @click="notifPrefs.email_alerts = !notifPrefs.email_alerts; saveNotificationPrefs()"
                      >
                        <span
                          class="inline-block h-3 w-3 rounded-full bg-white shadow transform transition-transform"
                          :class="notifPrefs.email_alerts ? 'translate-x-5' : 'translate-x-1'"
                        />
                      </button>
                    </div>

                    <!-- Device Offline -->
                    <div class="flex items-center justify-between pl-3">
                      <div>
                        <p class="text-sm text-[var(--text-primary)]">{{ t('settings.deviceOffline') }}</p>
                        <p class="text-xs text-[var(--text-muted)]">{{ t('settings.deviceOfflineHint') }}</p>
                      </div>
                      <button
                        class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors"
                        :class="notifPrefs.email_device_offline ? 'bg-[var(--primary)]' : 'bg-[var(--bg-raised)] border border-[var(--border)]'"
                        @click="notifPrefs.email_device_offline = !notifPrefs.email_device_offline; saveNotificationPrefs()"
                      >
                        <span
                          class="inline-block h-3 w-3 rounded-full bg-white shadow transform transition-transform"
                          :class="notifPrefs.email_device_offline ? 'translate-x-5' : 'translate-x-1'"
                        />
                      </button>
                    </div>

                    <!-- Automation Errors -->
                    <div class="flex items-center justify-between pl-3">
                      <div>
                        <p class="text-sm text-[var(--text-primary)]">{{ t('settings.automationErrors') }}</p>
                        <p class="text-xs text-[var(--text-muted)]">{{ t('settings.automationErrorsHint') }}</p>
                      </div>
                      <button
                        class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors"
                        :class="notifPrefs.email_automation_errors ? 'bg-[var(--primary)]' : 'bg-[var(--bg-raised)] border border-[var(--border)]'"
                        @click="notifPrefs.email_automation_errors = !notifPrefs.email_automation_errors; saveNotificationPrefs()"
                      >
                        <span
                          class="inline-block h-3 w-3 rounded-full bg-white shadow transform transition-transform"
                          :class="notifPrefs.email_automation_errors ? 'translate-x-5' : 'translate-x-1'"
                        />
                      </button>
                    </div>

                    <!-- Email Digest -->
                    <div class="flex items-center justify-between pl-3">
                      <div>
                        <p class="text-sm text-[var(--text-primary)]">{{ t('settings.emailDigest') }}</p>
                        <p class="text-xs text-[var(--text-muted)]">{{ t('settings.emailDigestHint') }}</p>
                      </div>
                      <select
                        :value="notifPrefs.email_digest"
                        class="px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--primary)]/50 transition-colors"
                        @change="notifPrefs.email_digest = ($event.target as HTMLSelectElement).value as 'off' | 'daily' | 'weekly'; saveNotificationPrefs()"
                      >
                        <option value="off">{{ t('settings.digestOff') }}</option>
                        <option value="daily">{{ t('settings.digestDaily') }}</option>
                        <option value="weekly">{{ t('settings.digestWeekly') }}</option>
                      </select>
                    </div>
                  </div>
                </div>
              </UCard>
            </template>

            <!-- Organization content -->
            <template v-if="section.key === 'organization'">
      <UCard>
        <template #header>
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">Organizations</h3>
          <span class="text-xs text-[var(--text-muted)]">{{ orgs.length }} org{{ orgs.length !== 1 ? 's' : '' }}</span>
        </template>

        <div v-if="orgsLoading" class="space-y-2">
          <USkeleton height="2.5rem" v-for="i in 2" :key="i" />
        </div>
        <UEmpty
          v-else-if="!orgs.length"
          title="No organizations"
          description="Create an organization to manage devices and team members."
          icon="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21"
        />
        <div v-else class="divide-y divide-[var(--border)]">
          <button
            v-for="org in orgs"
            :key="org.id"
            class="w-full flex items-center gap-3 px-1 py-3 text-left hover:bg-[var(--bg-raised)] transition-colors rounded"
            :class="selectedOrg?.id === org.id ? 'bg-[var(--primary)]/5' : ''"
            @click="selectOrg(org)"
          >
            <div class="h-9 w-9 rounded-lg bg-[var(--accent-purple, #a78bfa)]/10 border border-[var(--accent-purple, #a78bfa)]/30 flex items-center justify-center shrink-0">
              <svg class="h-4 w-4 text-[var(--accent-purple, #a78bfa)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21" />
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-semibold text-[var(--text-primary)] truncate">{{ org.name }}</p>
              <div class="flex items-center gap-2 mt-0.5">
                <UBadge status="neutral">{{ org.plan }}</UBadge>
                <span class="text-[10px] text-[var(--text-muted)]">max {{ org.max_devices }} devices</span>
              </div>
            </div>
            <svg v-if="selectedOrg?.id === org.id" class="h-4 w-4 text-[var(--primary)] shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
          </button>
        </div>
      </UCard>

      <!-- Selected org members -->
      <UCard v-if="selectedOrg">
        <template #header>
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">Members of {{ selectedOrg.name }}</h3>
          <span class="text-xs text-[var(--text-muted)]">{{ orgMembers.length }} member{{ orgMembers.length !== 1 ? 's' : '' }}</span>
        </template>

        <div v-if="orgMembersLoading" class="space-y-2">
          <USkeleton height="2rem" v-for="i in 3" :key="i" />
        </div>
        <div v-else-if="orgMembers.length" class="divide-y divide-[var(--border)]">
          <div v-for="member in orgMembers" :key="member.user_id" class="flex items-center gap-3 py-2.5">
            <div class="h-8 w-8 rounded-full bg-[var(--bg-raised)] border border-[var(--border)] flex items-center justify-center shrink-0">
              <span class="text-xs font-bold text-[var(--text-muted)]">{{ member.email.charAt(0).toUpperCase() }}</span>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-xs font-medium text-[var(--text-primary)] truncate">{{ member.email }}</p>
              <p class="text-[10px] text-[var(--text-muted)]">User #{{ member.user_id }}</p>
            </div>
            <UBadge :status="member.role === 'owner' ? 'ok' : member.role === 'admin' ? 'info' : member.role === 'operator' ? 'warning' : member.role === 'viewer' ? 'neutral' : 'neutral'">
              {{ member.role }}
            </UBadge>
          </div>
        </div>
        <UEmpty v-else title="No members" description="This organization has no members." icon="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
              </UCard>
              <!-- Branding / White-Label -->
              <UCard>
                <template #header>
                  <h3 class="text-sm font-semibold text-[var(--text-primary)]">Branding / White-Label</h3>
                  <span class="text-xs text-[var(--text-muted)]">Customize the look and feel for your organization</span>
                </template>
                <div class="space-y-3">
                  <div>
                    <label class="text-[10px] font-medium text-[var(--text-muted)]">Product Name</label>
                    <input v-model="brandName" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)]" placeholder="HubEx" />
                  </div>
                  <div class="grid grid-cols-2 gap-3">
                    <div>
                      <label class="text-[10px] font-medium text-[var(--text-muted)]">Primary Color</label>
                      <div class="flex gap-2 mt-1">
                        <input type="color" v-model="brandPrimary" class="h-8 w-10 rounded cursor-pointer" />
                        <input v-model="brandPrimary" class="flex-1 px-2 py-1 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs font-mono text-[var(--text-primary)]" />
                      </div>
                    </div>
                    <div>
                      <label class="text-[10px] font-medium text-[var(--text-muted)]">Accent Color</label>
                      <div class="flex gap-2 mt-1">
                        <input type="color" v-model="brandAccent" class="h-8 w-10 rounded cursor-pointer" />
                        <input v-model="brandAccent" class="flex-1 px-2 py-1 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs font-mono text-[var(--text-primary)]" />
                      </div>
                    </div>
                  </div>
                  <div>
                    <label class="text-[10px] font-medium text-[var(--text-muted)]">Logo URL</label>
                    <input v-model="brandLogo" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)]" placeholder="https://example.com/logo.png" />
                  </div>
                  <!-- Live preview -->
                  <div class="flex items-center gap-3 px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-raised)]">
                    <div class="h-6 w-6 rounded-full" :style="{ background: brandPrimary || '#F5A623' }" />
                    <div class="h-6 w-6 rounded-full" :style="{ background: brandAccent || '#2DD4BF' }" />
                    <span class="text-xs font-bold" :style="{ color: brandPrimary || '#F5A623' }">{{ brandName || 'HubEx' }}</span>
                    <span class="text-[10px] text-[var(--text-muted)]">Preview</span>
                  </div>
                  <div class="flex gap-2">
                    <button class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black hover:bg-[var(--primary-hover)]" @click="saveBranding">Save Branding</button>
                    <button class="px-3 py-1.5 rounded-lg text-xs font-medium text-[var(--text-muted)] border border-[var(--border)]" @click="resetBrandingForm">Reset to Defaults</button>
                  </div>
                </div>
              </UCard>
            </template>

            <!-- Developer content -->
            <template v-if="section.key === 'developer'">
              <UCard>
                <template #header>
                  <h3 class="text-sm font-semibold text-[var(--text-primary)]">Authentication Status</h3>
                </template>
                <div class="flex items-center gap-3">
                  <UBadge :status="tokenPresent ? 'ok' : 'bad'">
                    Token {{ tokenPresent ? 'present' : 'missing' }}
                  </UBadge>
                  <span class="text-xs text-[var(--text-muted)]">Caps status: {{ caps.status }}</span>
                </div>
              </UCard>
              <UCard>
                <template #header>
                  <h3 class="text-sm font-semibold text-[var(--text-primary)]">Capabilities</h3>
                  <span class="text-xs text-[var(--text-muted)]">{{ capList.length }} loaded</span>
                </template>
                <div v-if="capList.length" class="flex flex-wrap gap-1.5">
                  <span v-for="cap in capList" :key="cap" class="inline-block px-2 py-0.5 rounded text-[10px] font-mono border border-[var(--border)] bg-[var(--bg-raised)] text-[var(--text-secondary)]">{{ cap }}</span>
                </div>
                <p v-else class="text-xs text-[var(--text-muted)]">No capabilities loaded.</p>
              </UCard>
              <UCard>
                <ApiKeyManager />
              </UCard>
              <UCard>
                <template #header>
                  <h3 class="text-sm font-semibold text-[var(--text-primary)]">Useful Links</h3>
                </template>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <a href="/api/v1/docs" target="_blank" class="flex items-center gap-2 px-3 py-2 rounded-lg border border-[var(--border)] hover:border-[var(--primary)]/40 transition-colors">
                    <svg class="h-4 w-4 text-[var(--primary)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>
                    <div><p class="text-xs font-medium text-[var(--text-primary)]">API Documentation</p><p class="text-[10px] text-[var(--text-muted)]">Swagger / OpenAPI</p></div>
                  </a>
                  <router-link to="/token" class="flex items-center gap-2 px-3 py-2 rounded-lg border border-[var(--border)] hover:border-[var(--primary)]/40 transition-colors">
                    <svg class="h-4 w-4 text-[var(--primary)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" /></svg>
                    <div><p class="text-xs font-medium text-[var(--text-primary)]">Token Inspector</p><p class="text-[10px] text-[var(--text-muted)]">Decode & inspect JWT</p></div>
                  </router-link>
                </div>
              </UCard>
            </template>

            <!-- System content -->
            <template v-if="section.key === 'system'">
              <UCard>
                <template #header>
                  <h3 class="text-sm font-semibold text-[var(--text-primary)]">Demo Data</h3>
                  <span class="text-xs text-[var(--text-muted)]">Sample devices, variables, automations</span>
                </template>
                <div class="flex items-center gap-3 flex-wrap">
                  <button :disabled="demoLoading" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)]/10 text-[var(--primary)] hover:bg-[var(--primary)]/20 transition-colors disabled:opacity-50" @click="loadDemoData">
                    {{ demoLoading ? 'Loading...' : 'Load Demo Data' }}
                  </button>
                  <button :disabled="demoDeleting" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors disabled:opacity-50" @click="deleteDemoData">
                    {{ demoDeleting ? 'Deleting...' : 'Delete Demo Data' }}
                  </button>
                  <span v-if="demoResult" class="text-xs text-[var(--text-muted)]">{{ demoResult }}</span>
                </div>
              </UCard>
              <UCard>
                <template #header>
                  <h3 class="text-sm font-semibold text-[var(--text-primary)]">Export / Import</h3>
                  <span class="text-xs text-[var(--text-muted)]">Backup and restore your configuration</span>
                </template>
                <div class="flex items-center gap-3 flex-wrap">
                  <a
                    href="/api/v1/export"
                    download
                    class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)]/10 text-[var(--primary)] hover:bg-[var(--primary)]/20 transition-colors inline-flex items-center gap-1.5"
                  >
                    <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" /></svg>
                    Export Config
                  </a>
                  <label class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--accent)]/10 text-[var(--accent)] hover:bg-[var(--accent)]/20 transition-colors cursor-pointer inline-flex items-center gap-1.5">
                    <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" /></svg>
                    Import Config
                    <input type="file" accept=".json" class="hidden" @change="handleImport" />
                  </label>
                  <span v-if="importResult" class="text-xs text-[var(--text-muted)]">{{ importResult }}</span>
                </div>
              </UCard>
              <UCard>
                <template #header>
                  <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('settings.language') }}</h3>
                </template>
                <div class="flex flex-wrap items-center gap-2">
                  <button
                    v-for="lang in languageOptions"
                    :key="lang.code"
                    class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                    :class="currentLocale === lang.code ? 'bg-[var(--primary)]/15 text-[var(--primary)] border border-[var(--primary)]/30' : 'bg-[var(--bg-raised)] text-[var(--text-muted)] border border-[var(--border)]'"
                    @click="switchLocale(lang.code)"
                  >{{ lang.label }}</button>
                </div>
              </UCard>
              <UCard>
                <template #header>
                  <h3 class="text-sm font-semibold text-[var(--text-primary)]">UX Preferences</h3>
                </template>
                <div class="flex items-center gap-3 flex-wrap">
                  <button class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--bg-raised)] text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]/80 transition-colors" @click="resetOnboarding">Reset Welcome Screen</button>
                  <button class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--bg-raised)] text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]/80 transition-colors" @click="resetActionBars">Reset Help Hints</button>
                </div>
              </UCard>
            </template>

          </div>
        </div>
      </template>
    </div>

  </div>
</template>

<style scoped>
/* Sprint 3.2 — deep-link highlight pulse for feature rows.
   Triggered by ?highlight=<key> query param (e.g. from the Plugins page
   "Enable Orchestrator →" CTA). 3 pulses over ~4s, then fades. */
.feature-row-pulse {
  animation: feature-row-pulse 1.4s ease-out 3;
  box-shadow: 0 0 0 0 rgba(245, 166, 35, 0);
  border-color: var(--primary) !important;
}
@keyframes feature-row-pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(245, 166, 35, 0.55);
    background-color: rgba(245, 166, 35, 0.08);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(245, 166, 35, 0);
    background-color: rgba(245, 166, 35, 0.02);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(245, 166, 35, 0);
    background-color: transparent;
  }
}
</style>
