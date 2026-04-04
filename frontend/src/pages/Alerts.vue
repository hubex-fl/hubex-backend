<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import { useCapabilities, hasCap } from "../lib/capabilities";
import { useAlerts } from "../composables/useAlerts";
import UEmpty from "../components/ui/UEmpty.vue";
import type { AlertRule, AlertEvent } from "../composables/useAlerts";
import { useToastStore } from "../stores/toast";
import { mapErrorToUserText, parseApiError } from "../lib/errors";
import { relativeTime } from "../composables/useRecentAlerts";
import UEntitySelect from "../components/ui/UEntitySelect.vue";

const alertRoute = useRoute();
const caps = useCapabilities();
const toast = useToastStore();

const {
  rules,
  events,
  loading,
  error,
  refreshing,
  reload,
  ackEvent,
  resolveEvent,
  createRule,
  updateRule,
  deleteRule,
} = useAlerts();

// ── Tabs ──────────────────────────────────────────────────────────────────────
const activeTab = ref<"events" | "rules">("events");

// ── Refresh ───────────────────────────────────────────────────────────────────
const isRefreshing = ref(false);
async function handleRefresh() {
  isRefreshing.value = true;
  try { await reload(); } finally { isRefreshing.value = false; }
}

// ── Events Filters ─────────────────────────────────────────────────────────
const statusFilter = ref<"all" | "firing" | "acknowledged" | "resolved">("all");
const ruleFilter = ref<number | "all">("all");

const statusOrder: Record<string, number> = { firing: 0, acknowledged: 1, resolved: 2 };

const filteredEvents = computed(() => {
  let list = [...events.value];
  if (statusFilter.value !== "all") list = list.filter((e) => e.status === statusFilter.value);
  if (ruleFilter.value !== "all") list = list.filter((e) => e.rule_id === ruleFilter.value);
  list.sort((a, b) => {
    const sd = (statusOrder[a.status] ?? 9) - (statusOrder[b.status] ?? 9);
    if (sd !== 0) return sd;
    return new Date(b.triggered_at).getTime() - new Date(a.triggered_at).getTime();
  });
  return list;
});

function ruleNameFor(ruleId: number): string {
  const r = rules.value.find((r) => r.id === ruleId);
  return r ? r.name : `Rule #${ruleId}`;
}

// ── Event Actions ─────────────────────────────────────────────────────────
const ackingIds = ref(new Set<number>());
const resolvingIds = ref(new Set<number>());
const justAckedId = ref<number | null>(null);
const justAckedRuleId = ref<number | null>(null);

async function handleAck(event: AlertEvent) {
  ackingIds.value.add(event.id);
  try {
    await ackEvent(event.id);
    toast.addToast(`Alert acknowledged`, "success");
    justAckedId.value = event.id;
    justAckedRuleId.value = event.rule_id;
    // Auto-dismiss after 15s
    setTimeout(() => { if (justAckedId.value === event.id) justAckedId.value = null; }, 15000);
  } catch (err) {
    const info = parseApiError(err);
    toast.addToast(mapErrorToUserText(info, "Failed to acknowledge alert"), "error");
  } finally {
    ackingIds.value.delete(event.id);
  }
}

function dismissAckBar() {
  justAckedId.value = null;
  justAckedRuleId.value = null;
}

async function handleResolve(event: AlertEvent) {
  resolvingIds.value.add(event.id);
  try {
    await resolveEvent(event.id);
    toast.addToast(`Alert resolved`, "success");
  } catch (err) {
    const info = parseApiError(err);
    toast.addToast(mapErrorToUserText(info, "Failed to resolve alert"), "error");
  } finally {
    resolvingIds.value.delete(event.id);
  }
}

// ── Rules ─────────────────────────────────────────────────────────────────
const deletingConfirmId = ref<number | null>(null);
const deletingId = ref<number | null>(null);
const togglingId = ref<number | null>(null);

async function handleToggleRule(rule: AlertRule) {
  togglingId.value = rule.id;
  try {
    await updateRule(rule.id, { enabled: !rule.enabled });
  } catch (err) {
    const info = parseApiError(err);
    toast.addToast(mapErrorToUserText(info, "Failed to update rule"), "error");
  } finally {
    togglingId.value = null;
  }
}

async function handleDeleteRule(id: number) {
  if (deletingConfirmId.value !== id) {
    deletingConfirmId.value = id;
    return;
  }
  deletingId.value = id;
  deletingConfirmId.value = null;
  try {
    await deleteRule(id);
    toast.addToast("Rule deleted", "success");
  } catch (err) {
    const info = parseApiError(err);
    toast.addToast(mapErrorToUserText(info, "Failed to delete rule"), "error");
  } finally {
    deletingId.value = null;
  }
}

