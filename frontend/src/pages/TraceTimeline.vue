<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../lib/api";
import UCard from "../components/ui/UCard.vue";
import UBadge from "../components/ui/UBadge.vue";
import UInfoTooltip from "../components/ui/UInfoTooltip.vue";

type TraceEntry = {
  timestamp: string;
  source: string;
  type: string;
  summary: string;
  trace_id: string | null;
  device_uid: string | null;
};

type IncidentSummary = {
  active_alerts: number;
  automations_fired_24h: number;
  devices_offline: number;
  error_events_1h: number;
};

type AnomalyHint = {
  variable_key: string;
  device_id: number | null;
  current_value: number | null;
  mean: number;
  stddev: number;
  z_score: number;
  hint: string;
};

const { t, tm, rt } = useI18n();
const traces = ref<TraceEntry[]>([]);
const incidents = ref<IncidentSummary | null>(null);
const anomalies = ref<AnomalyHint[]>([]);
const loading = ref(true);
const minutes = ref(60);

const SOURCE_COLORS: Record<string, string> = {
  event: "var(--primary)",
  audit: "var(--accent)",
  alert: "var(--status-bad)",
  automation: "var(--status-info)",
};

async function loadAll() {
  loading.value = true;
  try {
    const [t, i, a] = await Promise.allSettled([
      apiFetch<TraceEntry[]>(`/api/v1/observability/traces?minutes=${minutes.value}&limit=100`),
      apiFetch<IncidentSummary>("/api/v1/observability/incidents"),
      apiFetch<AnomalyHint[]>("/api/v1/observability/anomalies?hours=24&threshold=2.5"),
    ]);
    traces.value = t.status === "fulfilled" ? t.value : [];
    incidents.value = i.status === "fulfilled" ? i.value : null;
    anomalies.value = a.status === "fulfilled" ? a.value : [];
  } finally {
    loading.value = false;
  }
}

const selectedTrace = ref<TraceEntry | null>(null);

function relativeTime(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 10) return t("dashboardsList.relative.justNow");
  if (s < 60) return t("dashboardsList.relative.secondsAgo", { n: s });
  const m = Math.floor(s / 60);
  if (m < 60) return t("dashboardsList.relative.minutesAgo", { n: m });
  return t("dashboardsList.relative.hoursAgo", { n: Math.floor(m / 60) });
}

