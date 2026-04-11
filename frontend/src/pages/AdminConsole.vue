<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";
import { useAuthStore } from "../stores/auth";
import { useCapabilities } from "../lib/capabilities";
import { fmtDateTime } from "../lib/relativeTime";
import UCard from "../components/ui/UCard.vue";
import UBadge from "../components/ui/UBadge.vue";
import UEmpty from "../components/ui/UEmpty.vue";
import UInfoTooltip from "../components/ui/UInfoTooltip.vue";

const toast = useToastStore();
const { t, tm, rt } = useI18n();
const authStore = useAuthStore();
const caps = useCapabilities();

const CAP_LABEL_KEYS: Record<string, string> = {
  "devices.read": "devicesRead", "devices.write": "devicesWrite",
  "vars.read": "varsRead", "vars.write": "varsWrite",
  "alerts.read": "alertsRead", "alerts.write": "alertsWrite",
  "automations.read": "automationsRead", "automations.write": "automationsWrite",
  "telemetry.read": "telemetryRead", "telemetry.emit": "telemetryEmit",
  "events.read": "eventsRead", "audit.read": "auditRead",
  "dashboards.read": "dashboardsRead", "dashboards.write": "dashboardsWrite",
  "config.read": "configRead", "config.write": "configWrite",
  "webhooks.read": "webhooksRead", "webhooks.write": "webhooksWrite",
  "org.read": "orgRead", "org.admin": "orgAdmin",
  "modules.read": "modulesRead", "modules.write": "modulesWrite",
};
function capLabel(cap: string): string {
  const key = CAP_LABEL_KEYS[cap];
  return key ? t(`pages.admin.capLabels.${key}`) : cap;
}

// ── Modules ──────────────────────────────────────────────────────────────────
type Module = {
  key: string;
  label: string;
  description: string;
  enabled: boolean;
  version: string;
  capabilities: string[];
};

const modules = ref<Module[]>([]);
const modulesLoading = ref(true);
const modulesError = ref<string | null>(null);
const togglingModule = ref<string | null>(null);

async function loadModules() {
  modulesLoading.value = true;
  modulesError.value = null;
  try {
    modules.value = await apiFetch<Module[]>("/api/v1/modules");
  } catch {
    modulesError.value = t('pages.admin.loadModulesFailed');
  } finally {
    modulesLoading.value = false;
  }
}

async function toggleModule(mod: Module) {
  if (mod.enabled) {
    const caps = (mod.capabilities || []).length;
    if (!confirm(t('pages.admin.disableConfirm', { name: mod.label || mod.key, caps }))) return;
  }
  togglingModule.value = mod.key;
  try {
    const action = mod.enabled ? "disable" : "enable";
    await apiFetch(`/api/v1/modules/${mod.key}/${action}`, { method: "POST" });
    mod.enabled = !mod.enabled;
    const message = mod.enabled
      ? t('pages.admin.moduleEnabled', { key: mod.key })
      : t('pages.admin.moduleDisabled', { key: mod.key });
    toast.addToast(message, "success");
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : t('pages.admin.toggleFailed'), "error");
  } finally {
    togglingModule.value = null;
  }
}

// ── System Status ────────────────────────────────────────────────────────────
type HealthData = {
  status: string;
  database: string;
  redis: string;
  version: string;
};

const health = ref<HealthData | null>(null);
const healthLoading = ref(true);

async function loadHealth() {
  healthLoading.value = true;
  try {
    health.value = await apiFetch<HealthData>("/health");
  } catch {
    health.value = null;
  } finally {
    healthLoading.value = false;
  }
}

// ── Plan/Capabilities Summary ────────────────────────────────────────────────
const enabledCount = computed(() => modules.value.filter(m => m.enabled).length);
const totalCaps = computed(() => {
  const all = new Set<string>();
  modules.value.filter(m => m.enabled).forEach(m => (m.capabilities || []).forEach(c => all.add(c)));
  return all.size;
});