// ── Modal ─────────────────────────────────────────────────────────────────
const modalOpen = ref(false);
const modalMode = ref<"create" | "edit">("create");
const modalError = ref<string | null>(null);
const modalSaving = ref(false);
const editingRule = ref<AlertRule | null>(null);

type RuleFormData = {
  name: string;
  condition_type: string;
  severity: "info" | "warning" | "critical";
  entity_id: string;
  cooldown_seconds: number;
  enabled: boolean;
};

const emptyForm = (): RuleFormData => ({
  name: "",
  condition_type: "device_offline",
  severity: "warning",
  entity_id: "",
  cooldown_seconds: 300,
  enabled: true,
});

const form = ref<RuleFormData>(emptyForm());

const conditionTypeHints: Record<string, string> = {
  device_offline: "Triggers when a device hasn't sent a heartbeat",
  entity_health: "Triggers based on entity health status",
  effect_failure_rate: "Triggers when effect failure rate exceeds threshold",
  event_lag: "Triggers when event processing lag is too high",
  variable_threshold: "Triggers when a variable value crosses a threshold",
};

// ── Variable Threshold fields ─────────────────────────────────────────────
const vtKey = ref("");
const vtOperator = ref<string>("gt");
const vtValue = ref<number>(0);
const vtDeviceUid = ref("");

const OPERATOR_OPTIONS = [
  { value: "gt",  label: "> greater than" },
  { value: "gte", label: "≥ greater or equal" },
  { value: "lt",  label: "< less than" },
  { value: "lte", label: "≤ less or equal" },
  { value: "eq",  label: "= equal" },
  { value: "ne",  label: "≠ not equal" },
];

const OPERATOR_SYMBOLS: Record<string, string> = {
  gt: ">", gte: "≥", lt: "<", lte: "≤", eq: "=", ne: "≠",
};

function formatVarThreshold(cfg: any): string {
  if (!cfg?.variable_key) return "";
  const sym = OPERATOR_SYMBOLS[cfg.threshold_operator] ?? cfg.threshold_operator;
  return `${cfg.variable_key} ${sym} ${cfg.threshold_value}`;
}

function openCreate() {
  modalMode.value = "create";
  editingRule.value = null;
  form.value = emptyForm();
  vtKey.value = ""; vtOperator.value = "gt"; vtValue.value = 0; vtDeviceUid.value = "";
  modalError.value = null;
  modalOpen.value = true;
}

// Auto-open create modal with pre-filled context from Variables or DeviceDetail
watch(() => loading.value, (isLoading) => {
  if (!isLoading && alertRoute.query.create === "true") {
    openCreate();
    if (alertRoute.query.variable_key) {
      form.value.condition_type = "variable_threshold";
      vtKey.value = String(alertRoute.query.variable_key);
    }
    if (alertRoute.query.device_uid) {
      vtDeviceUid.value = String(alertRoute.query.device_uid);
    }
    activeTab.value = "rules";
  }
}, { immediate: true });

function openEdit(rule: AlertRule) {
  modalMode.value = "edit";
  editingRule.value = rule;
  form.value = {
    name: rule.name,
    condition_type: rule.condition_type,
    severity: rule.severity,
    entity_id: rule.entity_id ?? "",
    cooldown_seconds: rule.cooldown_seconds,
    enabled: rule.enabled,
  };
  // Populate variable threshold fields
  if (rule.condition_type === "variable_threshold" && rule.condition_config) {
    vtKey.value = rule.condition_config.variable_key ?? "";
    vtOperator.value = rule.condition_config.threshold_operator ?? "gt";
    vtValue.value = rule.condition_config.threshold_value ?? 0;
    vtDeviceUid.value = rule.condition_config.device_uid ?? "";
  }
  modalError.value = null;
  modalOpen.value = true;
}

function closeModal() {
  modalOpen.value = false;
  modalError.value = null;
}

function onModalKeydown(e: KeyboardEvent) {
  if (e.key === "Escape") closeModal();
}

