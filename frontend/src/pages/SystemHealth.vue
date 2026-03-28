<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { apiFetch } from "../lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface HealthResponse {
  status: string;
  version?: string;
  checks?: Record<string, string>;
}

interface DeviceMetrics {
  total: number;
  online: number;
  stale: number;
  offline: number;
}

interface AlertMetrics {
  firing: number;
  acknowledged: number;
}

interface MetricsResponse {
  devices: DeviceMetrics;
  entities_total: number;
  effects_total: number;
  alerts: AlertMetrics;
  events_24h: number;
  webhooks_active: number;
  uptime_seconds: number;
}

// ── State ─────────────────────────────────────────────────────────────────────

const health = ref<HealthResponse | null>(null);
const readiness = ref<HealthResponse | null>(null);
const metrics = ref<MetricsResponse | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
const lastChecked = ref<Date | null>(null);
const refreshing = ref(false);

let timer: ReturnType<typeof setInterval> | null = null;

// ── Computed ─────────────────────────────────────────────────────────────────

const overallStatus = computed<"healthy" | "degraded" | "error">(() => {
  if (!health.value || !readiness.value) return "error";
  if (health.value.status !== "ok") return "error";
  if (readiness.value.status !== "ok") return "degraded";
  return "healthy";
});

const overallLabel = computed(() => {
  switch (overallStatus.value) {
    case "healthy": return "All Systems Operational";
    case "degraded": return "Degraded — Some Issues Detected";
    case "error": return "System Error";
  }
});

const dbStatus = computed(() => readiness.value?.checks?.db ?? "unknown");
const redisStatus = computed(() => readiness.value?.checks?.redis ?? "unknown");

const uptimeFormatted = computed(() => {
  if (!metrics.value) return "–";
  const s = metrics.value.uptime_seconds;
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = Math.floor(s % 60);
  if (h > 0) return `${h}h ${m}m ${sec}s`;
  if (m > 0) return `${m}m ${sec}s`;
  return `${sec}s`;
});

const lastCheckedLabel = computed(() => {
  if (!lastChecked.value) return "–";
  return lastChecked.value.toLocaleTimeString();
});

// ── Data fetching ─────────────────────────────────────────────────────────────

async function fetchAll() {
  refreshing.value = true;
  error.value = null;
  try {
    const [h, r, m] = await Promise.allSettled([
      fetch("/health").then((res) => res.json() as Promise<HealthResponse>),
      fetch("/ready").then((res) => res.json() as Promise<HealthResponse>),
      apiFetch<MetricsResponse>("/api/v1/metrics"),
    ]);

    health.value = h.status === "fulfilled" ? h.value : null;
    readiness.value = r.status === "fulfilled" ? r.value : null;
    metrics.value = m.status === "fulfilled" ? m.value : null;

    if (h.status === "rejected" && r.status === "rejected") {
      error.value = "Unable to reach backend server";
    }
    lastChecked.value = new Date();
  } catch (err) {
    error.value = String(err);
  } finally {
    loading.value = false;
    refreshing.value = false;
  }
}

onMounted(async () => {
  await fetchAll();
  timer = setInterval(fetchAll, 30_000);
});

onUnmounted(() => {
  if (timer !== null) clearInterval(timer);
});

// ── Status helpers ────────────────────────────────────────────────────────────

function statusColor(status: string): string {
  if (status === "ok" || status === "healthy") return "text-green-400";
  if (status === "degraded" || status === "disabled") return "text-yellow-400";
  return "text-red-400";
}

function statusDot(status: string): string {
  if (status === "ok" || status === "healthy") return "bg-green-400";
  if (status === "degraded" || status === "disabled") return "bg-yellow-400";
  return "bg-red-400";
}