// ── Sprint 8 R4 Bucket C F22: Admin Console MVP ────────────────────────────
// The Admin Console used to show only Module Registry + System Info, so the
// user said "irgendwie ohne Funktion, genau wie System Health". This adds
// three real sections: current-user capability set, list of accessible
// organizations, and members of the currently active organization.
//
// These are READ-ONLY panels for this release — invite/remove/role-change
// actions stay in the per-org settings flow. That keeps the blast radius
// small for dev-stable-v1 while still giving admins a real overview pane.

type OrgSummary = {
  id: number;
  name: string;
  slug?: string;
  edition?: string;
  created_at?: string;
  role?: string;
};

type OrgMember = {
  user_id: number;
  email: string;
  role: string;
  invited_at?: string | null;
  joined_at?: string | null;
};

const orgs = ref<OrgSummary[]>([]);
const orgsLoading = ref(true);
const orgsError = ref<string | null>(null);

const members = ref<OrgMember[]>([]);
const membersLoading = ref(true);
const membersError = ref<string | null>(null);

async function loadOrgs() {
  orgsLoading.value = true;
  orgsError.value = null;
  try {
    const res = await apiFetch<OrgSummary[] | { orgs: OrgSummary[] }>("/api/v1/orgs");
    // Backend may return a bare array OR a dict with .orgs; accept both.
    orgs.value = Array.isArray(res) ? res : (res?.orgs ?? []);
  } catch (e: any) {
    orgsError.value = e?.message || t('pages.admin.loadOrgsFailed');
  } finally {
    orgsLoading.value = false;
  }
}

async function loadMembers() {
  const currentOrgId = authStore.orgId;
  if (!currentOrgId) {
    membersLoading.value = false;
    return;
  }
  membersLoading.value = true;
  membersError.value = null;
  try {
    members.value = await apiFetch<OrgMember[]>(`/api/v1/orgs/${currentOrgId}/members`);
  } catch (e: any) {
    membersError.value = e?.message || t('pages.admin.loadMembersFailed');
  } finally {
    membersLoading.value = false;
  }
}

const sortedCaps = computed(() => {
  return Array.from(caps.caps).sort();
});

function roleBadgeStatus(role: string): "ok" | "warn" | "neutral" {
  if (role === "owner") return "warn";
  if (role === "admin") return "ok";
  return "neutral";
}

onMounted(() => {
  loadModules();
  loadHealth();
  loadOrgs();
  loadMembers();
});
</script>

