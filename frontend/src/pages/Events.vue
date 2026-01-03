<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useCapabilities, hasCap } from "../lib/capabilities";
import { fetchJson, ApiError } from "../lib/request";
import { useAbortHandle } from "../lib/abort";
import { createPoller } from "../lib/poller";

type EventItem = {
  cursor: number;
  ts: string;
  type: string;
  payload: Record<string, unknown>;
};

type EventsResponse = {
  stream: string;
  cursor: number;
  next_cursor: number;
  items: EventItem[];
};

const caps = useCapabilities();
const { signal } = useAbortHandle();

const stream = ref("");
const items = ref<EventItem[]>([]);
const cursor = ref(0);
const nextCursor = ref(0);
const loading = ref(false);
const error = ref<string | null>(null);
const stoppedOnError = ref(false);
const caughtUp = ref(false);
const polling = ref(false);

const canReadEvents = computed(() => hasCap("events.read"));
const limit = 100;

function mapError(err: unknown): string {
  const e = err as ApiError;
  if (e?.status) {
    return `HTTP ${e.status}: ${e.message}`;
  }
  return (e && "message" in e) ? String(e.message) : "request_failed";
}

function buildUrl() {
  const params = new URLSearchParams();
  params.set("stream", stream.value.trim());
  params.set("cursor", String(cursor.value));
  params.set("limit", String(limit));
  return `/api/v1/events?${params.toString()}`;
}

async function refreshEvents() {
  if (stoppedOnError.value) return;
  if (!canReadEvents.value) {
    error.value = "Missing capability: events.read";
    return;
  }
  const s = stream.value.trim();
  if (!s) {
    return;
  }
  loading.value = true;
  try {
    const res = await fetchJson<EventsResponse>(buildUrl(), { method: "GET" }, signal);
    nextCursor.value = res.next_cursor ?? res.cursor ?? cursor.value;
    if (res.items?.length) {
      items.value = [...items.value, ...res.items].slice(-500);
      cursor.value = nextCursor.value;
      caughtUp.value = false;
    } else {
      caughtUp.value = true;
    }
  } catch (err) {
    error.value = mapError(err);
    stoppedOnError.value = true;
    poller.stop();
  } finally {
    loading.value = false;
  }
}

function startPolling() {
  if (polling.value) return;
  if (!stream.value.trim()) {
    error.value = "Stream required";
    return;
  }
  error.value = null;
  stoppedOnError.value = false;
  polling.value = true;
  poller.start();
}

function stopPolling() {
  if (!polling.value) return;
  polling.value = false;
  poller.stop();
}

function retryAll() {
  error.value = null;
  stoppedOnError.value = false;
  refreshEvents().catch(() => {
    stoppedOnError.value = true;
    poller.stop();
  });
  if (polling.value) {
    poller.start();
  }
}

const poller = createPoller(refreshEvents, 3000, { pauseWhenHidden: true });

watch(
  () => stream.value,
  () => {
    items.value = [];
    cursor.value = 0;
    nextCursor.value = 0;
    caughtUp.value = false;
    if (polling.value) {
      stopPolling();
    }
  }
);

onMounted(() => {
  if (caps.status === "ready" && stream.value.trim()) {
    startPolling();
  }
});

onUnmounted(() => {
  stopPolling();
});
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>Events Viewer (read-only)</h2>
      <div class="row">
        <button class="btn secondary" @click="retryAll">Retry</button>
        <button class="btn secondary" @click="stopPolling" :disabled="!polling">Stop</button>
      </div>
    </div>

    <p v-if="caps.status === 'unavailable'" class="muted">Capabilities unavailable</p>
    <p v-else-if="caps.status === 'loading'" class="muted">Loading capabilities.</p>
    <p v-else-if="caps.status === 'error'" class="error">Capabilities error: {{ caps.error }}</p>

    <div v-if="!canReadEvents" class="muted">Missing capability: events.read</div>
    <div v-else class="card">
      <div class="form-row">
        <div>
          <label class="muted">Stream</label>
          <input v-model="stream" class="input" placeholder="tenant.system" />
        </div>
        <button class="btn" @click="startPolling" :disabled="polling">Start</button>
      </div>
      <p class="muted">ACK disabled in Phase-2</p>
      <p class="muted">
        Cursor: {{ cursor }} | Next: {{ nextCursor }}
        <span v-if="caughtUp"> - Caught up</span>
      </p>

      <div v-if="error" class="error">{{ error }}</div>
      <div v-else-if="loading" class="muted">Loading.</div>
      <div v-else-if="items.length === 0" class="muted">No events.</div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>Cursor</th>
            <th>Time</th>
            <th>Type</th>
            <th>Payload</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="`${item.cursor}-${item.type}`">
            <td>{{ item.cursor }}</td>
            <td>{{ item.ts }}</td>
            <td>{{ item.type }}</td>
            <td><pre class="muted">{{ item.payload }}</pre></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>




