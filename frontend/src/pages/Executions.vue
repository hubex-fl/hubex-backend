<script setup lang="ts">
import { computed, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useCapabilities, hasCap } from "../lib/capabilities";
import { fetchJson, ApiError } from "../lib/request";
import { useAbortHandle } from "../lib/abort";

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
  if (caps.status === "loading") return "Capabilities loading.";
  if (caps.status === "error") return `Capabilities error: ${caps.error ?? "unknown"}`;
  return "Capabilities unavailable";
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
    error.value = "Missing capability: tasks.read";
    return;
  }
  const id = Number(deviceIdInput.value.trim());
  if (!Number.isFinite(id) || id <= 0) {
    error.value = "Device ID required";
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
      <h2>Executions / Tasks (read-only)</h2>
      <div class="row">
        <button class="btn secondary" @click="retry">Refresh</button>
        <button class="btn secondary" @click="openTraceHub">Open in Trace Hub</button>
      </div>
    </div>

    <p v-if="caps.status === 'unavailable'" class="muted">Capabilities unavailable</p>
    <p v-else-if="caps.status === 'loading'" class="muted">Loading capabilities.</p>
    <p v-else-if="caps.status === 'error'" class="error">Capabilities error: {{ caps.error }}</p>
    <div v-else-if="!canReadTasks" class="muted">Missing capability: tasks.read</div>
    <div v-else class="card">
      <div class="form-row">
        <div>
          <label class="muted">Device ID</label>
          <input v-model="deviceIdInput" class="input" placeholder="e.g. 123" />
        </div>
        <div>
          <label class="muted">Status (optional)</label>
          <input v-model="statusFilter" class="input" placeholder="queued/in_flight/done" />
        </div>
        <div>
          <label class="muted">Context ID (optional)</label>
          <input v-model="contextFilter" class="input" placeholder="e.g. 1" />
        </div>
        <button class="btn" @click="refresh" :disabled="loading">Load</button>
      </div>

      <div v-if="error" class="error">{{ error }}</div>
      <div v-else-if="loading" class="muted">Loading.</div>
      <div v-else-if="tasks.length === 0" class="muted">No tasks.</div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Type</th>
            <th>Status</th>
            <th>Created</th>
            <th>Completed</th>
            <th>Context</th>
            <th>Device</th>
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

      <div v-if="!selected" class="muted">Select a task to view details.</div>
      <div v-else class="card">
        <div class="muted">Selected task: {{ selected.id }}</div>
        <pre class="muted">{{ selected }}</pre>
      </div>
    </div>
  </div>
</template>
