<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useCapabilities, hasCap } from "../lib/capabilities";
import { fetchJson, ApiError } from "../lib/request";
import { useAbortHandle } from "../lib/abort";
import { createPoller } from "../lib/poller";
import UCard from "../components/ui/UCard.vue";
import UButton from "../components/ui/UButton.vue";
import UInput from "../components/ui/UInput.vue";
import UEntitySelect from "../components/ui/UEntitySelect.vue";
import UBadge from "../components/ui/UBadge.vue";
import USkeleton from "../components/ui/USkeleton.vue";
import UEmpty from "../components/ui/UEmpty.vue";
import UInfoTooltip from "../components/ui/UInfoTooltip.vue";

type EventItem = {
  cursor: number;
  ts: string;
  type: string;
  payload: Record<string, unknown>;
  trace_id?: string | null;
};

type EventsResponse = {
  stream: string;
  cursor: number;
  next_cursor: number;
  items: EventItem[];
};

const { t, tm, rt } = useI18n();
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
const ackStatus = ref<string | null>(null);
const ackError = ref<string | null>(null);
const cursorInput = ref("");
const traceFilter = ref("");

const capsReady = computed(() => caps.status === "ready");
const canReadEvents = computed(() => hasCap("events.read"));
const canAckEvents = computed(() => hasCap("events.ack"));
const limit = 100;
const subscriberId = "ui.events.viewer";
const filteredItems = computed(() => {
  const raw = traceFilter.value.trim();
  if (!raw) return items.value;
  return items.value.filter((item) => String(item.trace_id ?? "").includes(raw));
});

function mapError(err: unknown): string {
  const e = err as ApiError;
  if (e?.status) return `HTTP ${e.status}: ${e.message}`;
  return (e && "message" in e) ? String(e.message) : "request_failed";
}

function buildUrl() {
  const params = new URLSearchParams();
  params.set("stream", stream.value.trim());
  params.set("cursor", String(cursor.value));
  params.set("limit", String(limit));
  return `/api/v1/events?${params.toString()}`;
}

function capsStatusMessage(): string {
  if (caps.status === "loading") return t('caps.loading');
  if (caps.status === "error") return `${t('caps.error')}: ${caps.error ?? t('common.unknown')}`;
  return t('caps.unavailable');
}

