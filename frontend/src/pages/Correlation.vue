<script setup lang="ts">
import { computed, onUnmounted, ref } from "vue";
import { useCapabilities, hasCap } from "../lib/capabilities";
import { fetchJson, ApiError } from "../lib/request";
import { useAbortHandle } from "../lib/abort";
import { useRouter } from "vue-router";

type TaskItem = {
  id: number;
  status: string;
  type?: string | null;
  created_at?: string | null;
  completed_at?: string | null;
  execution_context_id?: number | null;
  context_key?: string | null;
  client_id?: number | null;
  device_id?: number | null;
};

type EffectItem = {
  id: number;
  effect_id: string;
  kind: string;
  status: string;
  created_at: string;
  payload_json: Record<string, unknown>;
  error_json: Record<string, unknown> | null;
};

const caps = useCapabilities();
const router = useRouter();
const { signal: tasksSignal, abort: abortTasks } = useAbortHandle();
const { signal: effectSignal, abort: abortEffect } = useAbortHandle();

const contextKey = ref("");
const deviceIdInput = ref("");
const tasks = ref<TaskItem[]>([]);
const tasksError = ref<string | null>(null);
const tasksLoading = ref(false);

const effectIdInput = ref("");
const effectDetail = ref<EffectItem | null>(null);
const effectError = ref<string | null>(null);
const effectLoading = ref(false);

const entityIdInput = ref("");
const deviceIdLookup = ref("");

const capsReady = computed(() => caps.status === "ready");
const canReadTasks = computed(() => hasCap("tasks.read"));
const canReadEffects = computed(() => hasCap("effects.read"));
const canReadDevices = computed(() => hasCap("devices.read"));
const canReadEntities = computed(() => hasCap("entities.read"));

function mapError(err: unknown): string {
  const e = err as ApiError;
  if (e?.status) {
    return `HTTP ${e.status}: ${e.message}`;
  }
  return (e && "message" in e) ? String(e.message) : "request_failed";
}

function capsStatusMessage(): string {
  if (caps.status === "loading") return "Capabilities loading.";
  if (caps.status === "error") return `Capabilities error: ${caps.error ?? "unknown"}`;
  return "Capabilities unavailable";
}

async function lookupTasks() {
  if (!capsReady.value) {
    tasksError.value = capsStatusMessage();
    return;
  }
  if (!canReadTasks.value) {
    tasksError.value = "Missing capability: tasks.read";
    return;
  }
  const key = contextKey.value.trim();
  const deviceId = deviceIdInput.value.trim();
  if (!deviceId) {
    tasksError.value = "Device id required.";
    return;
  }
  tasksLoading.value = true;
  tasksError.value = null;
  try {
    const id = deviceId ? encodeURIComponent(deviceId) : "";
    const url = `/api/v1/devices/${id}/tasks?limit=200`;
    const res = await fetchJson<TaskItem[]>(url, { method: "GET" }, tasksSignal);
    const filtered = res.filter((item) => {
      if (key) {
        const ctx = String(item.context_key ?? "");
        const exec = String(item.execution_context_id ?? "");
        return ctx === key || exec === key;
      }
      return true;
    });
    tasks.value = filtered;
  } catch (err) {
    tasksError.value = mapError(err);
  } finally {
    tasksLoading.value = false;
  }
}

async function retryTasks() {
  tasksError.value = null;
  await lookupTasks();
}

async function lookupEffect() {
  if (!capsReady.value) {
    effectError.value = capsStatusMessage();
    return;
  }
  if (!canReadEffects.value) {
    effectError.value = "Missing capability: effects.read";
    return;
  }
  const id = effectIdInput.value.trim();
  if (!id) {
    effectError.value = "Effect id required.";
    return;
  }
  effectLoading.value = true;
  effectError.value = null;
  try {
    const res = await fetchJson<EffectItem>(`/api/v1/effects/${encodeURIComponent(id)}`, { method: "GET" }, effectSignal);
    effectDetail.value = res;
  } catch (err) {
    effectError.value = mapError(err);
  } finally {
    effectLoading.value = false;
  }
}

async function retryEffect() {
  effectError.value = null;
  await lookupEffect();
}

function openTasksView() {
  router.push("/executions");
}

function openEffectsView() {
  router.push("/effects");
}

function openSystemStage() {
  router.push("/system-stage");
}

onUnmounted(() => {
  abortTasks();
  abortEffect();
});
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>Trace Correlation (read-only)</h2>
    </div>

    <div v-if="caps.status !== 'ready'" class="muted">{{ capsStatusMessage() }}</div>

    <div v-else class="card">
      <h3>Lookup by Execution context_key</h3>
      <div v-if="!canReadTasks" class="muted">Missing capability: tasks.read</div>
      <div v-else>
        <div class="form-row">
          <input v-model="contextKey" class="input" placeholder="context_key" />
          <input v-model="deviceIdInput" class="input" placeholder="device id" />
          <button class="btn" @click="lookupTasks">Search</button>
          <button class="btn secondary" @click="retryTasks">Retry</button>
          <button class="btn secondary" @click="openTasksView">Open Tasks</button>
        </div>
        <div v-if="tasksError" class="error">{{ tasksError }}</div>
        <div v-else-if="tasksLoading" class="muted">Loading.</div>
        <div v-else-if="tasks.length === 0" class="muted">No matching tasks.</div>
        <table v-else class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Type</th>
              <th>Status</th>
              <th>Context</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in tasks" :key="t.id">
              <td>{{ t.id }}</td>
              <td>{{ t.type || "-" }}</td>
              <td>{{ t.status }}</td>
              <td>{{ t.context_key || t.execution_context_id || "-" }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="section-divider"></div>

      <h3>Lookup by Effect ID</h3>
      <div v-if="!canReadEffects" class="muted">Missing capability: effects.read</div>
      <div v-else>
        <div class="form-row">
          <input v-model="effectIdInput" class="input" placeholder="effect_id" />
          <button class="btn" @click="lookupEffect">Lookup</button>
          <button class="btn secondary" @click="retryEffect">Retry</button>
          <button class="btn secondary" @click="openEffectsView">Open Effects</button>
        </div>
        <div v-if="effectError" class="error">{{ effectError }}</div>
        <div v-else-if="effectLoading" class="muted">Loading.</div>
        <div v-else-if="effectDetail" class="card">
          <pre class="muted">{{ effectDetail }}</pre>
        </div>
      </div>

      <div class="section-divider"></div>

      <h3>Lookup by Entity / Device</h3>
      <div v-if="!canReadDevices && !canReadEntities" class="muted">Missing capability: devices.read / entities.read</div>
      <div v-else>
        <div class="form-row">
          <input v-model="entityIdInput" class="input" placeholder="entity_id" />
          <input v-model="deviceIdLookup" class="input" placeholder="device_id" />
          <button class="btn secondary" @click="openSystemStage">Open System Stage</button>
        </div>
        <div class="muted">Navigation only. No lookup performed here.</div>
      </div>
    </div>
  </div>
</template>
