<script setup lang="ts">
import { computed, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useCapabilities, hasCap } from "../lib/capabilities";
import { fetchJson, ApiError } from "../lib/request";
import { useAbortHandle } from "../lib/abort";
import UInfoTooltip from "../components/ui/UInfoTooltip.vue";

type TaskItem = {
  id: number;
  type: string;
  status: string;
  priority: number;
  created_at: string;
  completed_at: string | null;
  execution_context_id: number | null;
  idempotency_key: string | null;
};

type TaskItemWithClient = TaskItem & { client_id: number };

const caps = useCapabilities();
const router = useRouter();
const { t, tm, rt } = useI18n();
const { signal } = useAbortHandle();

const deviceIdInput = ref("");
const statusFilter = ref("");
const contextFilter = ref("");

const tasks = ref<TaskItemWithClient[]>([]);
const selected = ref<TaskItemWithClient | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);

const capsReady = computed(() => caps.status === "ready");
const canReadTasks = computed(() => hasCap("tasks.read"));

let inflight = false;

function mapError(err: unknown): string {
  const e = err as ApiError;
  if (e?.status) return `HTTP ${e.status}: ${e.message}`;
  return (e && "message" in e) ? String(e.message) : "request_failed";
}

function capsStatusMessage(): string {
  if (caps.status === "loading") return t('pages.executions.capsLoading');
  if (caps.status === "error") return t('pages.executions.capsError', { error: caps.error ?? 'unknown' });
  return t('pages.executions.capsUnavailable');
}

function buildUrl(deviceId: number): string {
  const params = new URLSearchParams();
  params.set("limit", "200");
  if (statusFilter.value.trim()) {
    params.set("status", statusFilter.value.trim());
  }
  return `/api/v1/devices/${deviceId}/tasks?${params.toString()}`;
}

async function refresh() {
  if (inflight) return;
  if (!capsReady.value) {
    error.value = capsStatusMessage();
    return;
  }
  if (!canReadTasks.value) {
    error.value = t('pages.executions.missingCap');
    return;
  }
  const id = Number(deviceIdInput.value.trim());
  if (!Number.isFinite(id) || id <= 0) {
    error.value = t('pages.executions.deviceIdRequired');
    return;
  }
  inflight = true;
  loading.value = true;
  try {
    const res = await fetchJson<TaskItem[]>(buildUrl(id), { method: "GET" }, signal);
    const mapped = res.map((item) => ({ ...item, client_id: id }));
    const filtered = contextFilter.value.trim()
      ? mapped.filter((item) => String(item.execution_context_id ?? "") === contextFilter.value.trim())
      : mapped;
    tasks.value = filtered;
    selected.value = null;
    error.value = null;
  } catch (err) {
    error.value = mapError(err);
  } finally {
    inflight = false;
    loading.value = false;
  }
}

function retry() {
  error.value = null;
  refresh().catch(() => undefined);
}

function openTraceHub() {
  router.push({ path: "/trace-hub" });
}

onUnmounted(() => {
  // useAbortHandle will abort inflight fetches automatically
});
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div class="flex items-center gap-1">
        <h2>{{ t('nav.executions') }}</h2>
        <UInfoTooltip :title="t('infoTooltips.executions.title')" :items="tm('infoTooltips.executions.items').map((i: any) => rt(i))" tourId="executions-overview" />
      </div>
      <div class="row">
        <button class="btn secondary" @click="retry">{{ t('common.refresh') }}</button>
        <button class="btn secondary" @click="openTraceHub">{{ t('pages.executions.openInTraceHub') }}</button>
      </div>
    </div>

    <p v-if="caps.status === 'unavailable'" class="muted">{{ t('pages.executions.capsUnavailable') }}</p>
    <p v-else-if="caps.status === 'loading'" class="muted">{{ t('pages.executions.capsLoading') }}</p>
    <p v-else-if="caps.status === 'error'" class="error">{{ t('pages.executions.capsError', { error: caps.error ?? '' }) }}</p>
    <div v-else-if="!canReadTasks" class="muted">{{ t('pages.executions.missingCap') }}</div>
    <div v-else class="card">
      <div class="form-row">
        <div>
          <label class="muted">{{ t('pages.executions.deviceIdLabel') }}</label>
          <input v-model="deviceIdInput" class="input" :placeholder="t('pages.executions.deviceIdPlaceholder')" />
        </div>
        <div>
          <label class="muted">{{ t('pages.executions.statusLabel') }}</label>
          <input v-model="statusFilter" class="input" :placeholder="t('pages.executions.statusPlaceholder')" />
        </div>
        <div>
          <label class="muted">{{ t('pages.executions.contextLabel') }}</label>
          <input v-model="contextFilter" class="input" :placeholder="t('pages.executions.contextPlaceholder')" />
        </div>
        <button class="btn" @click="refresh" :disabled="loading">{{ t('pages.executions.load') }}</button>
      </div>

      <div v-if="error" class="error">{{ error }}</div>
      <div v-else-if="loading" class="muted">{{ t('pages.executions.loading') }}</div>
      <div v-else-if="tasks.length === 0" class="muted">{{ t('pages.executions.noTasks') }}</div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>{{ t('pages.executions.colId') }}</th>
            <th>{{ t('pages.executions.colType') }}</th>
            <th>{{ t('pages.executions.colStatus') }}</th>
            <th>{{ t('pages.executions.colCreated') }}</th>
            <th>{{ t('pages.executions.colCompleted') }}</th>
            <th>{{ t('pages.executions.colContext') }}</th>
            <th>{{ t('pages.executions.colDevice') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in tasks" :key="task.id" @click="selected = task">
            <td>{{ task.id }}</td>
            <td>{{ task.type }}</td>
            <td>{{ task.status }}</td>
            <td>{{ task.created_at }}</td>
            <td>{{ task.completed_at ?? "-" }}</td>
            <td>{{ task.execution_context_id ?? "-" }}</td>
            <td>{{ task.client_id }}</td>
          </tr>
        </tbody>
      </table>

      <div class="section-divider"></div>

      <div v-if="!selected" class="muted">{{ t('pages.executions.selectToView') }}</div>
      <div v-else class="card">
        <div class="muted">{{ t('pages.executions.selectedTask', { id: selected.id }) }}</div>
        <pre class="muted">{{ selected }}</pre>
      </div>
    </div>
  </div>
</template>