async function handleSaveRule() {
  if (!form.value.name.trim()) {
    modalError.value = "Name is required.";
    return;
  }
  modalSaving.value = true;
  modalError.value = null;
  // Build condition_config based on condition_type
  let condCfg: Record<string, unknown> = {};
  if (form.value.condition_type === "variable_threshold") {
    if (!vtKey.value.trim()) { modalError.value = "Variable key is required."; modalSaving.value = false; return; }
    condCfg = {
      variable_key: vtKey.value.trim(),
      threshold_operator: vtOperator.value,
      threshold_value: Number(vtValue.value),
      ...(vtDeviceUid.value.trim() ? { device_uid: vtDeviceUid.value.trim() } : {}),
    };
  }

  const payload = {
    name: form.value.name.trim(),
    condition_type: form.value.condition_type,
    severity: form.value.severity,
    entity_id: form.value.entity_id.trim() || null,
    cooldown_seconds: Number(form.value.cooldown_seconds),
    enabled: form.value.enabled,
    condition_config: condCfg,
  };
  try {
    if (modalMode.value === "create") {
      await createRule(payload);
      toast.addToast("Rule created", "success");
    } else if (editingRule.value) {
      await updateRule(editingRule.value.id, payload);
      toast.addToast("Rule updated", "success");
    }
    closeModal();
  } catch (err) {
    const info = parseApiError(err);
    modalError.value = mapErrorToUserText(info, "Failed to save rule");
  } finally {
    modalSaving.value = false;
  }
}

// ── Severity styles ────────────────────────────────────────────────────────
const severityClass: Record<string, string> = {
  critical: "bg-[var(--status-bad-bg)] text-[var(--status-bad)]",
  warning: "bg-[var(--status-warn-bg)] text-[var(--status-warn)]",
  info: "bg-[var(--status-info-bg)] text-[var(--status-info)]",
};

const statusClass: Record<string, string> = {
  firing: "bg-[var(--status-bad-bg)] text-[var(--status-bad)]",
  acknowledged: "bg-[var(--status-warn-bg)] text-[var(--status-warn)]",
  resolved: "bg-[var(--status-ok-bg)] text-[var(--status-ok)]",
};
</script>

