<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useCapabilities, hasCap } from "../lib/capabilities";
import { fetchJson, ApiError } from "../lib/request";
import { useAbortHandle } from "../lib/abort";
import { createPoller } from "../lib/poller";

type EffectItem = {
  id: number;
  created_at: string;
  effect_id: string;
  source_event_id: number | null;
  kind: string;
  status: string;
  payload_json: Record<string, unknown>;
  error_json: Record<string, unknown> | null;
};

const caps = useCapabilities();
const { signal: listSignal } = useAbortHandle();
const { signal: detailSignal } = useAbortHandle();

const effects = ref<EffectItem[]>([]);
const selectedEffectId = ref<string | null>(null);
const detail = ref<EffectItem | null>(null);
const listError = ref<string | null>(null);
const detailError = ref<string | null>(null);
const loadingList = ref(false);
const loadingDetail = ref(false);
const stoppedOnError = ref(false);
const polling = ref(false);
const caughtUp = ref(false);

const limit = ref(50);
const kindFilter = ref("");

const canReadEffects = computed(() => hasCap("effects.read"));

let inflightList = false;
let inflightDetail = false;

function mapError(err: unknown): string {
  const e = err as ApiError;
  if (e?.status) {
    return `HTTP ${e.status}: ${e.message}`;
  }
  return (e && "message" in e) ? String(e.message) : "request_failed";
}

function lastId(): number | null {
  if (!effects.value.length) return null;
  return effects.value[effects.value.length - 1].id;
}

function buildListUrl(afterId?: number | null) {
  const params = new URLSearchParams();
  params.set("limit", String(Math.max(1, Math.min(200, limit.value))));
  if (afterId !== null && afterId !== undefined) {
    params.set("after_id", String(afterId));
  }
  if (kindFilter.value.trim()) {
    params.set("kind", kindFilter.value.trim());
  }
  return `/api/v1/effects?${params.toString()}`;
}

async function refreshList(reset = false) {
  if (stoppedOnError.value || inflightList) return;
  if (!canReadEffects.value) {
    listError.value = "Missing capability: effects.read";
    return;
  }
  inflightList = true;
  loadingList.value = true;
  const afterId = reset ? null : lastId();
  try {
    const res = await fetchJson<EffectItem[]>(buildListUrl(afterId), { method: "GET" }, listSignal);
    if (reset) {
      effects.value = res;
    } else if (res.length) {
      effects.value = [...effects.value, ...res].slice(-500);
    }
    caughtUp.value = res.length === 0;
    listError.value = null;
  } catch (err) {
    listError.value = mapError(err);
    stoppedOnError.value = true;
    poller.stop();
    polling.value = false;
  } finally {
    inflightList = false;
    loadingList.value = false;
  }
}

async function refreshDetail(effectId: string) {
  if (inflightDetail) return;
  if (!canReadEffects.value) {
    detailError.value = "Missing capability: effects.read";
    return;
  }
  inflightDetail = true;
  loadingDetail.value = true;
  try {
    const res = await fetchJson<EffectItem>(`/api/v1/effects/${encodeURIComponent(effectId)}`, { method: "GET" }, detailSignal);
    detail.value = res;
    detailError.value = null;
  } catch (err) {
    detailError.value = mapError(err);
  } finally {
    inflightDetail = false;
    loadingDetail.value = false;
  }
}

function startPolling() {
  if (polling.value) return;
  listError.value = null;
  stoppedOnError.value = false;
  polling.value = true;
  poller.start();
}

function stopPolling() {
  if (!polling.value) return;
  polling.value = false;
  poller.stop();
}

function retryList() {
  listError.value = null;
  stoppedOnError.value = false;
  refreshList(true).catch(() => {
    stoppedOnError.value = true;
    poller.stop();
    polling.value = false;
  });
  if (polling.value) {
    poller.start();
  }
}

const poller = createPoller(() => refreshList(false), 3000, { pauseWhenHidden: true });

watch(
  () => kindFilter.value,
  () => {
    effects.value = [];
    caughtUp.value = false;
    if (polling.value) {
      stopPolling();
    }
  }
);

watch(
  () => selectedEffectId.value,
  (val) => {
    detail.value = null;
    if (val) {
      refreshDetail(val).catch(() => undefined);
    }
  }
);

onMounted(() => {
  if (caps.status === "ready") {
    refreshList(true).catch(() => undefined);
  }
});

onUnmounted(() => {
  stopPolling();
});
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>Effects Trace (read-only)</h2>
      <div class="row">
        <button class="btn secondary" @click="retryList">Retry</button>
        <button class="btn secondary" @click="stopPolling" :disabled="!polling">Stop</button>
      </div>
    </div>

    <p v-if="caps.status === 'unavailable'" class="muted">Capabilities unavailable</p>
    <p v-else-if="caps.status === 'loading'" class="muted">Loading capabilities.</p>
    <p v-else-if="caps.status === 'error'" class="error">Capabilities error: {{ caps.error }}</p>

    <div v-if="!canReadEffects" class="muted">Missing capability: effects.read</div>
    <div v-else class="card">
      <div class="form-row">
        <div>
          <label class="muted">Kind (optional)</label>
          <input v-model="kindFilter" class="input" placeholder="vars.v3.apply" />
        </div>
        <div>
          <label class="muted">Limit</label>
          <input v-model.number="limit" type="number" min="1" max="200" class="input" />
        </div>
        <button class="btn" @click="startPolling" :disabled="polling">Start</button>
      </div>
      <p class="muted">
        <span v-if="caughtUp">- Caught up</span>
      </p>

      <div v-if="listError" class="error">{{ listError }}</div>
      <div v-else-if="loadingList" class="muted">Loading.</div>
      <div v-else-if="effects.length === 0" class="muted">No effects.</div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>Effect ID</th>
            <th>Kind</th>
            <th>Status</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="effect in effects"
            :key="effect.effect_id"
            @click="selectedEffectId = effect.effect_id"
          >
            <td>{{ effect.effect_id }}</td>
            <td>{{ effect.kind }}</td>
            <td>{{ effect.status }}</td>
            <td>{{ effect.created_at }}</td>
          </tr>
        </tbody>
      </table>

      <div class="section-divider"></div>

      <div v-if="!selectedEffectId" class="muted">Select an effect to view details.</div>
      <div v-else>
        <div class="muted">Selected: {{ selectedEffectId }}</div>
        <div v-if="detailError" class="error">{{ detailError }}</div>
        <div v-else-if="loadingDetail" class="muted">Loading.</div>
        <div v-else-if="detail" class="card">
          <pre class="muted">{{ detail }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>