onMounted(loadAll);
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <div class="flex items-center gap-1.5">
          <h1 class="text-xl font-semibold text-[var(--text-primary)]">{{ t('pages.traceTimeline.title') }}</h1>
          <UInfoTooltip :title="t('infoTooltips.traceTimeline.title')" :items="tm('infoTooltips.traceTimeline.items').map((i: any) => rt(i))" tourId="trace-timeline-overview" />
        </div>
        <p class="text-xs text-[var(--text-muted)] mt-0.5">{{ t('pages.traceTimeline.subtitle') }}</p>
      </div>
      <div class="flex items-center gap-2">
        <select v-model.number="minutes" class="px-2 py-1 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)]" @change="loadAll">
          <option :value="15">{{ t('traceTimeline.timeRange15Min') }}</option>
          <option :value="60">{{ t('traceTimeline.timeRange1Hour') }}</option>
          <option :value="360">{{ t('traceTimeline.timeRange6Hours') }}</option>
          <option :value="1440">{{ t('traceTimeline.timeRange24Hours') }}</option>
        </select>
        <a href="/api/v1/observability/support-bundle" download class="px-2.5 py-1 rounded-lg text-xs font-medium border border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text-primary)]">
          {{ t('traceTimeline.supportBundle') }}
        </a>
      </div>
    </div>

    <!-- Incident Summary Cards -->
    <div v-if="incidents" class="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <UCard padding="sm">
        <div class="text-center">
          <p class="text-xl font-bold" :class="incidents.active_alerts > 0 ? 'text-[var(--status-bad)]' : 'text-[var(--status-ok)]'">{{ incidents.active_alerts }}</p>
          <p class="text-[10px] text-[var(--text-muted)]">{{ t('traceTimeline.activeAlerts') }}</p>
        </div>
      </UCard>
      <UCard padding="sm">
        <div class="text-center">
          <p class="text-xl font-bold text-[var(--status-info)]">{{ incidents.automations_fired_24h }}</p>
          <p class="text-[10px] text-[var(--text-muted)]">{{ t('traceTimeline.automations24h') }}</p>
        </div>
      </UCard>
      <UCard padding="sm">
        <div class="text-center">
          <p class="text-xl font-bold" :class="incidents.devices_offline > 0 ? 'text-[var(--status-warn)]' : 'text-[var(--status-ok)]'">{{ incidents.devices_offline }}</p>
          <p class="text-[10px] text-[var(--text-muted)]">{{ t('traceTimeline.devicesOffline') }}</p>
        </div>
      </UCard>
      <UCard padding="sm">
        <div class="text-center">
          <p class="text-xl font-bold" :class="incidents.error_events_1h > 0 ? 'text-[var(--status-bad)]' : 'text-[var(--status-ok)]'">{{ incidents.error_events_1h }}</p>
          <p class="text-[10px] text-[var(--text-muted)]">{{ t('traceTimeline.errors1h') }}</p>
        </div>
      </UCard>
    </div>

    <!-- Anomaly Detection -->
    <UCard v-if="anomalies.length">
      <template #header>
        <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('traceTimeline.anomalyDetection') }}</h3>
        <span class="text-xs text-[var(--text-muted)]">{{ t('traceTimeline.anomalySubtitle') }}</span>
      </template>
      <div class="space-y-2">
        <div v-for="a in anomalies" :key="a.variable_key + '-' + a.device_id" class="flex items-center gap-3 px-3 py-2 rounded-lg bg-[var(--status-warn)]/5 border border-[var(--status-warn)]/20">
          <span class="text-xs font-medium text-[var(--status-warn)]">{{ a.z_score > 3 ? t('traceTimeline.veryUnusual') : t('traceTimeline.unusual') }}</span>
          <span class="text-xs text-[var(--text-primary)]">{{ a.variable_key }}</span>
          <span class="text-[10px] text-[var(--text-muted)]">{{ a.current_value?.toFixed(1) }} ({{ t('traceTimeline.normalRange') }}: {{ a.mean }} ± {{ a.stddev }})</span>
        </div>
      </div>
    </UCard>

    <!-- Trace Timeline -->
    <UCard>
      <template #header>
        <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('traceTimeline.eventTimeline') }}</h3>
        <span class="text-xs text-[var(--text-muted)]">{{ t('traceTimeline.entries', { count: traces.length }, traces.length) }}</span>
      </template>

      <div v-if="loading" class="text-xs text-[var(--text-muted)] py-4 text-center">{{ t('traceTimeline.loadingTraces') }}</div>
      <div v-else-if="!traces.length" class="text-xs text-[var(--text-muted)] py-4 text-center">{{ t('traceTimeline.noTraces') }}</div>
      <div v-else class="space-y-1 max-h-[50vh] overflow-y-auto">
        <div v-for="(t, i) in traces" :key="i" class="flex items-start gap-3 px-3 py-2 rounded-lg hover:bg-[var(--bg-raised)] transition-colors cursor-pointer" @click="selectedTrace = t">
          <!-- Timeline dot -->
          <div class="mt-1.5 shrink-0">
            <div class="h-2 w-2 rounded-full" :style="{ background: SOURCE_COLORS[t.source] || 'var(--text-muted)' }" />
          </div>
          <!-- Content -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="text-[10px] px-1.5 py-0.5 rounded font-medium" :style="{ background: (SOURCE_COLORS[t.source] || 'var(--text-muted)') + '20', color: SOURCE_COLORS[t.source] || 'var(--text-muted)' }">{{ t.source }}</span>
              <span class="text-xs text-[var(--text-primary)] truncate">{{ t.type }}</span>
              <span v-if="t.device_uid" class="text-[10px] font-mono text-[var(--text-muted)]">{{ t.device_uid }}</span>
            </div>
            <p class="text-[10px] text-[var(--text-muted)] mt-0.5 truncate">{{ t.summary }}</p>
          </div>
          <!-- Time -->
          <span class="text-[10px] text-[var(--text-muted)] shrink-0">{{ relativeTime(t.timestamp) }}</span>
        </div>
      </div>
    </UCard>

    <!-- Trace Detail Panel -->
    <UCard v-if="selectedTrace">
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('traceTimeline.traceDetail') }}</h3>
          <button class="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]" @click="selectedTrace = null">{{ t('common.close') }}</button>
        </div>
      </template>
      <div class="space-y-2 text-xs">
        <div class="grid grid-cols-2 gap-2">
          <div><span class="text-[var(--text-muted)]">{{ t('traceTimeline.fieldSource') }}:</span> <span class="font-medium" :style="{ color: SOURCE_COLORS[selectedTrace.source] }">{{ selectedTrace.source }}</span></div>
          <div><span class="text-[var(--text-muted)]">{{ t('traceTimeline.fieldType') }}:</span> <span class="font-medium">{{ selectedTrace.type }}</span></div>
          <div><span class="text-[var(--text-muted)]">{{ t('traceTimeline.fieldTime') }}:</span> <span>{{ new Date(selectedTrace.timestamp).toLocaleString() }}</span></div>
          <div v-if="selectedTrace.trace_id"><span class="text-[var(--text-muted)]">{{ t('traceTimeline.fieldTraceId') }}:</span> <span class="font-mono text-[10px]">{{ selectedTrace.trace_id }}</span></div>
        </div>
        <div v-if="selectedTrace.device_uid" class="flex items-center gap-2">
          <span class="text-[var(--text-muted)]">{{ t('traceTimeline.fieldDevice') }}:</span>
          <router-link :to="`/devices`" class="text-[var(--primary)] hover:underline font-mono">{{ selectedTrace.device_uid }}</router-link>
        </div>
        <div class="rounded-lg bg-[var(--bg-raised)] p-2 text-[10px] font-mono text-[var(--text-secondary)] break-all">{{ selectedTrace.summary }}</div>
      </div>
    </UCard>
  </div>
</template>
