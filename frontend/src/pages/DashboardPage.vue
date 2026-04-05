<script setup lang="ts">
import { computed, ref, watch, nextTick } from "vue";
import { useRouter } from "vue-router";
import UCard from "../components/ui/UCard.vue";
import UBadge from "../components/ui/UBadge.vue";
import UButton from "../components/ui/UButton.vue";
import USkeleton from "../components/ui/USkeleton.vue";
import UEmpty from "../components/ui/UEmpty.vue";
import { useMetrics, formatUptime } from "../composables/useMetrics";
import { useRecentAlerts, severityStatus, relativeTime } from "../composables/useRecentAlerts";
import { useEventStream, eventBadgeStatus, payloadPreview } from "../composables/useEventStream";

const router = useRouter();

const { data: metrics, loading: metricsLoading } = useMetrics();
const { alerts, loading: alertsLoading } = useRecentAlerts();
const { events, loading: eventsLoading, paused: streamPaused, togglePause } = useEventStream();

// ── SVG Donut Chart ───────────────────────────────────────────────────────────
const RADIUS = 60;
const CIRC = 2 * Math.PI * RADIUS;

const donutSegments = computed(() => {
  const m = metrics.value;
  if (!m || m.devices.total === 0) return [];
  const total = m.devices.total;
  const defs = [
    { label: "Online",  count: m.devices.online,  color: "var(--status-ok)",   pct: m.devices.online / total },
    { label: "Stale",   count: m.devices.stale,   color: "var(--status-warn)", pct: m.devices.stale / total  },
    { label: "Offline", count: m.devices.offline, color: "var(--status-bad)",  pct: m.devices.offline / total },
  ];
  let angle = -90;
  return defs.map((seg) => {
    const startAngle = angle;
    angle += seg.pct * 360;
    const dash = seg.pct * CIRC;
    const gap  = CIRC - dash;
    return { ...seg, startAngle, dash, gap };
  });
});

// ── Devices mini-bar ──────────────────────────────────────────────────────────
const deviceBarSegments = computed(() => {
  const m = metrics.value;
  if (!m || m.devices.total === 0) return [];
  const t = m.devices.total;
  return [
    { label: "Online",  pct: (m.devices.online / t) * 100,  cls: "bg-[var(--status-ok)]"   },
    { label: "Stale",   pct: (m.devices.stale / t) * 100,   cls: "bg-[var(--status-warn)]" },
    { label: "Offline", pct: (m.devices.offline / t) * 100, cls: "bg-[var(--status-bad)]"  },
  ].filter((s) => s.pct > 0);
});

const onlinePct = computed(() => {
  const m = metrics.value;
  if (!m || m.devices.total === 0) return 0;
  return Math.round((m.devices.online / m.devices.total) * 100);
});

// ── Online % Arc (small arc in Online tile) ───────────────────────────────────
const ARC_R    = 30;
const ARC_CIRC = 2 * Math.PI * ARC_R;
const arcDash  = computed(() => (onlinePct.value / 100) * ARC_CIRC);
const arcGap   = computed(() => ARC_CIRC - arcDash.value);
const arcStroke = computed(() =>
  onlinePct.value >= 80 ? "var(--status-ok)"
  : onlinePct.value >= 50 ? "var(--status-warn)"
  : "var(--status-bad)"
);

// ── Event stream auto-scroll ──────────────────────────────────────────────────
const eventListRef = ref<HTMLElement | null>(null);

watch(events, async () => {
  if (streamPaused.value) return;
  await nextTick();
  if (eventListRef.value) eventListRef.value.scrollTop = 0;
});
</script>