<template>
  <div class="space-y-6">
    <div>
      <div class="flex items-center">
        <h1 class="text-xl font-semibold text-[var(--text-primary)]">{{ t('pages.admin.title') }}</h1>
        <UInfoTooltip
          :title="t('infoTooltips.admin.title')"
          :items="tm('infoTooltips.admin.items').map((i: any) => rt(i))"
        />
      </div>
      <p class="text-xs text-[var(--text-muted)] mt-0.5">{{ t('pages.admin.subtitle') }}</p>
    </div>

    <!-- Status Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
      <UCard padding="md">
        <div class="text-center">
          <p class="text-2xl font-bold text-[var(--primary)]">{{ enabledCount }}/{{ modules.length }}</p>
          <p class="text-[10px] text-[var(--text-muted)] mt-1">{{ t('pages.admin.modulesEnabled') }}</p>
        </div>
      </UCard>
      <UCard padding="md">
        <div class="text-center">
          <p class="text-2xl font-bold text-[var(--accent)]">{{ totalCaps }}</p>
          <p class="text-[10px] text-[var(--text-muted)] mt-1">{{ t('pages.admin.activeCapabilities') }}</p>
        </div>
      </UCard>
      <UCard padding="md">
        <div class="text-center">
          <p class="text-2xl font-bold" :class="health?.status === 'ok' ? 'text-[var(--status-ok)]' : 'text-[var(--status-bad)]'">
            {{ healthLoading ? '...' : health?.status === 'ok' ? t('health.healthy') : t('health.degraded') }}
          </p>
          <p class="text-[10px] text-[var(--text-muted)] mt-1">{{ t('pages.admin.systemStatus') }}</p>
        </div>
      </UCard>
    </div>

    <!-- Module List -->
    <UCard>
      <template #header>
        <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('pages.admin.moduleRegistry') }}</h3>
        <span class="text-xs text-[var(--text-muted)]">{{ t('pages.admin.moduleRegistryHint') }}</span>
      </template>

      <div v-if="modulesLoading" class="text-xs text-[var(--text-muted)] py-4">{{ t('pages.admin.loadingModules') }}</div>
      <div v-else-if="modulesError" class="text-xs text-red-400 py-4">{{ modulesError }}</div>

      <UEmpty v-else-if="!modules.length"
        :title="t('pages.admin.noModulesTitle')"
        :description="t('pages.admin.noModulesDescription')"
        icon="M6.429 9.75L2.25 12l4.179 2.25m0-4.5l5.571 3 5.571-3m-11.142 0L2.25 7.5 12 2.25l9.75 5.25-4.179 2.25m0 0L21.75 12l-4.179 2.25m0 0L12 16.5l-5.571-2.25m11.142 0L21.75 16.5 12 21.75 2.25 16.5l4.179-2.25"
      />

      <div v-else class="divide-y divide-[var(--border)]">
        <div v-for="mod in modules" :key="mod.key" class="flex items-center gap-4 py-3">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="text-xs font-medium text-[var(--text-primary)]">{{ mod.label || mod.key }}</span>
              <UBadge :status="mod.enabled ? 'ok' : 'neutral'" size="sm">{{ mod.enabled ? t('pages.admin.enabledLabel') : t('pages.admin.disabledLabel') }}</UBadge>
              <span class="text-[10px] text-[var(--text-muted)] font-mono">v{{ mod.version }}</span>
            </div>
            <p v-if="mod.description" class="text-[10px] text-[var(--text-muted)] mt-0.5 truncate">{{ mod.description }}</p>
            <div v-if="mod.capabilities?.length" class="flex flex-wrap gap-1 mt-1">
              <span
                v-for="cap in mod.capabilities.slice(0, 5)"
                :key="cap"
                :title="capLabel(cap)"
                class="text-[9px] px-1 py-0.5 rounded bg-[var(--bg-raised)] border border-[var(--border)] font-mono text-[var(--text-muted)] cursor-help"
              >{{ cap }}</span>
              <span v-if="mod.capabilities.length > 5" class="text-[9px] text-[var(--text-muted)]">{{ t('pages.admin.moreCapabilities', { n: mod.capabilities.length - 5 }) }}</span>
            </div>
          </div>
          <button
            :disabled="togglingModule === mod.key"
            :class="[
              'relative w-10 h-5 rounded-full transition-colors',
              mod.enabled ? 'bg-[var(--status-ok)]' : 'bg-[var(--bg-overlay)]',
            ]"
            @click="toggleModule(mod)"
          >
            <span
              :class="[
                'absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform',
                mod.enabled ? 'translate-x-5' : 'translate-x-0.5',
              ]"
            />
          </button>
        </div>
      </div>
    </UCard>

    <!-- Sprint 8 R4 Bucket C F22: Your Capabilities -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('pages.admin.yourCapsTitle') }}</h3>
          <span class="text-xs text-[var(--text-muted)]">{{ t('pages.admin.yourCapsCount', { n: sortedCaps.length }) }}</span>
        </div>
      </template>
      <div v-if="caps.status !== 'ready'" class="text-xs text-[var(--text-muted)] py-2">
        {{ t('pages.admin.yourCapsLoading') }}
      </div>
      <div v-else-if="sortedCaps.length === 0" class="text-xs text-[var(--text-muted)] py-2">
        {{ t('pages.admin.yourCapsEmpty') }}
      </div>
      <div v-else class="flex flex-wrap gap-1.5">
        <span
          v-for="cap in sortedCaps"
          :key="cap"
          :title="capLabel(cap)"
          class="text-[10px] px-2 py-1 rounded bg-[var(--bg-raised)] border border-[var(--border)] font-mono text-[var(--text-secondary)]"
        >{{ cap }}</span>
      </div>
    </UCard>

    <!-- Sprint 8 R4 Bucket C F22: Your Organizations -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('pages.admin.yourOrgsTitle') }}</h3>
          <span class="text-xs text-[var(--text-muted)]">{{ t('pages.admin.yourOrgsHint') }}</span>
        </div>
      </template>
      <div v-if="orgsLoading" class="text-xs text-[var(--text-muted)] py-2">{{ t('pages.admin.loadingOrgs') }}</div>
      <div v-else-if="orgsError" class="text-xs text-[var(--status-bad)] py-2">{{ orgsError }}</div>
      <div v-else-if="!orgs.length" class="text-xs text-[var(--text-muted)] py-2">{{ t('pages.admin.noOrgs') }}</div>
      <div v-else class="divide-y divide-[var(--border)]">
        <div v-for="org in orgs" :key="org.id" class="flex items-center gap-4 py-3">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="text-xs font-medium text-[var(--text-primary)]">{{ org.name }}</span>
              <UBadge
                v-if="authStore.orgId === org.id"
                status="ok"
                size="sm"
              >{{ t('pages.admin.currentOrgBadge') }}</UBadge>
              <UBadge v-if="org.edition" status="neutral" size="sm">{{ org.edition }}</UBadge>
            </div>
            <p v-if="org.slug" class="text-[10px] text-[var(--text-muted)] mt-0.5 font-mono">{{ org.slug }}</p>
          </div>
          <span v-if="org.role" class="text-[10px] text-[var(--text-muted)] uppercase tracking-wide">{{ org.role }}</span>
        </div>
      </div>
    </UCard>

    <!-- Sprint 8 R4 Bucket C F22: Members of current organization -->
    <UCard v-if="authStore.orgId">
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('pages.admin.orgMembersTitle') }}</h3>
          <span class="text-xs text-[var(--text-muted)]">{{ t('pages.admin.orgMembersHint') }}</span>
        </div>
      </template>
      <div v-if="membersLoading" class="text-xs text-[var(--text-muted)] py-2">{{ t('pages.admin.loadingMembers') }}</div>
      <div v-else-if="membersError" class="text-xs text-[var(--status-bad)] py-2">{{ membersError }}</div>
      <div v-else-if="!members.length" class="text-xs text-[var(--text-muted)] py-2">{{ t('pages.admin.noMembers') }}</div>
      <div v-else class="divide-y divide-[var(--border)]">
        <div v-for="m in members" :key="m.user_id" class="flex items-center gap-4 py-3">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="text-xs font-medium text-[var(--text-primary)]">{{ m.email }}</span>
              <UBadge :status="roleBadgeStatus(m.role)" size="sm">{{ m.role }}</UBadge>
            </div>
            <p class="text-[10px] text-[var(--text-muted)] mt-0.5">
              <template v-if="m.joined_at">{{ t('pages.admin.joinedOn', { when: fmtDateTime(m.joined_at) }) }}</template>
              <template v-else-if="m.invited_at">{{ t('pages.admin.invitedOn', { when: fmtDateTime(m.invited_at) }) }}</template>
            </p>
          </div>
        </div>
      </div>
      <p class="text-[10px] text-[var(--text-muted)] mt-3 italic">{{ t('pages.admin.orgMembersManageHint') }}</p>
    </UCard>

    <!-- System Info -->
    <UCard v-if="health">
      <template #header>
        <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('pages.admin.systemInfo') }}</h3>
      </template>
      <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
        <div>
          <span class="text-[var(--text-muted)]">{{ t('pages.admin.database') }}</span>
          <p class="font-medium" :class="health.database === 'ok' ? 'text-[var(--status-ok)]' : 'text-[var(--status-bad)]'">{{ health.database }}</p>
        </div>
        <div>
          <span class="text-[var(--text-muted)]">{{ t('pages.admin.redis') }}</span>
          <p class="font-medium" :class="health.redis === 'ok' ? 'text-[var(--status-ok)]' : health.redis === 'not configured' ? 'text-[var(--text-muted)]' : 'text-[var(--status-bad)]'">{{ health.redis }}</p>
        </div>
        <div>
          <span class="text-[var(--text-muted)]">{{ t('pages.admin.version') }}</span>
          <p class="font-medium text-[var(--text-primary)]">{{ health.version || 'dev' }}</p>
        </div>
      </div>
    </UCard>
  </div>
</template>
