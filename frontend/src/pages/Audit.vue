<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";
import { useCapabilities, hasCap } from "../lib/capabilities";
import { fetchJson, ApiError } from "../lib/request";
import { useAbortHandle } from "../lib/abort";

type AuditEntry = {
  id: number;
  ts?: string;
  actor_type?: string;
  actor_id?: string;
  action?: string;
  resource?: string | null;
  metadata?: Record<string, unknown> | null;
  trace_id?: string | null;
};

const caps = useCapabilities();
const { signal: listSignal } = useAbortHandle();
const { signal: detailSignal } = useAbortHandle();

const entries = ref<AuditEntry[]>([]);
const selectedId = ref<number | null>(null);
const detail = ref<AuditEntry | null>(null);
const listError = ref<string | null>(null);
const detailError = ref<string | null>(null);
const loadingList = ref(false);
const loadingDetail = ref(false);

const limit = ref(100);
const actorFilter = ref("");
const actionFilter = ref("");

const capsReady = computed(() => caps.status === "ready");
const canReadAudit = computed(() => hasCap("audit.read"));

let inflightList = false;
let inflightDetail = false;

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

function buildListUrl(): string {
  const params = new URLSearchParams();
  params.set("limit", String(Math.max(1, Math.min(500, limit.value))));
  if (actorFilter.value.trim()) {
    params.set("actor_id", actorFilter.value.trim());
  }
  if (actionFilter.value.trim()) {
    params.set("action", actionFilter.value.trim());
  }
  return `/api/v1/audit?${params.toString()}`;
}

async function refreshList() {
  if (inflightList) return;
  if (!capsReady.value) {
    listError.value = capsStatusMessage();
    return;
  }
  if (!canReadAudit.value) {
    listError.value = "Missing capability: audit.read";
    return;
  }
  inflightList = true;
  loadingList.value = true;
  try {
    entries.value = await fetchJson<AuditEntry[]>(buildListUrl(), { method: "GET" }, listSignal);
    listError.value = null;
  } catch (err) {
    listError.value = mapError(err);
  } finally {
    inflightList = false;
    loadingList.value = false;
  }
}

async function refreshDetail(id: number) {
  if (inflightDetail) return;
  if (!capsReady.value) {
    detailError.value = capsStatusMessage();
    return;
  }
  if (!canReadAudit.value) {
    detailError.value = "Missing capability: audit.read";
    return;
  }
  inflightDetail = true;
  loadingDetail.value = true;
  try {
    detail.value = await fetchJson<AuditEntry>(`/api/v1/audit/${id}`, { method: "GET" }, detailSignal);
    detailError.value = null;
  } catch (err) {
    detailError.value = mapError(err);
  } finally {
    inflightDetail = false;
    loadingDetail.value = false;
  }
}

function retryList() {
  if (!capsReady.value) {
    listError.value = capsStatusMessage();
    return;
  }
  if (!canReadAudit.value) {
    listError.value = "Missing capability: audit.read";
    return;
  }
  listError.value = null;
  refreshList().catch(() => undefined);
}

watch(
  () => selectedId.value,
  (val) => {
    detail.value = null;
    detailError.value = null;
    if (val !== null) {
      refreshDetail(val).catch(() => undefined);
    }
  }
);

onUnmounted(() => {
  selectedId.value = null;
});
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>Audit (read-only)</h2>
      <button class="btn secondary" @click="retryList">Retry</button>
    </div>

    <p v-if="caps.status === 'unavailable'" class="muted">Capabilities unavailable</p>
    <p v-else-if="caps.status === 'loading'" class="muted">Loading capabilities.</p>
    <p v-else-if="caps.status === 'error'" class="error">Capabilities error: {{ caps.error }}</p>
    <div v-else-if="!canReadAudit" class="muted">Missing capability: audit.read</div>

    <div v-else class="card">
      <div class="form-row">
        <div>
          <label class="muted">Actor</label>
          <input v-model="actorFilter" class="input" placeholder="user-123" />
        </div>
        <div>
          <label class="muted">Action</label>
          <input v-model="actionFilter" class="input" placeholder="token.revoked" />
        </div>
        <div>
          <label class="muted">Limit</label>
          <input v-model.number="limit" type="number" min="1" max="500" class="input" />
        </div>
        <button class="btn" @click="retryList">Refresh</button>
      </div>

      <div v-if="listError" class="error">{{ listError }}</div>
      <div v-else-if="loadingList" class="muted">Loading.</div>
      <div v-else-if="entries.length === 0" class="muted">No audit entries.</div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>TS</th>
            <th>Actor</th>
            <th>Action</th>
            <th>Resource</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="entry in entries"
            :key="entry.id"
            @click="selectedId = entry.id"
          >
            <td>{{ entry.id }}</td>
            <td>{{ entry.ts ?? "-" }}</td>
            <td>{{ entry.actor_id ?? "-" }}</td>
            <td>{{ entry.action ?? "-" }}</td>
            <td>{{ entry.resource ?? "-" }}</td>
          </tr>
        </tbody>
      </table>

      <div class="section-divider"></div>

      <div v-if="selectedId === null" class="muted">Select an entry to view details.</div>
      <div v-else>
        <div class="muted">Selected: {{ selectedId }}</div>
        <div v-if="detailError" class="error">{{ detailError }}</div>
        <div v-else-if="loadingDetail" class="muted">Loading.</div>
        <div v-else-if="detail" class="card">
          <pre class="muted">{{ detail }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>
