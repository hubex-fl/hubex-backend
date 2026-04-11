<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useCapabilities, hasCap } from "../lib/capabilities";
import { fetchJson, ApiError } from "../lib/request";
import { useAbortHandle } from "../lib/abort";
import { createPoller } from "../lib/poller";
import UInfoTooltip from "../components/ui/UInfoTooltip.vue";

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

const { t, tm, rt } = useI18n();
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

const capsReady = computed(() => caps.status === "ready");
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

function capsStatusMessage(): string {
  if (caps.status === "loading") return t('pages.effects.capsLoading');
  if (caps.status === "error") return t('pages.effects.capsError', { error: caps.error ?? 'unknown' });
  return t('pages.effects.capsUnavailable');
}

async function refreshList(reset = false) {
  if (stoppedOnError.value || inflightList) return;
  if (!capsReady.value) {
    listError.value = capsStatusMessage();
    return;
  }
  if (!canReadEffects.value) {
    listError.value = t('pages.effects.missingCap');
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
  if (!capsReady.value) {
    detailError.value = capsStatusMessage();
    return;
  }
  if (!canReadEffects.value) {
    detailError.value = t('pages.effects.missingCap');
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
  if (!capsReady.value) {
    listError.value = capsStatusMessage();
    return;
  }
  if (!canReadEffects.value) {
    listError.value = t('pages.effects.missingCap');
    return;
  }
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
  if (!capsReady.value) {
    listError.value = capsStatusMessage();
    return;
  }
  if (!canReadEffects.value) {
    listError.value = t('pages.effects.missingCap');
    return;
  }
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
      <div class="flex items-center gap-1">
        <h2>{{ t('nav.effects') }}</h2>
        <UInfoTooltip :title="t('infoTooltips.effects.title')" :items="tm('infoTooltips.effects.items').map((i: any) => rt(i))" />
      </div>
      <div class="row">
        <button class="btn secondary" @click="retryList">{{ t('pages.effects.retry') }}</button>
        <button class="btn secondary" @click="stopPolling" :disabled="!polling">{{ t('pages.effects.stop') }}</button>
      </div>
    </div>

    <p v-if="caps.status === 'unavailable'" class="muted">{{ t('pages.effects.capsUnavailable') }}</p>
    <p v-else-if="caps.status === 'loading'" class="muted">{{ t('pages.effects.capsLoading') }}</p>
    <p v-else-if="caps.status === 'error'" class="error">{{ t('pages.effects.capsError', { error: caps.error ?? '' }) }}</p>

    <div v-else-if="!canReadEffects" class="muted">{{ t('pages.effects.missingCap') }}</div>
    <div v-else class="card">
      <div class="form-row">
        <div>
          <label class="muted">{{ t('pages.effects.kindLabel') }}</label>
          <input v-model="kindFilter" class="input" :placeholder="t('pages.effects.kindPlaceholder')" />
        </div>
        <div>
          <label class="muted">{{ t('pages.effects.limitLabel') }}</label>
          <input v-model.number="limit" type="number" min="1" max="200" class="input" />
        </div>
        <button class="btn" @click="startPolling" :disabled="polling">{{ t('pages.effects.start') }}</button>
      </div>
      <p class="muted">
        <span v-if="caughtUp">{{ t('pages.effects.caughtUp') }}</span>
      </p>

      <div v-if="listError" class="error">{{ listError }}</div>
      <div v-else-if="loadingList" class="muted">{{ t('pages.effects.loading') }}</div>
      <div v-else-if="effects.length === 0" class="muted">{{ t('pages.effects.noEffects') }}</div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>{{ t('pages.effects.colEffectId') }}</th>
            <th>{{ t('pages.effects.colKind') }}</th>
            <th>{{ t('pages.effects.colStatus') }}</th>
            <th>{{ t('pages.effects.colCreated') }}</th>
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

      <div v-if="!selectedEffectId" class="muted">{{ t('pages.effects.selectToView') }}</div>
      <div v-else>
        <div class="muted">{{ t('pages.effects.selected', { id: selectedEffectId }) }}</div>
        <div v-if="detailError" class="error">{{ detailError }}</div>
        <div v-else-if="loadingDetail" class="muted">{{ t('pages.effects.loading') }}</div>
        <div v-else-if="detail" class="card">
          <pre class="muted">{{ detail }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>
