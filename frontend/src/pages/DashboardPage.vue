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
    <!-- ── 1. Metric Cards ─────────────────────────────────────────────────── -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <!-- Loading skeletons -->
      <template v-if="metricsLoading">
        <div
          v-for="i in 6"
          :key="i"
          class="rounded-xl border bg-[var(--bg-surface)] border-[var(--border)] p-5"
        >
          <USkeleton height="1rem" width="40%" class="mb-3" />
          <USkeleton height="2rem" width="55%" class="mb-2" />
          <USkeleton height="0.75rem" width="70%" />
        </div>
      </template>

      <template v-else-if="metrics">
        <!-- Devices Total -->
        <UCard padding="md" data-testid="card-devices-total">
          <div class="flex items-start justify-between mb-3">
            <div class="p-2 rounded-lg bg-[var(--bg-raised)]">
              <svg class="h-5 w-5 text-[var(--accent-cyan)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z" />
              </svg>
            </div>
          </div>
          <p class="text-3xl font-mono font-bold text-[var(--text-primary)]">{{ metrics.devices.total }}</p>
          <p class="text-xs text-[var(--text-muted)] mt-1">Total Devices</p>
          <!-- Mini breakdown bar -->
          <div class="mt-3 h-1.5 rounded-full overflow-hidden flex bg-[var(--bg-raised)]">
            <div
              v-for="seg in deviceBarSegments"
              :key="seg.label"
              :class="seg.cls"
              :style="{ width: seg.pct + '%' }"
            />
          </div>
          <div class="mt-1.5 flex gap-3 flex-wrap">
            <span class="text-[10px] text-[var(--status-ok)]">{{ metrics.devices.online }} online</span>
            <span class="text-[10px] text-[var(--status-warn)]">{{ metrics.devices.stale }} stale</span>
            <span class="text-[10px] text-[var(--status-bad)]">{{ metrics.devices.offline }} offline</span>
          </div>
        </UCard>

        <!-- Devices Online -->
        <UCard padding="md" data-testid="card-devices-online">
          <div class="flex items-start justify-between mb-3">
            <div class="p-2 rounded-lg bg-[var(--status-ok)]/10">
              <svg class="h-5 w-5 text-[var(--status-ok)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <span class="text-xs font-mono text-[var(--status-ok)]">{{ onlinePct }}%</span>
          </div>
          <p class="text-3xl font-mono font-bold text-[var(--status-ok)]">{{ metrics.devices.online }}</p>
          <p class="text-xs text-[var(--text-muted)] mt-1">Devices Online</p>
        </UCard>

        <!-- Entities -->
        <UCard padding="md" data-testid="card-entities">
          <div class="flex items-start justify-between mb-3">
            <div class="p-2 rounded-lg bg-[var(--bg-raised)]">
              <svg class="h-5 w-5 text-[var(--accent-cyan)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
              </svg>
            </div>
          </div>
          <p class="text-3xl font-mono font-bold text-[var(--text-primary)]">{{ metrics.entities_total }}</p>
          <p class="text-xs text-[var(--text-muted)] mt-1">Entities</p>
        </UCard>

        <!-- Active Alerts -->
        <UCard padding="md" data-testid="card-alerts">
          <div class="flex items-start justify-between mb-3">
            <div
              :class="[
                'p-2 rounded-lg',
                metrics.alerts.firing > 0 ? 'bg-[var(--status-bad)]/10' : 'bg-[var(--bg-raised)]',
              ]"
            >
              <svg
                :class="['h-5 w-5', metrics.alerts.firing > 0 ? 'text-[var(--status-bad)]' : 'text-[var(--text-muted)]']"
                fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
              </svg>
            </div>
            <UBadge v-if="metrics.alerts.firing > 0" status="bad" :pulse="true">
              {{ metrics.alerts.firing }} firing
            </UBadge>
          </div>
          <p
            :class="[
              'text-3xl font-mono font-bold',
              metrics.alerts.firing > 0 ? 'text-[var(--status-bad)]' : 'text-[var(--text-primary)]',
            ]"
          >{{ metrics.alerts.firing }}</p>
          <p class="text-xs text-[var(--text-muted)] mt-1">Active Alerts</p>
        </UCard>

        <!-- Events 24h -->
        <UCard padding="md" data-testid="card-events">
          <div class="flex items-start justify-between mb-3">
            <div class="p-2 rounded-lg bg-[var(--bg-raised)]">
              <svg class="h-5 w-5 text-[var(--accent-amber)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" />
              </svg>
            </div>
          </div>
          <p class="text-3xl font-mono font-bold text-[var(--text-primary)]">{{ metrics.events_24h }}</p>
          <p class="text-xs text-[var(--text-muted)] mt-1">Events (24h)</p>
        </UCard>

        <!-- Uptime -->
        <UCard padding="md" data-testid="card-uptime">
          <div class="flex items-start justify-between mb-3">
            <div class="p-2 rounded-lg bg-[var(--bg-raised)]">
              <svg class="h-5 w-5 text-[var(--accent-lime)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <p class="text-3xl font-mono font-bold text-[var(--text-primary)]">
            {{ formatUptime(metrics.uptime_seconds) }}
          </p>
          <p class="text-xs text-[var(--text-muted)] mt-1">Uptime</p>
        </UCard>
      </template>
    </div>

    <!-- ── 2. Device Health Ring + Recent Alerts ───────────────────────────── -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <!-- Device Health Ring -->
      <UCard data-testid="device-health-ring">
        <template #header>
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">Device Health</h3>
        </template>

        <div v-if="metricsLoading" class="flex items-center justify-center py-10">
          <USkeleton width="160px" height="160px" rounded="full" />
        </div>
        <div v-else class="flex flex-col items-center gap-4 py-4">
          <!-- SVG Donut -->
          <svg width="160" height="160" viewBox="0 0 160 160" aria-label="Device health donut chart">
            <!-- Background ring -->
            <circle cx="80" cy="80" r="60" fill="none" stroke="var(--bg-raised)" stroke-width="16" />
            <!-- Segments -->
            <circle
              v-for="seg in donutSegments"
              :key="seg.label"
              cx="80" cy="80" r="60"
              fill="none"
              :style="{ stroke: seg.color }"
              stroke-width="16"
              :stroke-dasharray="`${seg.dash} ${seg.gap}`"
              stroke-linecap="butt"
              :transform="`rotate(${seg.startAngle} 80 80)`"
            />
            <!-- Center: total count -->
            <text
              x="80" y="75"
              text-anchor="middle"
              font-family="JetBrains Mono, ui-monospace, monospace"
              font-size="26"
              font-weight="700"
              fill="var(--text-primary)"
            >{{ metrics?.devices.total ?? "—" }}</text>
            <text
              x="80" y="93"
              text-anchor="middle"
              font-family="Inter, ui-sans-serif, sans-serif"
              font-size="11"
              fill="var(--text-muted)"
            >devices</text>
          </svg>

          <!-- Legend -->
          <div class="flex gap-5 flex-wrap justify-center">
            <div class="flex items-center gap-1.5">
              <span class="h-2.5 w-2.5 rounded-full bg-[var(--status-ok)] shrink-0" />
              <span class="text-xs text-[var(--text-secondary)]">Online</span>
              <span class="text-xs font-mono font-semibold text-[var(--text-primary)]">
                {{ metrics?.devices.online ?? 0 }}
              </span>
            </div>
            <div class="flex items-center gap-1.5">
              <span class="h-2.5 w-2.5 rounded-full bg-[var(--status-warn)] shrink-0" />
              <span class="text-xs text-[var(--text-secondary)]">Stale</span>
              <span class="text-xs font-mono font-semibold text-[var(--text-primary)]">
                {{ metrics?.devices.stale ?? 0 }}
              </span>
            </div>
            <div class="flex items-center gap-1.5">
              <span class="h-2.5 w-2.5 rounded-full bg-[var(--status-bad)] shrink-0" />
              <span class="text-xs text-[var(--text-secondary)]">Offline</span>
              <span class="text-xs font-mono font-semibold text-[var(--text-primary)]">
                {{ metrics?.devices.offline ?? 0 }}
              </span>
            </div>
          </div>
        </div>
      </UCard>

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
    <div class="flex flex-wrap gap-3">
      <UButton @click="router.push('/pairing')">
        <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        Pair Device
      </UButton>
      <UButton variant="secondary" @click="router.push('/alerts')">
        <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
        </svg>
        Create Alert Rule
      </UButton>
      <UButton variant="secondary" @click="router.push('/devices')">
        <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z" />
        </svg>
        View All Devices
      </UButton>
    </div>

    <!-- ── 4. Event Stream ─────────────────────────────────────────────────── -->
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
          class="flex items-center gap-3 py-2 px-1 text-xs"
        >
          <span class="font-mono text-[var(--text-muted)] shrink-0 w-28 truncate">
            {{ new Date(event.created_at).toLocaleTimeString() }}
          </span>
          <UBadge :status="eventBadgeStatus(event.event_type)" class="shrink-0 max-w-[10rem] truncate">
            {{ event.event_type }}
          </UBadge>
          <span class="text-[var(--text-secondary)] shrink-0 truncate max-w-[6rem]">{{ event.stream }}</span>
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
