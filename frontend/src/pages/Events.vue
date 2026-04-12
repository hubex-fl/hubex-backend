<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch, nextTick } from "vue";
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

const stream = ref("system");
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
const traceFilter = ref("");
const traceDropdownOpen = ref(false);
const traceInputEl = ref<HTMLInputElement | null>(null);
const traceDropdownEl = ref<HTMLDivElement | null>(null);
const jumpPreset = ref("");
const useFromTs = ref(false);
const fromTsValue = ref(0);

const capsReady = computed(() => caps.status === "ready");
const canReadEvents = computed(() => hasCap("events.read"));
const canAckEvents = computed(() => hasCap("events.ack"));
const limit = 100;
const MAX_ITEMS = 200;
const subscriberId = "ui.events.viewer";

/* ── Trace ID combobox helpers ── */
const uniqueTraceIds = computed(() => {
  const seen = new Map<string, EventItem>();
  for (const item of items.value) {
    const tid = item.trace_id;
    if (tid && !seen.has(tid)) seen.set(tid, item);
  }
  // Return most recent 20
  return Array.from(seen.entries()).slice(-20).reverse();
});

const filteredTraceOptions = computed(() => {
  const q = traceFilter.value.trim().toLowerCase();
  if (!q) return uniqueTraceIds.value;
  return uniqueTraceIds.value.filter(([tid]) => tid.toLowerCase().includes(q));
});

function selectTraceId(tid: string) {
  traceFilter.value = tid;
  traceDropdownOpen.value = false;
}

function clearTraceFilter() {
  traceFilter.value = "";
  traceDropdownOpen.value = false;
}

function onTraceInputFocus() {
  if (uniqueTraceIds.value.length > 0) traceDropdownOpen.value = true;
}

function onTraceInputBlur(e: FocusEvent) {
  // Delay to allow click on dropdown option
  const related = e.relatedTarget as HTMLElement | null;
  if (traceDropdownEl.value?.contains(related)) return;
  setTimeout(() => { traceDropdownOpen.value = false; }, 150);
}

function truncateId(id: string, maxLen = 16): string {
  return id.length > maxLen ? id.slice(0, maxLen) + "\u2026" : id;
}

const filteredItems = computed(() => {
  const raw = traceFilter.value.trim();
  if (!raw) return items.value;
  return items.value.filter((item) => String(item.trace_id ?? "").includes(raw));
});

/* ── Jump-to presets ── */
type JumpPresetOption = { key: string; labelKey: string; getTs: () => number };

const jumpPresets: JumpPresetOption[] = [
  { key: "latest", labelKey: "events.jumpLatest", getTs: () => 0 },
  { key: "1h",     labelKey: "events.jump1h",     getTs: () => (Date.now() / 1000) - 3600 },
  { key: "6h",     labelKey: "events.jump6h",     getTs: () => (Date.now() / 1000) - 21600 },
  { key: "24h",    labelKey: "events.jump24h",    getTs: () => (Date.now() / 1000) - 86400 },
  { key: "7d",     labelKey: "events.jump7d",     getTs: () => (Date.now() / 1000) - 604800 },
];

function applyJumpPreset() {
  const preset = jumpPresets.find((p) => p.key === jumpPreset.value);
  if (!preset) return;
  if (preset.key === "latest") {
    // Reset to beginning — newest events
    cursor.value = 0;
    useFromTs.value = false;
    fromTsValue.value = 0;
  } else {
    useFromTs.value = true;
    fromTsValue.value = preset.getTs();
    cursor.value = 0;
  }
  items.value = [];
  nextCursor.value = 0;
  caughtUp.value = false;
  // Trigger an immediate fetch
  refreshEvents();
}

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
  if (useFromTs.value && fromTsValue.value > 0) {
    params.set("from_ts", String(fromTsValue.value));
  }
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
      items.value = [...items.value, ...res.items].slice(-MAX_ITEMS);
      cursor.value = nextCursor.value;
      caughtUp.value = false;
      // After first successful fetch with from_ts, switch to cursor-based for subsequent polls
      if (useFromTs.value) {
        useFromTs.value = false;
        fromTsValue.value = 0;
      }
    } else {
      caughtUp.value = true;
      if (useFromTs.value) {
        useFromTs.value = false;
        fromTsValue.value = 0;
      }
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
  // Full reset: re-fetch from cursor 0, preserve the trace filter
  items.value = [];
  cursor.value = 0;
  nextCursor.value = 0;
  caughtUp.value = false;
  refreshEvents().catch(() => { stoppedOnError.value = true; poller.stop(); });
  if (polling.value) poller.start();
}