<template>
  <div class="space-y-6">
    <!-- ── 0. Welcome Banner (fresh install / no devices) ─────────────────── -->
    <div
      v-if="!metricsLoading && metrics && metrics.devices.total === 0"
      class="rounded-xl border border-[var(--primary)]/30 bg-[var(--primary)]/5 px-5 py-4 flex flex-col sm:flex-row items-start sm:items-center gap-4"
    >
      <div class="p-2.5 rounded-lg bg-[var(--primary)]/10 shrink-0">
        <svg class="h-6 w-6 text-[var(--primary)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" />
        </svg>
      </div>
      <div class="flex-1 min-w-0">
        <p class="text-sm font-semibold text-[var(--text-primary)]">Welcome to HUBEX</p>
        <p class="text-xs text-[var(--text-muted)] mt-0.5">No devices yet — pair your first device to start monitoring.</p>
      </div>
      <UButton size="sm" @click="router.push('/devices')">
        Pair Device
      </UButton>
    </div>

    <!-- ── 1. Hero Stats (3 large tiles) ────────────────────────────────────── -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <!-- Loading skeletons -->
      <template v-if="metricsLoading">
        <div
          v-for="i in 3"
          :key="i"
          class="rounded-xl border bg-[var(--bg-surface)] border-[var(--border)] p-5"
        >
          <USkeleton height="0.75rem" width="40%" class="mb-4" />
          <USkeleton height="3rem" width="50%" class="mb-3" />
          <USkeleton height="0.5rem" class="mb-2" />
          <USkeleton height="0.75rem" width="60%" />
        </div>
      </template>

      <template v-else-if="metrics">
        <!-- Total Devices tile -->
        <UCard padding="md" data-testid="card-devices-total">
          <div class="flex items-center gap-2 mb-3">
            <div class="p-1.5 rounded-lg bg-[var(--bg-raised)]">
              <svg class="h-4 w-4 text-[var(--primary)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z" />
              </svg>
            </div>
            <span class="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wide">Total Devices</span>
          </div>
          <p class="text-5xl font-mono font-bold text-[var(--text-primary)] mb-4">{{ metrics.devices.total }}</p>
          <!-- Health bar -->
          <div class="h-2 rounded-full overflow-hidden flex bg-[var(--bg-raised)] mb-2">
            <div
              v-for="seg in deviceBarSegments"
              :key="seg.label"
              :class="seg.cls"
              :style="{ width: seg.pct + '%' }"
            />
          </div>
          <div class="flex gap-4">
            <span class="text-[11px] text-[var(--status-ok)] font-medium">{{ metrics.devices.online }} online</span>
            <span class="text-[11px] text-[var(--status-warn)] font-medium">{{ metrics.devices.stale }} stale</span>
            <span class="text-[11px] text-[var(--status-bad)] font-medium">{{ metrics.devices.offline }} offline</span>
          </div>
        </UCard>

        <!-- Devices Online tile with arc -->
        <UCard padding="md" data-testid="card-devices-online">
          <div class="flex items-center gap-2 mb-3">
            <div class="p-1.5 rounded-lg bg-[var(--status-ok)]/10">
              <svg class="h-4 w-4 text-[var(--status-ok)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <span class="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wide">Online Now</span>
          </div>
          <div class="flex items-center gap-5">
            <div>
              <p class="text-5xl font-mono font-bold text-[var(--status-ok)]">{{ metrics.devices.online }}</p>
              <p class="text-xs text-[var(--text-muted)] mt-1">
                {{ onlinePct >= 80 ? "Fleet healthy" : onlinePct >= 50 ? "Partial outage" : "Major outage" }}
              </p>
            </div>
            <!-- Arc SVG -->
            <svg width="72" height="72" viewBox="0 0 72 72" class="shrink-0 ml-auto" aria-label="Online percentage arc">
              <circle cx="36" cy="36" r="30" fill="none" stroke="var(--bg-raised)" stroke-width="7" />
              <circle
                cx="36" cy="36" r="30"
                fill="none"
                :stroke="arcStroke"
                stroke-width="7"
                stroke-linecap="round"
                :stroke-dasharray="`${arcDash} ${arcGap}`"
                transform="rotate(-90 36 36)"
              />
              <text x="36" y="40" text-anchor="middle" font-size="13" font-weight="700"
                fill="var(--text-primary)" font-family="ui-monospace, monospace">{{ onlinePct }}%</text>
            </svg>
          </div>
        </UCard>

        <!-- Active Alerts tile -->
        <UCard padding="md" data-testid="card-alerts">
          <div class="flex items-center gap-2 mb-3">
            <div :class="['p-1.5 rounded-lg', metrics.alerts.firing > 0 ? 'bg-[var(--status-bad)]/10' : 'bg-[var(--bg-raised)]']">
              <svg
                :class="['h-4 w-4', metrics.alerts.firing > 0 ? 'text-[var(--status-bad)]' : 'text-[var(--text-muted)]']"
                fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
              </svg>
            </div>
            <span class="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wide">Active Alerts</span>
            <UBadge v-if="metrics.alerts.firing > 0" status="bad" :pulse="true" class="ml-auto">
              firing
            </UBadge>
          </div>
          <p :class="['text-5xl font-mono font-bold mb-1', metrics.alerts.firing > 0 ? 'text-[var(--status-bad)]' : 'text-[var(--text-primary)]']">
            {{ metrics.alerts.firing }}
          </p>
          <p :class="['text-xs', metrics.alerts.firing > 0 ? 'text-[var(--status-bad)]/80' : 'text-[var(--text-muted)]']">
            {{ metrics.alerts.firing === 0 ? "All clear — no active alerts" : `${metrics.alerts.firing} rule${metrics.alerts.firing > 1 ? 's' : ''} currently firing` }}
          </p>
        </UCard>
      </template>
    </div>

    <!-- ── 2. Info Stats (3 smaller tiles) ───────────────────────────────────── -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <template v-if="metricsLoading">
        <div v-for="i in 3" :key="i" class="rounded-xl border bg-[var(--bg-surface)] border-[var(--border)] p-4 flex items-center gap-3">
          <USkeleton width="2.5rem" height="2.5rem" rounded="lg" />
          <div class="flex-1"><USkeleton height="1.5rem" width="40%" class="mb-1" /><USkeleton height="0.75rem" width="60%" /></div>
        </div>
      </template>
      <template v-else-if="metrics">
        <!-- Entities -->
        <UCard padding="md" data-testid="card-entities" class="cursor-pointer hover:border-[var(--primary)]/40 transition-colors" @click="router.push('/entities')">
          <div class="flex items-center gap-3">
            <div class="p-2 rounded-lg bg-[var(--bg-raised)] shrink-0">
              <svg class="h-5 w-5 text-[var(--primary)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
              </svg>
            </div>
            <div>
              <p class="text-2xl font-mono font-bold text-[var(--text-primary)]">{{ metrics.entities_total }}</p>
              <p class="text-xs text-[var(--text-muted)]">Entities</p>
            </div>
          </div>
        </UCard>
        <!-- Events 24h -->
        <UCard padding="md" data-testid="card-events" class="cursor-pointer hover:border-[var(--accent-amber)]/40 transition-colors" @click="router.push('/events')">
          <div class="flex items-center gap-3">
            <div class="p-2 rounded-lg bg-[var(--bg-raised)] shrink-0">
              <svg class="h-5 w-5 text-[var(--accent-amber)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" />
              </svg>
            </div>
            <div>
              <p class="text-2xl font-mono font-bold text-[var(--text-primary)]">{{ metrics.events_24h }}</p>
              <p class="text-xs text-[var(--text-muted)]">Events (24h)</p>
            </div>
          </div>
        </UCard>
        <!-- Uptime -->
        <UCard padding="md" data-testid="card-uptime">
          <div class="flex items-center gap-3">
            <div class="p-2 rounded-lg bg-[var(--bg-raised)] shrink-0">
              <svg class="h-5 w-5 text-[var(--accent-lime)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <p class="text-2xl font-mono font-bold text-[var(--text-primary)]">{{ formatUptime(metrics.uptime_seconds) }}</p>
              <p class="text-xs text-[var(--text-muted)]">Uptime</p>
            </div>
          </div>
        </UCard>
      </template>
    </div>

    <!-- ── 3b. Quick Actions (M20) ────────────────────────────────────────── -->
    <div v-if="!metricsLoading && metrics" class="flex flex-wrap gap-2">
      <button
        class="quick-action-btn"
        @click="router.push('/alerts')"
      >
        <svg class="h-3.5 w-3.5 text-[var(--status-bad)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
        </svg>
        Active Alerts ({{ metrics.alerts.firing }})
      </button>
      <button
        class="quick-action-btn"
        @click="router.push('/devices')"
      >
        <svg class="h-3.5 w-3.5 text-[var(--status-warn)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 3l8.735 8.735m0 0a.374.374 0 11.53.53m-.53-.53l.53.53m-.53-.53L21 21" />
        </svg>
        Offline Devices ({{ metrics.devices.offline }})
      </button>
      <button
        class="quick-action-btn"
        @click="router.push('/automations')"
      >
        <svg class="h-3.5 w-3.5 text-[var(--primary)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
        </svg>
        Automations
      </button>
      <button
        class="quick-action-btn"
        @click="router.push('/dashboards')"
      >
        <svg class="h-3.5 w-3.5 text-[var(--accent-cyan)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6z" />
        </svg>
        Dashboards
      </button>
    </div>

    <!-- ── 4. Recent Alerts (full width) ─────────────────────────────────── -->
    <div>
      <!-- Recent Alerts -->
      <UCard data-testid="recent-alerts">
        <template #header>
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">Recent Alerts</h3>
          <UButton size="sm" variant="ghost" @click="router.push('/alerts')">View All</UButton>
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

        <!-- Empty -->
        <UEmpty
          v-else-if="alerts.length === 0"
          title="No active alerts"
          description="All systems are operating normally."
          icon="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          data-testid="alerts-empty"
        />

        <!-- Alert list -->
        <div v-else class="divide-y divide-[var(--border)]">
          <div
            v-for="alert in alerts"
            :key="alert.id"
            class="flex items-start gap-3 py-3 px-1 rounded-lg cursor-pointer hover:bg-[var(--bg-raised)] transition-colors"
            @click="router.push('/alerts')"
          >
            <UBadge :status="severityStatus(alert.severity)" class="shrink-0 mt-px">
              {{ alert.severity }}
            </UBadge>
            <div class="flex-1 min-w-0">
              <p class="text-sm text-[var(--text-primary)] truncate">{{ alert.message }}</p>
              <p class="text-xs text-[var(--text-muted)] mt-0.5">{{ relativeTime(alert.fired_at) }}</p>
            </div>
          </div>
        </div>
      </UCard>
    </div>

    <!-- ── 3. Quick Actions ────────────────────────────────────────────────── -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      <UCard
        padding="md"
        class="cursor-pointer hover:border-[var(--primary)]/50 transition-colors group"
        @click="router.push('/devices')"
      >
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-[var(--primary)]/10 shrink-0 group-hover:bg-[var(--primary)]/20 transition-colors">
            <svg class="h-5 w-5 text-[var(--primary)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-semibold text-[var(--text-primary)]">Pair Device</p>
            <p class="text-xs text-[var(--text-muted)] truncate">Add a new device</p>
          </div>
          <svg class="h-4 w-4 text-[var(--text-muted)] shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </div>
      </UCard>

      <UCard
        padding="md"
        class="cursor-pointer hover:border-[var(--primary)]/40 transition-colors group"
        @click="router.push('/devices')"
      >
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-[var(--bg-raised)] shrink-0 group-hover:bg-[var(--bg-card)] transition-colors">
            <svg class="h-5 w-5 text-[var(--text-secondary)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z" />
            </svg>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-semibold text-[var(--text-primary)]">View Devices</p>
            <p class="text-xs text-[var(--text-muted)] truncate">Monitor your fleet</p>
          </div>
          <svg class="h-4 w-4 text-[var(--text-muted)] shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </div>
      </UCard>

      <UCard
        padding="md"
        class="cursor-pointer hover:border-[var(--status-bad)]/40 transition-colors group"
        @click="router.push('/alerts')"
      >
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-[var(--bg-raised)] shrink-0 group-hover:bg-[var(--status-bad)]/10 transition-colors">
            <svg class="h-5 w-5 text-[var(--text-secondary)] group-hover:text-[var(--status-bad)] transition-colors" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
            </svg>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-semibold text-[var(--text-primary)]">Create Alert</p>
            <p class="text-xs text-[var(--text-muted)] truncate">Set up notifications</p>
          </div>
          <svg class="h-4 w-4 text-[var(--text-muted)] shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </div>
      </UCard>

      <UCard
        padding="md"
        class="cursor-pointer hover:border-[var(--primary)]/40 transition-colors group"
        @click="router.push('/entities')"
      >
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-[var(--bg-raised)] shrink-0 group-hover:bg-[var(--bg-card)] transition-colors">
            <svg class="h-5 w-5 text-[var(--text-secondary)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
            </svg>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-semibold text-[var(--text-primary)]">View Entities</p>
            <p class="text-xs text-[var(--text-muted)] truncate">Groups &amp; logical things</p>
          </div>
          <svg class="h-4 w-4 text-[var(--text-muted)] shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </div>
      </UCard>
    </div>

    <!-- ── 5. Event Stream ─────────────────────────────────────────────────── -->
    <UCard data-testid="event-stream">
      <template #header>
        <div class="flex items-center gap-2">
          <span
            v-if="!streamPaused"
            class="h-1.5 w-1.5 rounded-full bg-[var(--status-ok)] animate-pulse-slow"
          />
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">Event Stream</h3>
        </div>
        <UButton size="sm" variant="ghost" @click="togglePause">
          <!-- Resume icon -->
          <svg v-if="streamPaused" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
          </svg>
          <!-- Pause icon -->
          <svg v-else class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 5.25v13.5m-7.5-13.5v13.5" />
          </svg>
          {{ streamPaused ? "Resume" : "Pause" }}
        </UButton>
      </template>

      <!-- Loading -->
      <div v-if="eventsLoading" class="space-y-2 py-1">
        <div v-for="i in 5" :key="i" class="flex gap-3 items-center">
          <USkeleton width="7rem" height="1rem" />
          <USkeleton width="6rem" height="1.25rem" rounded="full" />
          <USkeleton height="1rem" />
        </div>
      </div>

      <!-- Event list -->
      <div
        v-else-if="events.length"
        ref="eventListRef"
        class="max-h-72 overflow-y-auto divide-y divide-[var(--border)]"
      >
        <div
          v-for="event in events"
          :key="event.id"
          class="flex items-center gap-2 py-2 px-1 text-xs"
        >
          <span class="font-mono text-[var(--text-muted)] shrink-0 hidden sm:block w-24 truncate">
            {{ new Date(event.created_at).toLocaleTimeString() }}
          </span>
          <UBadge :status="eventBadgeStatus(event.event_type)" class="shrink-0 max-w-[8rem] truncate">
            {{ event.event_type }}
          </UBadge>
          <span class="text-[var(--text-secondary)] shrink-0 truncate max-w-[5rem] hidden md:block">{{ event.stream }}</span>
          <span class="font-mono text-[var(--text-muted)] truncate flex-1">
            {{ payloadPreview(event.payload) }}
          </span>
        </div>
      </div>

      <!-- Empty -->
      <UEmpty
        v-else
        title="No recent events"
        description="Events will appear here as they arrive."
      />
    </UCard>
  </div>
</template>

<style scoped>
.quick-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg-surface);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}
.quick-action-btn:hover {
  border-color: var(--primary);
  color: var(--text-base);
  background: color-mix(in srgb, var(--primary) 5%, transparent);
}
</style>
