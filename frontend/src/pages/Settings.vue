<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { apiFetch, getToken, clearToken } from "../lib/api";
import { useCapabilities, hasCap } from "../lib/capabilities";
import { useRouter } from "vue-router";
import { usePreferencesStore } from "../stores/preferences";
import { setLocale, getCurrentLocale } from "../i18n";
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

const router = useRouter();
const caps = useCapabilities();
const currentLocale = ref(getCurrentLocale());
function switchLocale(locale: 'en' | 'de') {
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
  toast.addToast("Branding applied", "success");
}

function resetBrandingForm() {
  brandName.value = "HubEx";
  brandPrimary.value = "#F5A623";
  brandAccent.value = "#2DD4BF";
  brandLogo.value = "";
  resetBranding();
  toast.addToast("Branding reset to defaults", "success");
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

// ── Accordion sections ────────────────────────────────────────────────────────
type SectionKey = "account" | "organization" | "developer" | "system";
const expandedSection = ref<SectionKey | null>(null);

function toggleSection(key: SectionKey) {
  expandedSection.value = expandedSection.value === key ? null : key;
}

type Section = { key: SectionKey; label: string; description: string; icon: string };
const sections: Section[] = [
  { key: "account", label: "Profile & Account", description: "Email, session, authentication", icon: "M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" },
  { key: "organization", label: "Organization & Team", description: "Manage members and plans", icon: "M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 4.5H21m-3.75 4.5H21" },
  { key: "developer", label: "Developer", description: "API keys, capabilities, links", icon: "M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" },
  { key: "system", label: "System", description: "Demo data, UX preferences, reset", icon: "M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z M15 12a3 3 0 11-6 0 3 3 0 016 0z" },
];

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
onMounted(() => {
  loadUser();
  loadOrgs();
});
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-xl font-semibold text-[var(--text-primary)]">Settings</h1>
        <p class="text-sm text-[var(--text-muted)] mt-1">Manage your account, organization, and integrations</p>
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
                  <h3 class="text-sm font-semibold text-[var(--text-primary)]">Language / Sprache</h3>
                </template>
                <div class="flex items-center gap-3">
                  <button
                    class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                    :class="currentLocale === 'en' ? 'bg-[var(--primary)]/15 text-[var(--primary)] border border-[var(--primary)]/30' : 'bg-[var(--bg-raised)] text-[var(--text-muted)] border border-[var(--border)]'"
                    @click="switchLocale('en')"
                  >🇬🇧 English</button>
                  <button
                    class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                    :class="currentLocale === 'de' ? 'bg-[var(--primary)]/15 text-[var(--primary)] border border-[var(--primary)]/30' : 'bg-[var(--bg-raised)] text-[var(--text-muted)] border border-[var(--border)]'"
                    @click="switchLocale('de')"
                  >🇩🇪 Deutsch</button>
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