<template>
  <div class="space-y-4">
    <!-- No permission -->
    <div
      v-if="caps.status === 'ready' && !hasCap('alerts.read')"
      class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-8 text-center"
    >
      <p class="text-[var(--text-muted)]">You don't have permission to view alerts.</p>
    </div>

    <template v-else>
      <!-- Page header -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-xl font-semibold text-[var(--text-primary)]">Alerts</h1>
          <p class="text-sm text-[var(--text-muted)] mt-1">Monitor and manage alert rules and events</p>
        </div>
        <div class="flex items-center gap-2">
        <span v-if="refreshing" class="text-xs text-[var(--text-muted)] animate-pulse">refreshing…</span>
        <button
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--border)] text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:border-[var(--border-hover)] bg-[var(--bg-raised)] transition-colors"
          :disabled="isRefreshing"
          @click="handleRefresh"
        >
          <svg class="h-3.5 w-3.5" :class="isRefreshing ? 'animate-spin' : ''" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
          </svg>
          Refresh
        </button>
        </div>
      </div>

      <!-- Error banner -->
      <div
        v-if="error"
        class="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400"
      >
        {{ error }}
      </div>

      <!-- Tabs -->
      <div class="flex gap-1 border-b border-[var(--border)]">
        <button
          v-for="tab in [{ key: 'events', label: 'Events' }, { key: 'rules', label: 'Rules' }]"
          :key="tab.key"
          :class="[
            'px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px',
            activeTab === tab.key
              ? 'border-[var(--primary)] text-[var(--primary)]'
              : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)]',
          ]"
          @click="activeTab = tab.key as 'events' | 'rules'"
        >
          {{ tab.label }}
          <span
            v-if="tab.key === 'events' && events.filter(e => e.status === 'firing').length > 0"
            class="ml-1.5 inline-flex items-center justify-center rounded-full bg-red-500/20 text-red-400 text-[10px] font-mono px-1.5 min-w-[18px]"
          >
            {{ events.filter(e => e.status === "firing").length }}
          </span>
        </button>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading" class="space-y-2">
        <div v-for="i in 4" :key="i" class="h-16 rounded-xl bg-[var(--bg-surface)] animate-pulse" />
      </div>

      <!-- EVENTS TAB -->
      <template v-else-if="activeTab === 'events'">
        <!-- Filter bar -->
        <div class="flex flex-wrap items-center gap-2">
          <!-- Status pills -->
          <div class="flex gap-1">
            <button
              v-for="s in ['all', 'firing', 'acknowledged', 'resolved']"
              :key="s"
              :class="[
                'px-3 py-1 rounded-full text-xs font-medium transition-colors',
                statusFilter === s
                  ? 'bg-[var(--primary)]/20 text-[var(--primary)]'
                  : 'bg-[var(--bg-raised)] text-[var(--text-muted)] hover:text-[var(--text-primary)]',
              ]"
              @click="statusFilter = s as typeof statusFilter"
            >
              {{ s === 'all' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1) }}
            </button>
          </div>

          <!-- Rule dropdown -->
          <select
            v-model="ruleFilter"
            class="ml-auto text-xs px-2 py-1 rounded-lg border border-[var(--border)] bg-[var(--bg-raised)] text-[var(--text-muted)] focus:outline-none focus:border-[var(--primary)]"
          >
            <option value="all">All Rules</option>
            <option v-for="r in rules" :key="r.id" :value="r.id">{{ r.name }}</option>
          </select>

          <!-- Contextual: Create Automation from alerts -->
          <button
            class="flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium text-[var(--primary)] hover:bg-[var(--primary)]/10 transition-colors"
            title="Create automation to handle these alerts"
            @click="$router.push({ path: '/automations', query: { create: 'true' } })"
          >
            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
            </svg>
            Create Automation
          </button>
        </div>

        <!-- Event list -->
        <UEmpty
          v-if="filteredEvents.length === 0"
          title="No alert events"
          description="Alert events appear here when a rule is triggered. They are generated automatically when conditions are met."
          icon="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
        />

        <div v-else class="space-y-2">
          <div
            v-for="ev in filteredEvents"
            :key="ev.id"
            class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 flex items-start gap-3"
          >
            <!-- Severity badge -->
            <span
              :class="['shrink-0 mt-0.5 text-[10px] font-mono uppercase px-2 py-0.5 rounded', severityClass[ev.status === 'firing' ? (rules.find(r => r.id === ev.rule_id)?.severity ?? 'info') : (rules.find(r => r.id === ev.rule_id)?.severity ?? 'info')]]"
            >
              {{ rules.find(r => r.id === ev.rule_id)?.severity ?? "info" }}
            </span>

            <!-- Main content -->
            <div class="flex-1 min-w-0 space-y-1">
              <div class="flex items-center gap-2 flex-wrap">
                <!-- Status badge -->
                <span
                  :class="['text-[10px] font-mono uppercase px-2 py-0.5 rounded', statusClass[ev.status], ev.status === 'firing' ? 'animate-pulse' : '']"
                >
                  {{ ev.status }}
                </span>
                <span class="text-xs text-[var(--text-muted)]">{{ ruleNameFor(ev.rule_id) }}</span>
                <span class="text-xs text-[var(--text-muted)] ml-auto">{{ relativeTime(ev.triggered_at) }}</span>
              </div>
              <p class="text-sm text-[var(--text-primary)] line-clamp-2">{{ ev.message }}</p>
              <!-- Clickable device link -->
              <router-link
                v-if="ev.device_id"
                :to="`/devices/${ev.device_id}`"
                class="inline-flex items-center gap-1 text-xs text-[var(--primary)] hover:underline mt-0.5"
              >
                <svg class="h-3 w-3" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z" />
                </svg>
                Device #{{ ev.device_id }}
              </router-link>
            </div>

            <!-- Actions -->
            <div class="shrink-0 flex gap-1.5">
              <button
                v-if="ev.status === 'firing'"
                :disabled="ackingIds.has(ev.id)"
                class="px-2.5 py-1 rounded-lg text-xs font-medium bg-yellow-500/10 text-yellow-400 hover:bg-yellow-500/20 disabled:opacity-50 transition-colors"
                @click="handleAck(ev)"
              >
                {{ ackingIds.has(ev.id) ? "…" : "Ack" }}
              </button>
              <button
                v-if="ev.status !== 'resolved'"
                :disabled="resolvingIds.has(ev.id)"
                class="px-2.5 py-1 rounded-lg text-xs font-medium bg-green-500/10 text-green-400 hover:bg-green-500/20 disabled:opacity-50 transition-colors"
                @click="handleResolve(ev)"
              >
                {{ resolvingIds.has(ev.id) ? "…" : "Resolve" }}
              </button>
            </div>
          </div>

          <!-- Post-Acknowledge Action Bar -->
          <div
            v-if="justAckedId === ev.id"
            class="flex items-center gap-3 px-4 py-2 mt-1 rounded-lg border border-[var(--primary)]/20 bg-[var(--primary)]/5 text-xs"
          >
            <span class="text-[var(--text-muted)]">Alert acknowledged.</span>
            <router-link
              v-if="ev.device_uid || ev.device_id"
              :to="`/devices/${ev.device_uid || ev.device_id}`"
              class="text-[var(--primary)] hover:underline"
            >Zum Device</router-link>
            <button
              class="text-[var(--primary)] hover:underline"
              @click="$router.push({ path: '/automations', query: { create: 'true', variable_key: ev.variable_key || '' } })"
            >Create Automation</button>
            <button
              class="text-[var(--text-muted)] hover:text-[var(--text-primary)] ml-auto"
              @click="dismissAckBar"
            >
              <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
        </div>
      </template>

      <!-- RULES TAB -->
      <template v-else-if="activeTab === 'rules'">
        <!-- Toolbar -->
        <div class="flex justify-end">
          <button
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)]/10 text-[var(--primary)] hover:bg-[var(--primary)]/20 transition-colors"
            @click="openCreate"
          >
            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            New Rule
          </button>
        </div>

        <!-- Enhanced empty state -->
        <div
          v-if="rules.length === 0"
          class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-8 py-12 text-center"
        >
          <div class="flex flex-col items-center gap-5">
            <div class="h-14 w-14 rounded-xl bg-[var(--bg-raised)] flex items-center justify-center">
              <svg class="h-7 w-7 text-[var(--status-warn)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
              </svg>
            </div>
            <div class="space-y-1 max-w-sm">
              <h3 class="text-base font-semibold text-[var(--text-primary)]">Get notified when something happens</h3>
              <p class="text-sm text-[var(--text-muted)]">Alert rules fire when devices go offline, variables cross thresholds, or automation errors occur.</p>
            </div>
            <div class="flex flex-col sm:flex-row gap-2.5 items-center">
              <button
                class="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-[var(--primary)]/10 text-[var(--primary)] hover:bg-[var(--primary)]/20 transition-colors"
                @click="openCreate"
              >
                <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                Create Alert Rule
              </button>
              <span class="text-xs text-[var(--text-muted)]">or go to a variable / device to create a rule in context</span>
            </div>
          </div>
        </div>

        <div v-else class="space-y-2">
          <div
            v-for="rule in rules"
            :key="rule.id"
            class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 flex items-center gap-3"
          >
            <!-- Name & badges -->
            <div class="flex-1 min-w-0 space-y-1">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-sm font-medium text-[var(--text-primary)] truncate">{{ rule.name }}</span>
                <span class="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-[var(--primary)]/15 text-[var(--primary)]">
                  {{ rule.condition_type }}
                </span>
                <span :class="['text-[10px] font-mono uppercase px-2 py-0.5 rounded', severityClass[rule.severity]]">
                  {{ rule.severity }}
                </span>
              </div>
              <p v-if="rule.condition_type === 'variable_threshold' && rule.condition_config" class="text-xs text-[var(--primary)] font-mono">
                {{ formatVarThreshold(rule.condition_config) }}
              </p>
              <p class="text-xs text-[var(--text-muted)]">Cooldown: {{ rule.cooldown_seconds }}s</p>
            </div>

            <!-- Toggle -->
            <button
              :title="rule.enabled ? 'Disable rule' : 'Enable rule'"
              :disabled="togglingId === rule.id"
              :class="[
                'relative shrink-0 h-5 w-9 rounded-full transition-colors focus:outline-none disabled:opacity-50',
                rule.enabled ? 'bg-[var(--primary)]/70' : 'bg-[var(--bg-raised)]',
              ]"
              @click="handleToggleRule(rule)"
            >
              <span
                :class="[
                  'absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform',
                  rule.enabled ? 'translate-x-4' : 'translate-x-0.5',
                ]"
              />
            </button>

            <!-- Edit -->
            <button
              class="shrink-0 p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
              title="Edit rule"
              @click="openEdit(rule)"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
              </svg>
            </button>

            <!-- Delete (two-step) -->
            <button
              :disabled="deletingId === rule.id"
              :class="[
                'shrink-0 px-2.5 py-1 rounded-lg text-xs font-medium transition-colors disabled:opacity-50',
                deletingConfirmId === rule.id
                  ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                  : 'text-[var(--text-muted)] hover:text-red-400 hover:bg-red-500/10',
              ]"
              @click="handleDeleteRule(rule.id)"
            >
              {{ deletingId === rule.id ? '…' : deletingConfirmId === rule.id ? 'Confirm?' : 'Delete' }}
            </button>
          </div>
        </div>
      </template>
    </template>

    <!-- Create/Edit Modal -->
    <Teleport to="body">
      <div
        v-if="modalOpen"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
        @keydown="onModalKeydown"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/60" @click="closeModal" />

        <!-- Modal card -->
        <div class="relative z-10 w-full max-w-md rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] shadow-2xl p-6 space-y-4">
          <h3 class="text-base font-semibold text-[var(--text-primary)]">
            {{ modalMode === 'create' ? 'New Alert Rule' : 'Edit Alert Rule' }}
          </h3>

          <!-- Name -->
          <div class="space-y-1">
            <label class="text-xs font-medium text-[var(--text-muted)]">Name <span class="text-red-400">*</span></label>
            <input
              v-model="form.name"
              type="text"
              placeholder="Rule name"
              class="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--primary)] transition-colors"
            />
          </div>

          <!-- Condition Type -->
          <div class="space-y-1">
            <label class="text-xs font-medium text-[var(--text-muted)]">Condition Type</label>
            <select
              v-model="form.condition_type"
              class="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--primary)] transition-colors"
            >
              <option value="device_offline">device_offline</option>
              <option value="entity_health">entity_health</option>
              <option value="effect_failure_rate">effect_failure_rate</option>
              <option value="event_lag">event_lag</option>
              <option value="variable_threshold">variable_threshold</option>
            </select>
            <p v-if="conditionTypeHints[form.condition_type]" class="text-xs text-[var(--text-muted)]">
              {{ conditionTypeHints[form.condition_type] }}
            </p>
          </div>

          <!-- Variable Threshold config (only when condition_type === variable_threshold) -->
          <template v-if="form.condition_type === 'variable_threshold'">
            <UEntitySelect v-model="vtKey" entity-type="variable" label="Variable Key" />
            <div class="grid grid-cols-2 gap-3">
              <div class="space-y-1">
                <label class="text-xs font-medium text-[var(--text-muted)]">Operator</label>
                <select
                  v-model="vtOperator"
                  class="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--primary)] transition-colors"
                >
                  <option v-for="op in OPERATOR_OPTIONS" :key="op.value" :value="op.value">{{ op.label }}</option>
                </select>
              </div>
              <div class="space-y-1">
                <label class="text-xs font-medium text-[var(--text-muted)]">Threshold Value</label>
                <input
                  v-model.number="vtValue"
                  type="number"
                  step="any"
                  class="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--primary)] transition-colors"
                />
              </div>
            </div>
            <UEntitySelect v-model="vtDeviceUid" entity-type="device" label="Device UID" placeholder="Leave empty for global variable" :optional="true" />
          </template>

          <!-- Severity -->
          <div class="space-y-1">
            <label class="text-xs font-medium text-[var(--text-muted)]">Severity</label>
            <select
              v-model="form.severity"
              class="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--primary)] transition-colors"
            >
              <option value="info">info</option>
              <option value="warning">warning</option>
              <option value="critical">critical</option>
            </select>
          </div>

          <!-- Entity ID -->
          <UEntitySelect v-model="form.entity_id" entity-type="entity" label="Entity ID" :optional="true" />

          <!-- Cooldown -->
          <div class="space-y-1">
            <label class="text-xs font-medium text-[var(--text-muted)]">Cooldown (seconds)</label>
            <input
              v-model.number="form.cooldown_seconds"
              type="number"
              min="0"
              class="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--primary)] transition-colors"
            />
          </div>

          <!-- Enabled -->
          <div class="flex items-center gap-2">
            <input
              id="modal-enabled"
              v-model="form.enabled"
              type="checkbox"
              class="h-4 w-4 rounded border-[var(--border)] accent-[var(--primary)]"
            />
            <label for="modal-enabled" class="text-sm text-[var(--text-primary)]">Enabled</label>
          </div>

          <!-- Inline error -->
          <p v-if="modalError" class="text-xs text-red-400">{{ modalError }}</p>

          <!-- Buttons -->
          <div class="flex justify-end gap-2 pt-2">
            <button
              class="px-4 py-2 rounded-lg text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
              @click="closeModal"
            >
              Cancel
            </button>
            <button
              :disabled="modalSaving"
              class="px-4 py-2 rounded-lg text-sm font-medium bg-[var(--primary)]/10 text-[var(--primary)] hover:bg-[var(--primary)]/20 disabled:opacity-50 transition-colors"
              @click="handleSaveRule"
            >
              {{ modalSaving ? 'Saving…' : 'Save' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
