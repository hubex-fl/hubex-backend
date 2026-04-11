<script setup lang="ts">
import { computed, ref, watch, nextTick } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
const { t } = useI18n();
import UCard from "../components/ui/UCard.vue";
import UBadge from "../components/ui/UBadge.vue";
import UButton from "../components/ui/UButton.vue";
import USkeleton from "../components/ui/USkeleton.vue";
import UEmpty from "../components/ui/UEmpty.vue";
import { useMetrics } from "../composables/useMetrics";
import { useRecentAlerts, severityStatus, relativeTime, firedAtFor } from "../composables/useRecentAlerts";
import { useEventStream, eventBadgeStatus, eventTypeOf, eventTimestampOf, type StreamEvent } from "../composables/useEventStream";

const router = useRouter();
const onboardingDismissed = ref(localStorage.getItem('hubex_onboarding_dismissed') === 'true');
watch(onboardingDismissed, (v) => { if (v) localStorage.setItem('hubex_onboarding_dismissed', 'true'); });

const { data: metrics, loading: metricsLoading } = useMetrics();
const { alerts, loading: alertsLoading } = useRecentAlerts();
const { events, loading: eventsLoading } = useEventStream();

// ── Activity feed — progressive disclosure ───────────────────────────────────
const activityExpanded = ref(false);
const COLLAPSED_COUNT = 5;

const visibleEvents = computed(() => {
  if (activityExpanded.value) return events.value.slice(0, 10);
  return events.value.slice(0, COLLAPSED_COUNT);
});

const canExpandEvents = computed(() => events.value.length > COLLAPSED_COUNT);

// ── Online % for fleet health label ──────────────────────────────────────────
const onlinePct = computed(() => {
  const m = metrics.value;
  if (!m || m.devices.total === 0) return 0;
  return Math.round((m.devices.online / m.devices.total) * 100);
});

// ── Event description helper ─────────────────────────────────────────────────
function eventDescription(event: StreamEvent): string {
  const parts: string[] = [];
  // Make event type human readable: "device.online" -> "Device Online"
  const type = eventTypeOf(event);
  if (type) {
    parts.push(type.replace(/[._]/g, ' ').replace(/\b\w/g, c => c.toUpperCase()));
  }
  if (event.stream) parts.push(`[${event.stream}]`);
  return parts.join(' ');
}

function eventRelativeTime(dateStr: string | undefined | null): string {
  if (!dateStr) return "";
  const parsed = new Date(dateStr).getTime();
  if (isNaN(parsed)) return "";
  const diff = Date.now() - parsed;
  const secs = Math.floor(diff / 1000);
  const mins = Math.floor(secs / 60);
  const hours = Math.floor(mins / 60);
  const days = Math.floor(hours / 24);
  if (days > 0) return `${days}d`;
  if (hours > 0) return `${hours}h`;
  if (mins > 0) return `${mins}m`;
  return `${secs}s`;
}

function eventIcon(eventType: string): string {
  if (eventType.startsWith('device.')) return 'M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z';
  if (eventType.startsWith('alert.')) return 'M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0';
  if (eventType.startsWith('task.') || eventType.startsWith('automation.')) return 'M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z';
  if (eventType.startsWith('telemetry.')) return 'M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z';
  return 'M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z';
}

function eventIconColor(eventType: string): string {
  if (eventType.startsWith('device.')) return 'text-[var(--primary)]';
  if (eventType.startsWith('alert.')) return 'text-[var(--status-bad)]';
  if (eventType.startsWith('task.') || eventType.startsWith('automation.')) return 'text-[var(--accent-cyan)]';
  if (eventType.startsWith('telemetry.')) return 'text-[var(--accent-amber)]';
  return 'text-[var(--text-muted)]';
}
</script>