const poller = createPoller(refreshEvents, 3000, { pauseWhenHidden: true });

watch(() => stream.value, () => {
  const wasPolling = polling.value;
  if (wasPolling) stopPolling();
  items.value = [];
  cursor.value = 0;
  nextCursor.value = 0;
  caughtUp.value = false;
  error.value = null;
  stoppedOnError.value = false;
  useFromTs.value = false;
  fromTsValue.value = 0;
  // Auto-restart polling if it was running before the stream change
  if (wasPolling && stream.value.trim()) {
    nextTick(() => startPolling());
  }
});

/* ── Auto-start: default to "system" stream and begin polling ── */
onMounted(() => {
  if (!stream.value.trim()) stream.value = "system";

  // Wait for caps to be ready, then auto-start
  if (capsReady.value && canReadEvents.value) {
    nextTick(() => startPolling());
  } else {
    const unwatch = watch(
      () => caps.status,
      (status) => {
        if (status === "ready" && canReadEvents.value && stream.value.trim()) {
          nextTick(() => startPolling());
          unwatch();
        }
      }
    );
  }
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
          <UInfoTooltip :title="t('infoTooltips.events.title')" :items="tm('infoTooltips.events.items').map((i: any) => rt(i))" tourId="events-overview" />
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
            <label class="block text-xs text-[var(--text-muted)] mb-1 inline-flex items-center gap-1">{{ t('events.stream') }}
              <UInfoTooltip :title="t('events.streamTooltip')" :items="tm('events.streamTooltipItems').map((i: any) => rt(i))" />
            </label>
            <UEntitySelect v-model="stream" entity-type="stream" class="w-full" />
          </div>

          <!-- Trace ID combobox -->
          <div class="flex-1 relative">
            <label class="block text-xs text-[var(--text-muted)] mb-1">
              <span class="inline-flex items-center gap-1">{{ t('events.traceIdFilter') }}<UInfoTooltip :title="t('events.traceIdTooltip')" :items="tm('events.traceIdTooltipItems').map((i: any) => rt(i))" /></span>
            </label>
            <div class="relative">
              <input
                ref="traceInputEl"
                v-model="traceFilter"
                type="text"
                :placeholder="uniqueTraceIds.length ? t('events.traceSelectPlaceholder') : 'trace_id'"
                class="w-full h-9 px-3 pr-16 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--primary)]/60 focus:ring-1 focus:ring-[var(--primary)]/30"
                @focus="onTraceInputFocus"
                @blur="onTraceInputBlur"
                @input="traceDropdownOpen = uniqueTraceIds.length > 0"
              />
              <div class="absolute inset-y-0 right-0 flex items-center gap-0.5 pr-1.5">
                <button
                  v-if="traceFilter"
                  @mousedown.prevent="clearTraceFilter"
                  class="p-1 rounded hover:bg-[var(--bg-raised)] text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                  :title="t('common.clear')"
                >
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
                <button
                  v-if="uniqueTraceIds.length"
                  @mousedown.prevent="traceDropdownOpen = !traceDropdownOpen"
                  class="p-1 rounded hover:bg-[var(--bg-raised)] text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                >
                  <svg class="w-3.5 h-3.5 transition-transform" :class="{ 'rotate-180': traceDropdownOpen }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg>
                </button>
              </div>
            </div>
            <!-- Trace ID dropdown -->
            <div
              v-if="traceDropdownOpen && filteredTraceOptions.length"
              ref="traceDropdownEl"
              class="absolute z-50 mt-1 w-full max-h-56 overflow-y-auto rounded-lg border border-[var(--border)] bg-[var(--bg-card)] shadow-lg"
            >
              <button
                v-for="[tid, item] in filteredTraceOptions"
                :key="tid"
                @mousedown.prevent="selectTraceId(tid)"
                class="w-full text-left px-3 py-2 hover:bg-[var(--bg-raised)] transition-colors flex items-center gap-2 text-xs"
              >
                <span class="font-mono text-[var(--text-primary)] truncate flex-shrink-0" style="max-width: 10rem">{{ truncateId(tid) }}</span>
                <UBadge status="info" class="flex-shrink-0">{{ item.type }}</UBadge>
                <span class="text-[var(--text-muted)] ml-auto whitespace-nowrap flex-shrink-0">{{ item.ts }}</span>
              </button>
              <div v-if="filteredTraceOptions.length === 0" class="px-3 py-2 text-xs text-[var(--text-muted)]">
                {{ t('events.noTraceIds') }}
              </div>
            </div>
          </div>

          <div class="flex items-end">
            <UButton :disabled="polling" @click="startPolling" class="w-full sm:w-auto">{{ t('events.start') }}</UButton>
          </div>
        </div>

        <!-- Jump-to row -->
        <div class="flex flex-col sm:flex-row gap-3 items-end">
          <div class="flex-1">
            <label class="block text-xs text-[var(--text-muted)] mb-1">
              <span class="inline-flex items-center">{{ t('events.jumpTo') }}<UInfoTooltip :title="t('events.jumpToTooltip')" :items="[]" /></span>
            </label>
            <select
              v-model="jumpPreset"
              @change="applyJumpPreset"
              class="w-full h-9 px-3 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--primary)]/60 focus:ring-1 focus:ring-[var(--primary)]/30 appearance-none cursor-pointer"
              style="background-image: url('data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2212%22 height=%2212%22 viewBox=%220 0 24 24%22 fill=%22none%22 stroke=%22%23888%22 stroke-width=%222%22%3E%3Cpath d=%22M6 9l6 6 6-6%22/%3E%3C/svg%3E'); background-repeat: no-repeat; background-position: right 0.75rem center;"
            >
              <option value="" disabled>{{ t('events.jumpSelectTime') }}</option>
              <option v-for="preset in jumpPresets" :key="preset.key" :value="preset.key">
                {{ t(preset.labelKey) }}
              </option>
            </select>
          </div>
          <div class="flex flex-wrap gap-2">
            <UButton variant="secondary" size="sm" @click="jumpToNext" :title="t('events.jumpToNextTooltip')">
              {{ t('events.jumpToNext') }}
            </UButton>
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
            <span v-if="filteredItems.length" class="ml-1.5 text-xs font-normal text-[var(--text-muted)]">({{ filteredItems.length }}<template v-if="items.length >= MAX_ITEMS"> / {{ t('events.showingLast', { count: MAX_ITEMS }) }}</template>)</span>
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
                <th class="text-left px-4 py-2.5 text-[var(--text-muted)] font-medium whitespace-nowrap hidden md:table-cell">
                  <span class="inline-flex items-center">{{ t('events.colTrace') }}<UInfoTooltip :title="t('events.traceIdTooltip')" :items="[]" /></span>
                </th>
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
                <td class="px-4 py-2.5 font-mono hidden md:table-cell">
                  <button
                    v-if="item.trace_id"
                    @click="selectTraceId(item.trace_id!)"
                    class="text-[var(--primary)] hover:underline cursor-pointer"
                    :title="t('events.filterByTrace')"
                  >{{ truncateId(item.trace_id, 20) }}</button>
                  <span v-else class="text-[var(--text-muted)]">&mdash;</span>
                </td>
                <td class="px-4 py-2.5 font-mono text-[var(--text-muted)] max-w-xs truncate">{{ JSON.stringify(item.payload) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </UCard>
    </template>
  </div>
</template>
