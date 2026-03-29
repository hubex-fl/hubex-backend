<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";
import { useCapabilities, hasCap } from "../lib/capabilities";
import { fetchJson, ApiError } from "../lib/request";
import { useAbortHandle } from "../lib/abort";
import UCard from "../components/ui/UCard.vue";
import UButton from "../components/ui/UButton.vue";
import UInput from "../components/ui/UInput.vue";
import UBadge from "../components/ui/UBadge.vue";
import USkeleton from "../components/ui/USkeleton.vue";
import UEmpty from "../components/ui/UEmpty.vue";

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
  if (e?.status) return `HTTP ${e.status}: ${e.message}`;
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
  if (actorFilter.value.trim()) params.set("actor_id", actorFilter.value.trim());
  if (actionFilter.value.trim()) params.set("action", actionFilter.value.trim());
  return `/api/v1/audit?${params.toString()}`;
}

async function refreshList() {
  if (inflightList) return;
  if (!capsReady.value) { listError.value = capsStatusMessage(); return; }
  if (!canReadAudit.value) { listError.value = "Missing capability: audit.read"; return; }
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
  if (!capsReady.value) { detailError.value = capsStatusMessage(); return; }
  if (!canReadAudit.value) { detailError.value = "Missing capability: audit.read"; return; }
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
  if (!capsReady.value) { listError.value = capsStatusMessage(); return; }
  if (!canReadAudit.value) { listError.value = "Missing capability: audit.read"; return; }
  listError.value = null;
  refreshList().catch(() => undefined);
}

watch(() => selectedId.value, (val) => {
  detail.value = null;
  detailError.value = null;
  if (val !== null) refreshDetail(val).catch(() => undefined);
});

onUnmounted(() => { selectedId.value = null; });
</script>

<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold text-[var(--text-primary)]">Audit Log</h2>
        <p class="text-xs text-[var(--text-muted)] mt-0.5">Read-only audit trail</p>
      </div>
      <UButton variant="secondary" size="sm" @click="retryList">Refresh</UButton>
    </div>

    <!-- Caps unavailable -->
    <UCard v-if="caps.status !== 'ready' || !canReadAudit" padding="md">
      <p v-if="caps.status === 'unavailable'" class="text-sm text-[var(--text-muted)]">Capabilities unavailable</p>
      <p v-else-if="caps.status === 'loading'" class="text-sm text-[var(--text-muted)]">Loading capabilities…</p>
      <p v-else-if="caps.status === 'error'" class="text-sm text-[var(--status-bad)]">Capabilities error: {{ caps.error }}</p>
      <p v-else class="text-sm text-[var(--text-muted)]">Missing capability: audit.read</p>
    </UCard>

    <template v-else>
      <!-- Filter bar -->
      <UCard padding="md">
        <div class="flex flex-col sm:flex-row gap-3 items-end">
          <div class="flex-1">
            <label class="block text-xs text-[var(--text-muted)] mb-1">Actor</label>
            <UInput v-model="actorFilter" placeholder="user-123" class="w-full" />
          </div>
          <div class="flex-1">
            <label class="block text-xs text-[var(--text-muted)] mb-1">Action</label>
            <UInput v-model="actionFilter" placeholder="token.revoked" class="w-full" />
          </div>
          <div class="w-full sm:w-24">
            <label class="block text-xs text-[var(--text-muted)] mb-1">Limit</label>
            <UInput v-model.number="limit" type="number" min="1" max="500" class="w-full" />
          </div>
          <div>
            <UButton @click="retryList" class="w-full sm:w-auto">Apply</UButton>
          </div>
        </div>
      </UCard>

      <!-- Error state -->
      <UCard v-if="listError" padding="md" class="border-[var(--status-bad)]/50">
        <p class="text-sm text-[var(--status-bad)]">{{ listError }}</p>
      </UCard>

      <!-- Entries table -->
      <UCard v-else padding="none">
        <template #header>
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">
            Entries
            <span v-if="entries.length" class="ml-1.5 text-xs font-normal text-[var(--text-muted)]">({{ entries.length }})</span>
          </h3>
        </template>

        <!-- Loading -->
        <div v-if="loadingList" class="p-4 space-y-2">
          <div v-for="i in 6" :key="i" class="flex gap-3 items-center">
            <USkeleton width="3rem" height="1rem" />
            <USkeleton width="8rem" height="1rem" />
            <USkeleton width="6rem" height="1rem" />
            <USkeleton height="1rem" />
          </div>
        </div>

        <!-- Empty -->
        <UEmpty
          v-else-if="entries.length === 0"
          title="No audit entries"
          description="Every API action is logged here for traceability. Audit entries will appear as you use the platform."
          icon="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z"
        />

        <!-- Table -->
        <div v-else class="overflow-x-auto">
          <table class="w-full text-xs">
            <thead>
              <tr class="border-b border-[var(--border)]">
                <th class="text-left px-4 py-2.5 text-[var(--text-muted)] font-medium whitespace-nowrap">ID</th>
                <th class="text-left px-4 py-2.5 text-[var(--text-muted)] font-medium whitespace-nowrap hidden sm:table-cell">Time</th>
                <th class="text-left px-4 py-2.5 text-[var(--text-muted)] font-medium whitespace-nowrap">Actor</th>
                <th class="text-left px-4 py-2.5 text-[var(--text-muted)] font-medium whitespace-nowrap">Action</th>
                <th class="text-left px-4 py-2.5 text-[var(--text-muted)] font-medium hidden md:table-cell">Resource</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--border)]">
              <tr
                v-for="entry in entries"
                :key="entry.id"
                :class="[
                  'cursor-pointer transition-colors hover:bg-[var(--bg-raised)]',
                  selectedId === entry.id ? 'bg-[var(--primary)]/5' : '',
                ]"
                @click="selectedId = entry.id"
              >
                <td class="px-4 py-2.5 font-mono text-[var(--text-muted)]">{{ entry.id }}</td>
                <td class="px-4 py-2.5 font-mono text-[var(--text-muted)] whitespace-nowrap hidden sm:table-cell">
                  {{ entry.ts ? new Date(entry.ts).toLocaleString() : "—" }}
                </td>
                <td class="px-4 py-2.5 text-[var(--text-secondary)] truncate max-w-[8rem]">{{ entry.actor_id ?? "—" }}</td>
                <td class="px-4 py-2.5 whitespace-nowrap">
                  <UBadge v-if="entry.action" status="neutral">{{ entry.action }}</UBadge>
                  <span v-else class="text-[var(--text-muted)]">—</span>
                </td>
                <td class="px-4 py-2.5 text-[var(--text-muted)] truncate max-w-[10rem] hidden md:table-cell">{{ entry.resource ?? "—" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </UCard>

      <!-- Detail panel -->
      <UCard v-if="selectedId !== null" padding="md">
        <template #header>
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">Entry #{{ selectedId }}</h3>
          <button
            class="p-1 rounded text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
            @click="selectedId = null"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </template>

        <div v-if="detailError" class="text-sm text-[var(--status-bad)]">{{ detailError }}</div>
        <div v-else-if="loadingDetail" class="space-y-2">
          <USkeleton height="1rem" /><USkeleton height="1rem" width="80%" />
        </div>
        <pre v-else-if="detail" class="text-xs text-[var(--text-secondary)] overflow-auto whitespace-pre-wrap break-all">{{ JSON.stringify(detail, null, 2) }}</pre>
      </UCard>
    </template>
  </div>
</template>