<template>
  <div class="space-y-6">
    <!-- ── 0. Getting Started Guide ─────────────────────────────────────── -->
    <div
      v-if="!metricsLoading && metrics && !onboardingDismissed"
      class="rounded-xl border border-[var(--primary)]/30 bg-[var(--primary)]/5 px-5 py-4"
    >
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <span class="text-lg">&#x1F680;</span>
          <p class="text-sm font-semibold text-[var(--text-primary)]">{{ t('dashboard.gettingStarted') }}</p>
        </div>
        <button class="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]" @click="onboardingDismissed = true">{{ t('dashboard.dismiss') }} &times;</button>
      </div>
      <div class="grid grid-cols-2 sm:grid-cols-5 gap-2">
        <button class="flex flex-col items-center gap-1.5 p-3 rounded-lg border transition-colors text-center"
          :class="metrics.devices.total > 0 ? 'border-[var(--status-ok)]/30 bg-[var(--status-ok)]/5 text-[var(--status-ok)]' : 'border-[var(--border)] bg-[var(--bg-raised)] text-[var(--text-muted)] hover:border-[var(--primary)]/40'"
          @click="router.push('/devices?wizard=open')">
          <span class="text-lg">{{ metrics.devices.total > 0 ? '&#10003;' : '1' }}</span>
          <span class="text-[10px] font-medium">{{ t('dashboard.addDevice') }}</span>
        </button>
        <button class="flex flex-col items-center gap-1.5 p-3 rounded-lg border transition-colors text-center"
          :class="metrics.devices.online > 0 ? 'border-[var(--status-ok)]/30 bg-[var(--status-ok)]/5 text-[var(--status-ok)]' : 'border-[var(--border)] bg-[var(--bg-raised)] text-[var(--text-muted)] hover:border-[var(--primary)]/40'"
          @click="router.push('/variables')">
          <span class="text-lg">{{ metrics.devices.online > 0 ? '&#10003;' : '2' }}</span>
          <span class="text-[10px] font-medium">{{ t('dashboard.seeData') }}</span>
        </button>
        <button class="flex flex-col items-center gap-1.5 p-3 rounded-lg border border-[var(--border)] bg-[var(--bg-raised)] text-[var(--text-muted)] hover:border-[var(--primary)]/40 transition-colors text-center"
          @click="router.push('/alerts?create=true')">
          <span class="text-lg">3</span>
          <span class="text-[10px] font-medium">{{ t('dashboard.setAlert') }}</span>
        </button>
        <button class="flex flex-col items-center gap-1.5 p-3 rounded-lg border border-[var(--border)] bg-[var(--bg-raised)] text-[var(--text-muted)] hover:border-[var(--primary)]/40 transition-colors text-center"
          @click="router.push('/dashboards')">
          <span class="text-lg">4</span>
          <span class="text-[10px] font-medium">{{ t('dashboard.buildDashboard') }}</span>
        </button>
        <button class="flex flex-col items-center gap-1.5 p-3 rounded-lg border border-[var(--border)] bg-[var(--bg-raised)] text-[var(--text-muted)] hover:border-[var(--primary)]/40 transition-colors text-center"
          @click="router.push('/automations?create=true')">
          <span class="text-lg">5</span>
          <span class="text-[10px] font-medium">{{ t('dashboard.automate') }}</span>
        </button>
      </div>
    </div>

    <!-- ── 1. KPI Cards (4 tiles) ──────────────────────────────────────── -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- Loading skeletons -->
      <template v-if="metricsLoading">
        <div
          v-for="i in 4"
          :key="i"
          class="rounded-xl border bg-[var(--bg-surface)] border-[var(--border)] p-5"
        >
          <USkeleton height="0.75rem" width="60%" class="mb-3" />
          <USkeleton height="2.5rem" width="40%" class="mb-2" />
          <USkeleton height="0.625rem" width="50%" />
        </div>
      </template>

      <template v-else-if="metrics">
        <!-- Devices Online -->
        <div
          class="kpi-card group cursor-pointer"
          @click="router.push('/devices')"
        >
          <div class="kpi-icon-wrap bg-[var(--status-ok)]/10">
            <svg class="h-4 w-4 text-[var(--status-ok)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p
            class="kpi-number"
            :class="
              metrics.devices.total === 0
                ? 'text-[var(--text-muted)]'
                : onlinePct >= 80
                  ? 'text-[var(--status-ok)]'
                  : onlinePct >= 50
                    ? 'text-[var(--status-warn)]'
                    : 'text-[var(--status-bad)]'
            "
          >{{ metrics.devices.online }}</p>
          <p class="kpi-label">{{ t('dashboard.devicesOnline') }}</p>
          <!--
            Sprint 5 REAL-10 fix: replaced vague "Major outage" label
            (which clashed with the positive-looking big number "6") with
            an honest "6 / 13 online" ratio. Number color also now
            encodes health so users get the warn signal visually.
          -->
          <p class="kpi-sub">
            <template v-if="metrics.devices.total === 0">
              {{ t('dashboard.noDevices') }}
            </template>
            <template v-else-if="metrics.devices.online === 0">
              {{ t('dashboard.allOffline') }}
            </template>
            <template v-else>
              {{ t('dashboard.onlineRatio', { online: metrics.devices.online, total: metrics.devices.total }) }}
            </template>
          </p>
        </div>

        <!-- Active Alerts -->
        <div
          class="kpi-card group cursor-pointer"
          @click="router.push('/alerts')"
        >
          <div :class="['kpi-icon-wrap', metrics.alerts.firing > 0 ? 'bg-[var(--status-bad)]/10' : 'bg-[var(--bg-raised)]']">
            <svg
              :class="['h-4 w-4', metrics.alerts.firing > 0 ? 'text-[var(--status-bad)]' : 'text-[var(--text-muted)]']"
              fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
            </svg>
          </div>
          <p :class="['kpi-number', metrics.alerts.firing > 0 ? 'text-[var(--status-bad)]' : 'text-[var(--text-primary)]']">
            {{ metrics.alerts.firing }}
          </p>
          <p class="kpi-label">{{ t('dashboard.activeAlerts') }}</p>
          <p class="kpi-sub">
            {{ metrics.alerts.firing === 0 ? t('dashboard.noActiveAlerts') : t('dashboard.rulesFiring', { count: metrics.alerts.firing }, metrics.alerts.firing) }}
          </p>
        </div>

        <!-- Events Today -->
        <div
          class="kpi-card group cursor-pointer"
          @click="router.push('/events')"
        >
          <div class="kpi-icon-wrap bg-[var(--accent-amber)]/10">
            <svg class="h-4 w-4 text-[var(--accent-amber)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" />
            </svg>
          </div>
          <p class="kpi-number text-[var(--text-primary)]">{{ metrics.events_24h }}</p>
          <p class="kpi-label">{{ t('dashboard.eventsToday') }}</p>
        </div>

        <!-- Automations Active -->
        <div
          class="kpi-card group cursor-pointer"
          @click="router.push('/automations')"
        >
          <div class="kpi-icon-wrap bg-[var(--accent-cyan)]/10">
            <svg class="h-4 w-4 text-[var(--accent-cyan)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
            </svg>
          </div>
          <p class="kpi-number text-[var(--text-primary)]">{{ metrics.automations_active }}</p>
          <p class="kpi-label">{{ t('dashboard.automationsActive') }}</p>
        </div>
      </template>
    </div>

    <!-- ── 2. Recent Alerts ────────────────────────────────────────────── -->
    <UCard data-testid="recent-alerts">
      <template #header>
        <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('dashboard.recentAlerts') }}</h3>
        <UButton size="sm" variant="ghost" @click="router.push('/alerts')">{{ t('dashboard.viewAll') }}</UButton>
      </template>

      <!-- Loading -->
      <div v-if="alertsLoading" class="space-y-3 py-2">
        <div v-for="i in 3" :key="i" class="flex gap-3 items-start">
          <USkeleton width="4.5rem" height="1.25rem" rounded="full" />
          <div class="flex-1">
            <USkeleton height="1rem" class="mb-1" />
            <USkeleton height="0.75rem" width="40%" />
          </div>
        </div>
      </div>

      <!-- Empty — calm green state -->
      <div
        v-else-if="alerts.length === 0"
        class="flex items-center gap-3 py-4 px-2"
        data-testid="alerts-empty"
      >
        <div class="p-2 rounded-full bg-[var(--status-ok)]/10">
          <svg class="h-5 w-5 text-[var(--status-ok)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div>
          <p class="text-sm font-medium text-[var(--status-ok)]">{{ t('dashboard.noActiveAlerts') }}</p>
          <p class="text-xs text-[var(--text-muted)]">{{ t('dashboard.allClear') }}</p>
        </div>
      </div>

      <!-- Alert list -->
      <div v-else class="divide-y divide-[var(--border)]">
        <div
          v-for="alert in alerts"
          :key="alert.id"
          class="flex items-center gap-3 py-3 px-1 rounded-lg cursor-pointer hover:bg-[var(--bg-raised)] transition-colors"
          @click="router.push('/alerts')"
        >
          <UBadge :status="severityStatus(alert.severity)" class="shrink-0">
            {{ alert.severity }}
          </UBadge>
          <p class="text-sm text-[var(--text-primary)] truncate flex-1 min-w-0">{{ alert.message }}</p>
          <span class="text-xs text-[var(--text-muted)] shrink-0">{{ relativeTime(firedAtFor(alert)) }}</span>
        </div>
      </div>
    </UCard>

    <!-- ── 3. Activity Feed ────────────────────────────────────────────── -->
    <UCard data-testid="activity-feed">
      <template #header>
        <div class="flex items-center gap-2">
          <span
            v-if="!eventsLoading && events.length > 0"
            class="h-1.5 w-1.5 rounded-full bg-[var(--status-ok)] animate-pulse-slow"
          />
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('dashboard.eventStream') }}</h3>
        </div>
        <UButton size="sm" variant="ghost" @click="router.push('/events')">{{ t('dashboard.viewAll') }}</UButton>
      </template>

      <!-- Loading -->
      <div v-if="eventsLoading" class="space-y-3 py-2">
        <div v-for="i in 5" :key="i" class="flex gap-3 items-center">
          <USkeleton width="1.5rem" height="1.5rem" rounded="full" />
          <USkeleton height="1rem" class="flex-1" />
          <USkeleton width="2rem" height="0.75rem" />
        </div>
      </div>

      <!-- Empty -->
      <UEmpty
        v-else-if="events.length === 0"
        :title="t('dashboard.noRecentEvents')"
        :description="t('dashboard.eventsAppearHere')"
      />

      <!-- Event timeline -->
      <div v-else class="divide-y divide-[var(--border)]">
        <div
          v-for="event in visibleEvents"
          :key="event.id"
          class="flex items-center gap-3 py-2.5 px-1"
        >
          <!-- Icon -->
          <div class="shrink-0 p-1.5 rounded-lg bg-[var(--bg-raised)]">
            <svg :class="['h-3.5 w-3.5', eventIconColor(eventTypeOf(event))]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" :d="eventIcon(eventTypeOf(event))" />
            </svg>
          </div>
          <!-- Description -->
          <p class="text-sm text-[var(--text-primary)] truncate flex-1 min-w-0">
            {{ eventDescription(event) }}
          </p>
          <!-- Time -->
          <span class="text-xs text-[var(--text-muted)] shrink-0 font-mono">
            {{ eventRelativeTime(eventTimestampOf(event)) }}
          </span>
        </div>

        <!-- Show more / Show less -->
        <div v-if="canExpandEvents" class="pt-2 pb-1 text-center">
          <button
            class="text-xs text-[var(--primary)] hover:text-[var(--primary-hover)] font-medium transition-colors"
            @click="activityExpanded = !activityExpanded"
          >
            {{ activityExpanded ? t('dashboard.showLess') : t('dashboard.showMore') }}
          </button>
        </div>
      </div>
    </UCard>
  </div>
</template>

<style scoped>
.kpi-card {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 1.25rem;
  border-radius: 0.75rem;
  border: 1px solid var(--border);
  background: var(--bg-surface);
  transition: border-color 0.15s, box-shadow 0.15s;
}
.kpi-card:hover {
  border-color: color-mix(in srgb, var(--primary) 40%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--primary) 10%, transparent);
}
.kpi-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
  margin-bottom: 0.5rem;
}
.kpi-number {
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
  font-size: 2rem;
  font-weight: 700;
  line-height: 1;
}
.kpi-label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.025em;
  margin-top: 0.25rem;
}
.kpi-sub {
  font-size: 0.6875rem;
  color: var(--text-muted);
  margin-top: 0.125rem;
}
</style>