async function refreshEvents() {
  if (stoppedOnError.value) return;
  if (!capsReady.value) { error.value = capsStatusMessage(); return; }
  if (!canReadEvents.value) { error.value = t('caps.missing', { cap: 'events.read' }); return; }
  const s = stream.value.trim();
  if (!s) return;
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
  if (!capsReady.value) { error.value = capsStatusMessage(); return; }
  if (!canReadEvents.value) { error.value = t('caps.missing', { cap: 'events.read' }); return; }
  if (!stream.value.trim()) { error.value = t('events.streamRequired'); return; }
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

function setCursorFromInput() {
  const raw = String(cursorInput.value ?? "").trim();
  if (!raw) { error.value = t('events.cursorRequired'); return; }
  const next = Number(raw);
  if (!Number.isFinite(next) || next < 0) { error.value = t('events.cursorInvalid'); return; }
  cursor.value = Math.floor(next);
  items.value = [];
  nextCursor.value = 0;
  caughtUp.value = false;
}

function jumpToNext() {
  cursor.value = nextCursor.value;
  items.value = [];
  caughtUp.value = false;
}

async function ackCursor() {
  ackStatus.value = null;
  ackError.value = null;
  if (!capsReady.value) { ackError.value = capsStatusMessage(); return; }
  if (!canAckEvents.value) { ackError.value = t('caps.missing', { cap: 'events.ack' }); return; }
  const s = stream.value.trim();
  if (!s) { ackError.value = t('events.streamRequired'); return; }
  try {
    const res = await fetchJson<{ ok: boolean; stored_cursor: number; status: string }>(
      "/api/v1/events/ack",
      { method: "POST", body: JSON.stringify({ stream: s, subscriber_id: subscriberId, cursor: cursor.value }) },
      signal
    );
    if (res?.ok) {
      ackStatus.value = `ACK OK (${res.status ?? "OK"})`;
    } else {
      ackError.value = t('events.ackFailed');
    }
  } catch (err) {
    ackError.value = mapError(err);
  }
}

function retryAll() {
  if (!capsReady.value) { error.value = capsStatusMessage(); return; }
  if (!canReadEvents.value) { error.value = t('caps.missing', { cap: 'events.read' }); return; }
  error.value = null;
  stoppedOnError.value = false;
  refreshEvents().catch(() => { stoppedOnError.value = true; poller.stop(); });
  if (polling.value) poller.start();
}

const poller = createPoller(refreshEvents, 3000, { pauseWhenHidden: true });

watch(() => stream.value, () => {
  items.value = [];
  cursor.value = 0;
  nextCursor.value = 0;
  caughtUp.value = false;
  if (polling.value) stopPolling();
});

onMounted(() => {
  if (caps.status === "ready" && stream.value.trim()) startPolling();
});

onUnmounted(() => { stopPolling(); });
</script>

<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <div class="flex items-center">
          <h2 class="text-lg font-semibold text-[var(--text-primary)]">{{ t('pages.events.title') }}</h2>
          <UInfoTooltip :title="t('infoTooltips.events.title')" :items="tm('infoTooltips.events.items').map((i: any) => rt(i))" />
        </div>
        <p class="text-xs text-[var(--text-muted)] mt-0.5">{{ t('pages.events.description') }}</p>
      </div>
      <div class="flex gap-2">
        <a href="/api/v1/events/export?format=csv&limit=1000" download class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium border border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:border-[var(--primary)]/40 transition-colors">{{ t('events.exportCsv') }}</a>
        <UButton variant="secondary" size="sm" @click="retryAll">{{ t('events.retry') }}</UButton>
        <UButton variant="secondary" size="sm" :disabled="!polling" @click="stopPolling">{{ t('events.stop') }}</UButton>
      </div>
    </div>

    <!-- Caps unavailable -->
    <UCard v-if="caps.status !== 'ready' || !canReadEvents" padding="md">
      <p v-if="caps.status === 'unavailable'" class="text-sm text-[var(--text-muted)]">{{ t('caps.unavailable') }}</p>
      <p v-else-if="caps.status === 'loading'" class="text-sm text-[var(--text-muted)]">{{ t('caps.loading') }}</p>
      <p v-else-if="caps.status === 'error'" class="text-sm text-[var(--status-bad)]">{{ t('caps.error') }}: {{ caps.error }}</p>
      <p v-else class="text-sm text-[var(--text-muted)]">{{ t('caps.missing', { cap: 'events.read' }) }}</p>
    </UCard>

    <template v-else>
      <!-- Controls -->
      <UCard padding="md">
        <!-- Stream + trace filter row -->
        <div class="flex flex-col sm:flex-row gap-3 mb-3">
          <div class="flex-1">
            <label class="block text-xs text-[var(--text-muted)] mb-1">{{ t('events.stream') }}</label>
            <UEntitySelect v-model="stream" entity-type="stream" class="w-full" />
          </div>
          <div class="flex-1">
            <label class="block text-xs text-[var(--text-muted)] mb-1">{{ t('events.traceIdFilter') }}</label>
            <UInput v-model="traceFilter" placeholder="trace_id" class="w-full" />
          </div>
          <div class="flex items-end">
            <UButton :disabled="polling" @click="startPolling" class="w-full sm:w-auto">{{ t('events.start') }}</UButton>
          </div>
        </div>

        <!-- Cursor row -->
        <div class="flex flex-col sm:flex-row gap-3 items-end">
          <div class="flex-1">
            <label class="block text-xs text-[var(--text-muted)] mb-1">{{ t('events.setCursor') }}</label>
            <UInput v-model="cursorInput" type="number" min="0" placeholder="0" class="w-full" />
          </div>
          <div class="flex flex-wrap gap-2">
            <UButton variant="secondary" size="sm" @click="setCursorFromInput" :title="t('pages.events.setCursorTooltip')">{{ t('events.setCursor') }}</UButton>
            <UButton variant="secondary" size="sm" @click="jumpToNext" :title="t('pages.events.jumpToNextTooltip')">{{ t('events.jumpToNext') }}</UButton>
            <UButton v-if="canAckEvents" variant="secondary" size="sm" @click="ackCursor" :title="t('pages.events.ackTooltip')">ACK</UButton>
          </div>
        </div>

        <!-- Status bar -->
        <div class="mt-3 flex flex-wrap gap-x-4 gap-y-1">
          <span class="text-xs text-[var(--text-muted)] font-mono">{{ t('events.cursor') }}: {{ cursor }}</span>
          <span class="text-xs text-[var(--text-muted)] font-mono">{{ t('events.next') }}: {{ nextCursor }}</span>
          <span v-if="caughtUp" class="text-xs text-[var(--status-ok)]">{{ t('events.caughtUp') }}</span>
          <span v-if="polling" class="flex items-center gap-1 text-xs text-[var(--status-ok)]">
            <span class="h-1.5 w-1.5 rounded-full bg-[var(--status-ok)] animate-pulse" />
            {{ t('events.polling') }}
          </span>
        </div>

        <!-- Ack feedback -->
        <p v-if="ackStatus" class="mt-2 text-xs text-[var(--status-ok)]">{{ ackStatus }}</p>
        <p v-if="ackError" class="mt-2 text-xs text-[var(--status-bad)]">{{ ackError }}</p>
      </UCard>

      <!-- Error state -->
      <UCard v-if="error" padding="md" class="border-[var(--status-bad)]/50">
        <p class="text-sm text-[var(--status-bad)]">{{ error }}</p>
      </UCard>

      <!-- Events table -->
      <UCard v-else padding="none">
        <template #header>
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">
            {{ t('events.events') }}
            <span v-if="filteredItems.length" class="ml-1.5 text-xs font-normal text-[var(--text-muted)]">({{ filteredItems.length }})</span>
          </h3>
        </template>

        <!-- Loading -->
        <div v-if="loading && filteredItems.length === 0" class="p-4 space-y-2">
          <div v-for="i in 5" :key="i" class="flex gap-3 items-center">
            <USkeleton width="4rem" height="1rem" />
            <USkeleton width="6rem" height="1rem" />
            <USkeleton width="8rem" height="1rem" />
            <USkeleton height="1rem" />
          </div>
        </div>

        <!-- Empty -->
        <UEmpty
          v-else-if="filteredItems.length === 0"
          :title="t('events.noEvents')"
          :description="t('events.noEventsDesc')"
          icon="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z"
        />

        <!-- Table -->
        <div v-else class="overflow-x-auto">
          <table class="w-full text-xs">
            <thead>
              <tr class="border-b border-[var(--border)]">
                <th class="text-left px-4 py-2.5 text-[var(--text-muted)] font-medium whitespace-nowrap">{{ t('events.cursor') }}</th>
                <th class="text-left px-4 py-2.5 text-[var(--text-muted)] font-medium whitespace-nowrap">{{ t('events.colTime') }}</th>
                <th class="text-left px-4 py-2.5 text-[var(--text-muted)] font-medium whitespace-nowrap">{{ t('events.colType') }}</th>
                <th class="text-left px-4 py-2.5 text-[var(--text-muted)] font-medium whitespace-nowrap hidden md:table-cell">{{ t('events.colTrace') }}</th>
                <th class="text-left px-4 py-2.5 text-[var(--text-muted)] font-medium">{{ t('events.colPayload') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--border)]">
              <tr
                v-for="item in filteredItems"
                :key="`${item.cursor}-${item.type}`"
                class="hover:bg-[var(--bg-raised)] transition-colors"
              >
                <td class="px-4 py-2.5 font-mono text-[var(--text-muted)] whitespace-nowrap">{{ item.cursor }}</td>
                <td class="px-4 py-2.5 font-mono text-[var(--text-muted)] whitespace-nowrap">{{ item.ts }}</td>
                <td class="px-4 py-2.5 whitespace-nowrap">
                  <UBadge status="info">{{ item.type }}</UBadge>
                </td>
                <td class="px-4 py-2.5 font-mono text-[var(--text-muted)] hidden md:table-cell">{{ item.trace_id ?? "—" }}</td>
                <td class="px-4 py-2.5 font-mono text-[var(--text-muted)] max-w-xs truncate">{{ JSON.stringify(item.payload) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </UCard>
    </template>
  </div>
</template>