function deviceHealthPercent(): number {
  if (!metrics.value) return 0;
  const { total, online } = metrics.value.devices;
  if (total === 0) return 100;
  return Math.round((online / total) * 100);
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <svg class="h-5 w-5 text-[var(--accent-cyan)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />
        </svg>
        <h2 class="text-base font-semibold text-[var(--text-primary)]">System Health</h2>
        <span v-if="refreshing" class="text-xs text-[var(--text-muted)] animate-pulse">refreshing…</span>
      </div>

      <div class="flex items-center gap-3">
        <span class="text-xs text-[var(--text-muted)]">
          Last checked: <span class="text-[var(--text-primary)]">{{ lastCheckedLabel }}</span>
        </span>
        <button
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--border)] text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:border-[var(--border-hover)] bg-[var(--bg-raised)] transition-colors"
          :disabled="refreshing"
          @click="fetchAll"
        >
          <svg class="h-3.5 w-3.5" :class="refreshing ? 'animate-spin' : ''" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
          </svg>
          Refresh
        </button>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-4">
      <div class="h-20 rounded-xl bg-[var(--bg-surface)] animate-pulse" />
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div v-for="i in 4" :key="i" class="h-24 rounded-xl bg-[var(--bg-surface)] animate-pulse" />
      </div>
    </div>

    <template v-else>
      <!-- Overall Status Banner -->
      <div
        :class="[
          'rounded-xl border px-6 py-4 flex items-center gap-4',
          overallStatus === 'healthy'
            ? 'border-green-500/30 bg-green-500/5'
            : overallStatus === 'degraded'
            ? 'border-yellow-500/30 bg-yellow-500/5'
            : 'border-red-500/30 bg-red-500/5',
        ]"
      >
        <!-- Animated status dot -->
        <div class="relative shrink-0">
          <div :class="['h-4 w-4 rounded-full', overallStatus === 'healthy' ? 'bg-green-400' : overallStatus === 'degraded' ? 'bg-yellow-400' : 'bg-red-400']" />
          <div
            v-if="overallStatus === 'healthy'"
            class="absolute inset-0 h-4 w-4 rounded-full bg-green-400 animate-ping opacity-60"
          />
        </div>
        <div>
          <p :class="['text-sm font-semibold', overallStatus === 'healthy' ? 'text-green-400' : overallStatus === 'degraded' ? 'text-yellow-400' : 'text-red-400']">
            {{ overallLabel }}
          </p>
          <p class="text-xs text-[var(--text-muted)] mt-0.5">
            Auto-refreshes every 30 seconds
          </p>
        </div>
        <div class="ml-auto text-right">
          <p class="text-xs text-[var(--text-muted)]">Version</p>
          <p class="text-sm font-mono text-[var(--text-primary)]">{{ health?.version ?? "–" }}</p>
        </div>
      </div>

      <!-- Error banner -->
      <div
        v-if="error"
        class="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400"
      >
        {{ error }}
      </div>

      <!-- Component Status Row -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <!-- Backend -->
        <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wide">Backend API</span>
            <div :class="['h-2 w-2 rounded-full', health ? statusDot(health.status) : 'bg-red-400']" />
          </div>
          <p :class="['text-sm font-semibold', health ? statusColor(health.status) : 'text-red-400']">
            {{ health?.status ?? "unreachable" }}
          </p>
          <p class="text-xs text-[var(--text-muted)] mt-1">Liveness probe</p>
        </div>

        <!-- Database -->
        <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wide">Database</span>
            <div :class="['h-2 w-2 rounded-full', statusDot(dbStatus)]" />
          </div>
          <p :class="['text-sm font-semibold', statusColor(dbStatus)]">{{ dbStatus }}</p>
          <p class="text-xs text-[var(--text-muted)] mt-1">PostgreSQL connectivity</p>
        </div>

        <!-- Redis -->
        <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wide">Redis</span>
            <div :class="['h-2 w-2 rounded-full', redisStatus === 'disabled' ? 'bg-[var(--text-muted)]' : statusDot(redisStatus)]" />
          </div>
          <p :class="['text-sm font-semibold', redisStatus === 'disabled' ? 'text-[var(--text-muted)]' : statusColor(redisStatus)]">
            {{ redisStatus }}
          </p>
          <p class="text-xs text-[var(--text-muted)] mt-1">Cache / Pub-Sub</p>
        </div>
      </div>

      <!-- Metrics Grid -->
      <div v-if="metrics" class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <!-- Devices Online -->
        <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-4">
          <p class="text-xs text-[var(--text-muted)] uppercase tracking-wide mb-1">Devices Online</p>
          <p class="text-2xl font-bold text-[var(--text-primary)]">{{ metrics.devices.online }}</p>
          <p class="text-xs text-[var(--text-muted)] mt-1">of {{ metrics.devices.total }} total</p>
          <div class="mt-2 h-1 rounded-full bg-[var(--bg-raised)] overflow-hidden">
            <div
              class="h-full rounded-full bg-green-400 transition-all"
              :style="{ width: deviceHealthPercent() + '%' }"
            />
          </div>
          <p class="text-xs text-[var(--text-muted)] mt-1">{{ deviceHealthPercent() }}% healthy</p>
        </div>

        <!-- Stale / Offline -->
        <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-4">
          <p class="text-xs text-[var(--text-muted)] uppercase tracking-wide mb-1">Stale / Offline</p>
          <p class="text-2xl font-bold" :class="metrics.devices.offline > 0 ? 'text-red-400' : 'text-[var(--text-primary)]'">
            {{ metrics.devices.offline }}
          </p>
          <p class="text-xs text-[var(--text-muted)] mt-1">offline</p>
          <p class="text-xs text-yellow-400 mt-1">{{ metrics.devices.stale }} stale</p>
        </div>

        <!-- Active Alerts -->
        <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-4">
          <p class="text-xs text-[var(--text-muted)] uppercase tracking-wide mb-1">Active Alerts</p>
          <p class="text-2xl font-bold" :class="metrics.alerts.firing > 0 ? 'text-red-400 animate-pulse' : 'text-[var(--text-primary)]'">
            {{ metrics.alerts.firing }}
          </p>
          <p class="text-xs text-[var(--text-muted)] mt-1">firing</p>
          <p class="text-xs text-yellow-400 mt-1">{{ metrics.alerts.acknowledged }} acknowledged</p>
        </div>

        <!-- Events 24h -->
        <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-4">
          <p class="text-xs text-[var(--text-muted)] uppercase tracking-wide mb-1">Events (24h)</p>
          <p class="text-2xl font-bold text-[var(--text-primary)]">{{ metrics.events_24h.toLocaleString() }}</p>
          <p class="text-xs text-[var(--text-muted)] mt-1">system events</p>
        </div>
      </div>

      <!-- Second Row Metrics -->
      <div v-if="metrics" class="grid grid-cols-2 md:grid-cols-3 gap-3">
        <!-- Uptime -->
        <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-4">
          <p class="text-xs text-[var(--text-muted)] uppercase tracking-wide mb-1">Uptime</p>
          <p class="text-xl font-bold font-mono text-green-400">{{ uptimeFormatted }}</p>
          <p class="text-xs text-[var(--text-muted)] mt-1">since last restart</p>
        </div>

        <!-- Entities -->
        <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-4">
          <p class="text-xs text-[var(--text-muted)] uppercase tracking-wide mb-1">Entities</p>
          <p class="text-2xl font-bold text-[var(--text-primary)]">{{ metrics.entities_total }}</p>
          <p class="text-xs text-[var(--text-muted)] mt-1">registered entities</p>
        </div>

        <!-- Webhooks -->
        <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-4">
          <p class="text-xs text-[var(--text-muted)] uppercase tracking-wide mb-1">Active Webhooks</p>
          <p class="text-2xl font-bold text-[var(--text-primary)]">{{ metrics.webhooks_active }}</p>
          <p class="text-xs text-[var(--text-muted)] mt-1">subscriptions</p>
        </div>
      </div>
    </template>
  </div>
</template>
