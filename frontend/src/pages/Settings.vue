<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { apiFetch, getToken, clearToken } from "../lib/api";
import { useCapabilities, hasCap } from "../lib/capabilities";
import { useRouter } from "vue-router";
import UCard from "../components/ui/UCard.vue";
import UButton from "../components/ui/UButton.vue";
import UInput from "../components/ui/UInput.vue";
import UBadge from "../components/ui/UBadge.vue";
import USkeleton from "../components/ui/USkeleton.vue";
import UEmpty from "../components/ui/UEmpty.vue";

const router = useRouter();
const caps = useCapabilities();

// ── Tab navigation ────────────────────────────────────────────────────────────
type TabKey = "account" | "organization" | "api" | "developer";
const activeTab = ref<TabKey>("account");

const tabs: { key: TabKey; label: string; icon: string }[] = [
  { key: "account", label: "Account", icon: "M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" },
  { key: "organization", label: "Organization", icon: "M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 4.5H21m-3.75 4.5H21" },
  { key: "api", label: "API Keys", icon: "M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" },
  { key: "developer", label: "Developer", icon: "M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" },
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
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold text-[var(--text-primary)]">Settings</h1>
        <p class="text-xs text-[var(--text-muted)] mt-0.5">Manage your account, organization, and integrations</p>
      </div>
    </div>

    <!-- Tab navigation -->
    <div class="flex gap-1 border-b border-[var(--border)] pb-0">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="[
          'flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors border-b-2 -mb-px',
          activeTab === tab.key
            ? 'border-[var(--accent-cyan)] text-[var(--accent-cyan)]'
            : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]',
        ]"
        @click="activeTab = tab.key"
      >
        <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" :d="tab.icon" />
        </svg>
        {{ tab.label }}
      </button>
    </div>

    <!-- ── Account Tab ───────────────────────────────────────────────────── -->
    <div v-if="activeTab === 'account'" class="space-y-4">
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
            <!-- Avatar placeholder -->
            <div class="h-14 w-14 rounded-full bg-[var(--accent-cyan)]/10 border border-[var(--accent-cyan)]/30 flex items-center justify-center shrink-0">
              <span class="text-xl font-bold text-[var(--accent-cyan)]">{{ userInfo.email.charAt(0).toUpperCase() }}</span>
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

      <!-- Session -->
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
    </div>

    <!-- ── Organization Tab ──────────────────────────────────────────────── -->
    <div v-if="activeTab === 'organization'" class="space-y-4">
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
            :class="selectedOrg?.id === org.id ? 'bg-[var(--accent-cyan)]/5' : ''"
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
            <svg v-if="selectedOrg?.id === org.id" class="h-4 w-4 text-[var(--accent-cyan)] shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
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
            <UBadge :status="member.role === 'owner' ? 'ok' : member.role === 'admin' ? 'info' : 'neutral'">
              {{ member.role }}
            </UBadge>
          </div>
        </div>
        <UEmpty v-else title="No members" description="This organization has no members." icon="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
      </UCard>
    </div>

    <!-- ── API Keys Tab ──────────────────────────────────────────────────── -->
    <div v-if="activeTab === 'api'" class="space-y-4">
      <UCard>
        <template #header>
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">API Keys</h3>
        </template>
        <UEmpty
          title="Coming soon"
          description="API key management will be available in a future release. For now, use JWT tokens via the auth endpoints."
          icon="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z"
        />
      </UCard>
    </div>

    <!-- ── Developer Tab ─────────────────────────────────────────────────── -->
    <div v-if="activeTab === 'developer'" class="space-y-4">
      <UCard>
        <template #header>
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">Authentication Status</h3>
        </template>
        <div class="space-y-3">
          <div class="flex items-center gap-3">
            <UBadge :status="tokenPresent ? 'ok' : 'bad'">
              Token {{ tokenPresent ? 'present' : 'missing' }}
            </UBadge>
            <span class="text-xs text-[var(--text-muted)]">Caps status: {{ caps.status }}</span>
          </div>
        </div>
      </UCard>

      <UCard>
        <template #header>
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">Capabilities</h3>
          <span class="text-xs text-[var(--text-muted)]">{{ capList.length }} loaded</span>
        </template>

        <div v-if="capList.length" class="flex flex-wrap gap-1.5">
          <span
            v-for="cap in capList"
            :key="cap"
            class="inline-block px-2 py-0.5 rounded text-[10px] font-mono border border-[var(--border)] bg-[var(--bg-raised)] text-[var(--text-secondary)]"
          >{{ cap }}</span>
        </div>
        <p v-else class="text-xs text-[var(--text-muted)]">No capabilities loaded.</p>
      </UCard>

      <UCard>
        <template #header>
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">Useful Links</h3>
        </template>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <a href="/api/v1/docs" target="_blank" class="flex items-center gap-2 px-3 py-2 rounded-lg border border-[var(--border)] hover:border-[var(--accent-cyan)]/40 transition-colors">
            <svg class="h-4 w-4 text-[var(--accent-cyan)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            <div>
              <p class="text-xs font-medium text-[var(--text-primary)]">API Documentation</p>
              <p class="text-[10px] text-[var(--text-muted)]">Swagger / OpenAPI</p>
            </div>
          </a>
          <router-link to="/token" class="flex items-center gap-2 px-3 py-2 rounded-lg border border-[var(--border)] hover:border-[var(--accent-cyan)]/40 transition-colors">
            <svg class="h-4 w-4 text-[var(--accent-cyan)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
            </svg>
            <div>
              <p class="text-xs font-medium text-[var(--text-primary)]">Token Inspector</p>
              <p class="text-[10px] text-[var(--text-muted)]">Decode & inspect JWT</p>
            </div>
          </router-link>
          <router-link to="/audit" class="flex items-center gap-2 px-3 py-2 rounded-lg border border-[var(--border)] hover:border-[var(--accent-cyan)]/40 transition-colors">
            <svg class="h-4 w-4 text-[var(--accent-cyan)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <p class="text-xs font-medium text-[var(--text-primary)]">Audit Log</p>
              <p class="text-[10px] text-[var(--text-muted)]">Track all actions</p>
            </div>
          </router-link>
          <router-link to="/observability" class="flex items-center gap-2 px-3 py-2 rounded-lg border border-[var(--border)] hover:border-[var(--accent-cyan)]/40 transition-colors">
            <svg class="h-4 w-4 text-[var(--accent-cyan)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75z" />
            </svg>
            <div>
              <p class="text-xs font-medium text-[var(--text-primary)]">Observability</p>
              <p class="text-[10px] text-[var(--text-muted)]">System health metrics</p>
            </div>
          </router-link>
        </div>
      </UCard>
    </div>

  </div>
</template>
