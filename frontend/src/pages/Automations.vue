<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import {
  listAutomations,
  createAutomation,
  updateAutomation,
  deleteAutomation,
  testAutomation,
  getAutomationHistory,
  type AutomationRuleOut,
  type AutomationRuleCreate,
  type AutomationFireLogOut,
} from "../lib/automations";
import { useToastStore } from "../stores/toast";
import { parseApiError, mapErrorToUserText } from "../lib/errors";
import UEntitySelect from "../components/ui/UEntitySelect.vue";

const route = useRoute();
const { t } = useI18n();
const toast = useToastStore();

// ── State ─────────────────────────────────────────────────────────────────────

const rules = ref<AutomationRuleOut[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const refreshing = ref(false);

// ── Load ──────────────────────────────────────────────────────────────────────

async function reload() {
  refreshing.value = true;
  error.value = null;
  try {
    rules.value = await listAutomations();
  } catch (err) {
    const info = parseApiError(err);
    error.value = mapErrorToUserText(info, "Failed to load automation rules");
  } finally {
    loading.value = false;
    refreshing.value = false;
  }
}

onMounted(async () => {
  await reload();
  // Auto-open create modal with pre-filled context from Variables or DeviceDetail
  if (route.query.create === "true") {
    openCreate();
    if (route.query.variable_key) {
      formTriggerType.value = "variable_threshold";
      trigVarKey.value = String(route.query.variable_key);
    }
    if (route.query.device_uid) {
      trigDeviceUid.value = String(route.query.device_uid);
    }
  }
});

// ── Delete ────────────────────────────────────────────────────────────────────

const deletingConfirmId = ref<number | null>(null);
const deletingId = ref<number | null>(null);

async function handleDelete(id: number) {
  if (deletingConfirmId.value !== id) {
    deletingConfirmId.value = id;
    return;
  }
  deletingId.value = id;
  deletingConfirmId.value = null;
  try {
    await deleteAutomation(id);
    rules.value = rules.value.filter((r) => r.id !== id);
    toast.addToast(t('toast.deleted', { item: 'Rule' }), "success");
  } catch (err) {
    const info = parseApiError(err);
    toast.addToast(mapErrorToUserText(info, "Failed to delete rule"), "error");
  } finally {
    deletingId.value = null;
  }
}

// ── Toggle ────────────────────────────────────────────────────────────────────

const togglingId = ref<number | null>(null);

async function handleToggle(rule: AutomationRuleOut) {
  togglingId.value = rule.id;
  try {
    const updated = await updateAutomation(rule.id, { enabled: !rule.enabled });
    const idx = rules.value.findIndex((r) => r.id === rule.id);
    if (idx !== -1) rules.value[idx] = updated;
  } catch (err) {
    const info = parseApiError(err);
    toast.addToast(mapErrorToUserText(info, "Failed to update rule"), "error");
  } finally {
    togglingId.value = null;
  }
}

// ── Test Fire ─────────────────────────────────────────────────────────────────

const testingId = ref<number | null>(null);
const testConfirmId = ref<number | null>(null);

async function handleTest(id: number) {
  if (testConfirmId.value !== id) {
    testConfirmId.value = id;
    return;
  }
  testConfirmId.value = null;
  testingId.value = id;
  try {
    const result = await testAutomation(id);
    if (result.success) {
      toast.addToast("Test fire successful", "success");
    } else {
      toast.addToast(`Test fire failed: ${result.message}`, "error");
    }
  } catch (err) {
    const info = parseApiError(err);
    toast.addToast(mapErrorToUserText(info, "Test fire failed"), "error");
  } finally {
    testingId.value = null;
  }
}

// ── History Modal ─────────────────────────────────────────────────────────────

const historyOpen = ref(false);
const historyRuleName = ref("");
const historyEntries = ref<AutomationFireLogOut[]>([]);
const historyLoading = ref(false);

async function openHistory(rule: AutomationRuleOut) {
  historyRuleName.value = rule.name;
  historyOpen.value = true;
  historyLoading.value = true;
  try {
    historyEntries.value = await getAutomationHistory(rule.id);
  } catch {
    historyEntries.value = [];
  } finally {
    historyLoading.value = false;
  }
}

function closeHistory() {
  historyOpen.value = false;
}

// ── Create/Edit Modal ─────────────────────────────────────────────────────────

const modalOpen = ref(false);
const modalMode = ref<"create" | "edit">("create");
const modalSaving = ref(false);
const modalError = ref<string | null>(null);
const editingId = ref<number | null>(null);

// Form state
const formName = ref("");
const formDescription = ref("");
const formEnabled = ref(true);
const formTriggerType = ref("variable_threshold");
const formActionType = ref("create_alert_event");
const formCooldown = ref(300);

// Trigger-specific fields
const trigVarKey = ref("");
const trigOperator = ref("gt");
const trigValue = ref(0);
const trigDeviceUid = ref("");
// Geofence
const trigGeoType = ref<"circle" | "polygon">("circle");
const trigGeoExitEnter = ref<"exit" | "enter">("exit");
const trigGeoLat = ref(0);
const trigGeoLng = ref(0);
const trigGeoRadius = ref(500);
const trigGeoPolygon = ref("[[48.137, 11.576], [48.140, 11.580], [48.135, 11.582]]");
// Device offline / telemetry
const trigEventType = ref("");

// Action-specific fields
const actVarKey = ref("");
const actVarValue = ref('""');
const actVarScope = ref("global");
const actVarDeviceUid = ref("");
const actWebhookUrl = ref("");
const actWebhookMethod = ref("POST");
const actWebhookHeaders = ref("{}");
const actWebhookPayload = ref("{}");
const actAlertSeverity = ref("warning");
const actAlertMessage = ref("");
const actEventType = ref("");
const actEventPayload = ref("{}");

const TRIGGER_TYPES = [
  { value: "variable_threshold", label: "Variable Threshold", desc: "When a variable exceeds or drops below a value", icon: "M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" },
  { value: "variable_geofence", label: "Variable Geofence", desc: "When a GPS variable leaves or enters a zone", icon: "M15 10.5a3 3 0 11-6 0 3 3 0 016 0z M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" },
  { value: "device_offline", label: "Device Offline", desc: "When a device goes offline", icon: "M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z" },
  { value: "telemetry_received", label: "Telemetry Received", desc: "When telemetry data arrives", icon: "M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" },
  { value: "variable_change", label: "Variable Change", desc: "When any variable value changes", icon: "M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" },
  { value: "device_online", label: "Device Online", desc: "When a device comes back online", icon: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" },
  { value: "schedule", label: "Schedule (Cron)", desc: "Run on a time-based schedule", icon: "M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" },
];

const ACTION_TYPES = [
  { value: "set_variable", label: "Set Variable", desc: "Update a variable value", icon: "M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z" },
  { value: "call_webhook", label: "Call Webhook", desc: "Send HTTP request to external URL", icon: "M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" },
  { value: "create_alert_event", label: "Create Alert", desc: "Generate an alert event", icon: "M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" },
  { value: "emit_system_event", label: "Emit System Event", desc: "Broadcast a system event", icon: "M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-13.5 0v-1.5m13.5 1.5v-1.5m0 0a3 3 0 00-3-3H7.5a3 3 0 00-3 3m13.5 0v-6.75a3 3 0 00-3-3H7.5a3 3 0 00-3 3v6.75" },
  { value: "send_notification", label: "Send Notification", desc: "Create an in-app notification", icon: "M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" },
  { value: "log_to_audit", label: "Log to Audit", desc: "Write an entry to the audit log", icon: "M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" },
  { value: "send_email", label: "Send Email", desc: "Send an email using a template", icon: "M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" },
];

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

function triggerSummary(rule: AutomationRuleOut): string {
  const cfg = rule.trigger_config;
  if (rule.trigger_type === "variable_threshold") {
    const sym = OPERATOR_SYMBOLS[cfg.operator as string] ?? cfg.operator;
    return `${cfg.variable_key} ${sym} ${cfg.value}`;
  }
  if (rule.trigger_type === "variable_geofence") {
    const t = cfg.geofence_type === "polygon" ? "polygon" : `circle (${cfg.radius_m ?? 500}m)`;
    return `${cfg.variable_key} ${cfg.exit_or_enter ?? "exit"} ${t}`;
  }
  if (rule.trigger_type === "device_offline") {
    return cfg.device_uid ? `device: ${cfg.device_uid}` : "any device";
  }
  if (rule.trigger_type === "telemetry_received") {
    return cfg.device_uid ? `device: ${cfg.device_uid}` : "any telemetry";
  }
  return rule.trigger_type;
}

function actionSummary(rule: AutomationRuleOut): string {
  const cfg = rule.action_config;
  if (rule.action_type === "set_variable") return `set ${cfg.variable_key} = ${JSON.stringify(cfg.value)}`;
  if (rule.action_type === "call_webhook") return `${cfg.method ?? "POST"} → ${String(cfg.url ?? "").slice(0, 30)}`;
  if (rule.action_type === "create_alert_event") return `alert: ${String(cfg.message ?? "").slice(0, 40)}`;
  if (rule.action_type === "emit_system_event") return `event: ${cfg.event_type ?? ""}`;
  return rule.action_type;
}

function relativeTime(dt: string | null): string {
  if (!dt) return "never";
  const diff = Date.now() - new Date(dt).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function resetForm() {
  formName.value = "";
  formDescription.value = "";
  formEnabled.value = true;
  formTriggerType.value = "variable_threshold";
  formActionType.value = "create_alert_event";
  formCooldown.value = 300;
  trigVarKey.value = "";
  trigOperator.value = "gt";
  trigValue.value = 0;
  trigDeviceUid.value = "";
  trigGeoType.value = "circle";
  trigGeoExitEnter.value = "exit";
  trigGeoLat.value = 0;
  trigGeoLng.value = 0;
  trigGeoRadius.value = 500;
  trigGeoPolygon.value = "[[48.137, 11.576], [48.140, 11.580], [48.135, 11.582]]";
  trigEventType.value = "";
  actVarKey.value = "";
  actVarValue.value = '""';
  actVarScope.value = "global";
  actVarDeviceUid.value = "";
  actWebhookUrl.value = "";
  actWebhookMethod.value = "POST";
  actWebhookHeaders.value = "{}";
  actWebhookPayload.value = "{}";
  actAlertSeverity.value = "warning";
  actAlertMessage.value = "";
  actEventType.value = "";
  actEventPayload.value = "{}";
}

function openCreate() {
  modalMode.value = "create";
  editingId.value = null;
  resetForm();
  modalError.value = null;
  modalOpen.value = true;
}

// ── Quick-start templates ─────────────────────────────────────────────────────
interface AutomationTemplate {
  name: string;
  description: string;
  icon: string;
  color: string;
  triggerType: string;
  actionType: string;
  prefill?: () => void;
}

const quickTemplates: AutomationTemplate[] = [
  {
    name: "Alert when variable exceeds threshold",
    description: "Fires when a numeric variable goes above a set value",
    icon: "M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z",
    color: "var(--primary)",
    triggerType: "variable_threshold",
    actionType: "create_alert_event",
    prefill: () => {
      trigOperator.value = "gt";
      trigValue.value = 100;
    },
  },
  {
    name: "Notify when device goes offline",
    description: "Sends a webhook when a device becomes unreachable",
    icon: "M8.288 15.038a5.25 5.25 0 017.424 0M5.106 11.856c3.807-3.808 9.98-3.808 13.788 0M1.924 8.674c5.565-5.565 14.587-5.565 20.152 0M12.53 18.22l-.53.53-.53-.53a.75.75 0 011.06 0z",
    color: "var(--status-bad)",
    triggerType: "device_offline",
    actionType: "send_webhook",
    prefill: () => {},
  },
  {
    name: "Set variable on event",
    description: "Updates a variable value when a custom event fires",
    icon: "M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h1.5C5.496 19.5 6 18.996 6 18.375m-3.75.125v-1.5",
    color: "var(--accent)",
    triggerType: "event_received",
    actionType: "set_variable",
    prefill: () => {},
  },
];

function openFromTemplate(tpl: AutomationTemplate) {
  modalMode.value = "create";
  editingId.value = null;
  resetForm();
  formName.value = tpl.name;
  formTriggerType.value = tpl.triggerType;
  formActionType.value = tpl.actionType;
  if (tpl.prefill) tpl.prefill();
  modalError.value = null;
  modalOpen.value = true;
}

function openEdit(rule: AutomationRuleOut) {
  modalMode.value = "edit";
  editingId.value = rule.id;
  resetForm();
  formName.value = rule.name;
  formDescription.value = rule.description ?? "";
  formEnabled.value = rule.enabled;
  formTriggerType.value = rule.trigger_type;
  formActionType.value = rule.action_type;
  formCooldown.value = rule.cooldown_seconds;

  // Populate trigger config
  const tc = rule.trigger_config;
  if (rule.trigger_type === "variable_threshold") {
    trigVarKey.value = String(tc.variable_key ?? "");
    trigOperator.value = String(tc.operator ?? "gt");
    trigValue.value = Number(tc.value ?? 0);
    trigDeviceUid.value = String(tc.device_uid ?? "");
  } else if (rule.trigger_type === "variable_geofence") {
    trigVarKey.value = String(tc.variable_key ?? "");
    trigDeviceUid.value = String(tc.device_uid ?? "");
    trigGeoType.value = (tc.geofence_type as "circle" | "polygon") ?? "circle";
    trigGeoExitEnter.value = (tc.exit_or_enter as "exit" | "enter") ?? "exit";
    if (tc.center && typeof tc.center === "object") {
      const c = tc.center as Record<string, number>;
      trigGeoLat.value = c.lat ?? 0;
      trigGeoLng.value = c.lng ?? 0;
    }
    trigGeoRadius.value = Number(tc.radius_m ?? 500);
    if (tc.polygon) trigGeoPolygon.value = JSON.stringify(tc.polygon);
  } else if (rule.trigger_type === "device_offline") {
    trigDeviceUid.value = String(tc.device_uid ?? "");
  } else if (rule.trigger_type === "telemetry_received") {
    trigDeviceUid.value = String(tc.device_uid ?? "");
    trigEventType.value = String(tc.event_type ?? "");
  }

  // Populate action config
  const ac = rule.action_config;
  if (rule.action_type === "set_variable") {
    actVarKey.value = String(ac.variable_key ?? "");
    actVarValue.value = JSON.stringify(ac.value ?? "");
    actVarScope.value = String(ac.scope ?? "global");
    actVarDeviceUid.value = String(ac.device_uid ?? "");
  } else if (rule.action_type === "call_webhook") {
    actWebhookUrl.value = String(ac.url ?? "");
    actWebhookMethod.value = String(ac.method ?? "POST");
    actWebhookHeaders.value = JSON.stringify(ac.headers ?? {});
    actWebhookPayload.value = JSON.stringify(ac.payload_template ?? {});
  } else if (rule.action_type === "create_alert_event") {
    actAlertSeverity.value = String(ac.severity ?? "warning");
    actAlertMessage.value = String(ac.message ?? "");
  } else if (rule.action_type === "emit_system_event") {
    actEventType.value = String(ac.event_type ?? "");
    actEventPayload.value = JSON.stringify(ac.payload_extra ?? {});
  }

  modalError.value = null;
  modalOpen.value = true;
}

function duplicateRule(rule: AutomationRuleOut) {
  openEdit(rule);
  modalMode.value = "create";
  editingId.value = null;
  formName.value = `${rule.name} (Copy)`;
}

function closeModal() {
  modalOpen.value = false;
  modalError.value = null;
}

function buildTriggerConfig(): Record<string, unknown> {
  if (formTriggerType.value === "variable_threshold") {
    const cfg: Record<string, unknown> = {
      variable_key: trigVarKey.value.trim(),
      operator: trigOperator.value,
      value: Number(trigValue.value),
    };
    if (trigDeviceUid.value.trim()) cfg.device_uid = trigDeviceUid.value.trim();
    return cfg;
  }
  if (formTriggerType.value === "variable_geofence") {
    const cfg: Record<string, unknown> = {
      variable_key: trigVarKey.value.trim(),
      geofence_type: trigGeoType.value,
      exit_or_enter: trigGeoExitEnter.value,
    };
    if (trigDeviceUid.value.trim()) cfg.device_uid = trigDeviceUid.value.trim();
    if (trigGeoType.value === "circle") {
      cfg.center = { lat: Number(trigGeoLat.value), lng: Number(trigGeoLng.value) };
      cfg.radius_m = Number(trigGeoRadius.value);
    } else {
      try { cfg.polygon = JSON.parse(trigGeoPolygon.value); } catch { /* ignore */ }
    }
    return cfg;
  }
  if (formTriggerType.value === "device_offline") {
    const cfg: Record<string, unknown> = {};
    if (trigDeviceUid.value.trim()) cfg.device_uid = trigDeviceUid.value.trim();
    return cfg;
  }
  if (formTriggerType.value === "telemetry_received") {
    const cfg: Record<string, unknown> = {};
    if (trigDeviceUid.value.trim()) cfg.device_uid = trigDeviceUid.value.trim();
    if (trigEventType.value.trim()) cfg.event_type = trigEventType.value.trim();
    return cfg;
  }
  return {};
}

function buildActionConfig(): Record<string, unknown> {
  if (formActionType.value === "set_variable") {
    let val: unknown = actVarValue.value;
    try { val = JSON.parse(actVarValue.value); } catch { /* keep as string */ }
    const cfg: Record<string, unknown> = {
      variable_key: actVarKey.value.trim(),
      value: val,
      scope: actVarScope.value,
    };
    if (actVarDeviceUid.value.trim()) cfg.device_uid = actVarDeviceUid.value.trim();
    return cfg;
  }
  if (formActionType.value === "call_webhook") {
    let headers: unknown = {};
    let payload: unknown = {};
    try { headers = JSON.parse(actWebhookHeaders.value); } catch { /* ignore */ }
    try { payload = JSON.parse(actWebhookPayload.value); } catch { /* ignore */ }
    return {
      url: actWebhookUrl.value.trim(),
      method: actWebhookMethod.value,
      headers,
      payload_template: payload,
    };
  }
  if (formActionType.value === "create_alert_event") {
    return {
      severity: actAlertSeverity.value,
      message: actAlertMessage.value.trim() || `Automation rule fired`,
    };
  }
  if (formActionType.value === "emit_system_event") {
    let extra: unknown = {};
    try { extra = JSON.parse(actEventPayload.value); } catch { /* ignore */ }
    return {
      event_type: actEventType.value.trim() || "automation.fired",
      payload_extra: extra,
    };
  }
  return {};
}

async function handleSave() {
  if (!formName.value.trim()) {
    modalError.value = "Name is required.";
    return;
  }
  if (formTriggerType.value === "variable_threshold" && !trigVarKey.value.trim()) {
    modalError.value = "Variable key is required for Variable Threshold trigger.";
    return;
  }
  if (formTriggerType.value === "variable_geofence" && !trigVarKey.value.trim()) {
    modalError.value = "Variable key is required for Geofence trigger.";
    return;
  }
  if (formActionType.value === "call_webhook" && !actWebhookUrl.value.trim()) {
    modalError.value = "URL is required for Call Webhook action.";
    return;
  }

  modalSaving.value = true;
  modalError.value = null;

  const payload: AutomationRuleCreate = {
    name: formName.value.trim(),
    description: formDescription.value.trim() || null,
    enabled: formEnabled.value,
    trigger_type: formTriggerType.value,
    trigger_config: buildTriggerConfig(),
    action_type: formActionType.value,
    action_config: buildActionConfig(),
    cooldown_seconds: Number(formCooldown.value),
  };

  try {
    if (modalMode.value === "create") {
      const created = await createAutomation(payload);
      rules.value.unshift(created);
      toast.addToast("Automation rule created", "success");
    } else if (editingId.value !== null) {
      const updated = await updateAutomation(editingId.value, payload);
      const idx = rules.value.findIndex((r) => r.id === editingId.value);
      if (idx !== -1) rules.value[idx] = updated;
      toast.addToast("Automation rule updated", "success");
    }
    closeModal();
  } catch (err) {
    const info = parseApiError(err);
    modalError.value = mapErrorToUserText(info, "Failed to save rule");
  } finally {
    modalSaving.value = false;
  }
}

const triggerTypeLabel = computed(() => TRIGGER_TYPES.find((t) => t.value === formTriggerType.value)?.label ?? "");
const actionTypeLabel = computed(() => ACTION_TYPES.find((t) => t.value === formActionType.value)?.label ?? "");

const inputClass = "w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--primary)] transition-colors";
const labelClass = "text-xs font-medium text-[var(--text-muted)]";

// Compact card expansion
const expandedRuleId = ref<number | null>(null);
function toggleRuleExpand(id: number) {
  expandedRuleId.value = expandedRuleId.value === id ? null : id;
}
</script>

<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-xl font-semibold text-[var(--text-primary)]">{{ t('automations.title') }}</h1>
        <p class="text-sm text-[var(--text-muted)] mt-1">{{ t('automations.subtitle') }}</p>
      </div>
      <div class="flex items-center gap-2">
        <button
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--border)] text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:border-[var(--border-hover)] bg-[var(--bg-raised)] transition-colors"
          :disabled="refreshing"
          @click="reload"
        >
          <svg class="h-3.5 w-3.5" :class="refreshing ? 'animate-spin' : ''" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
          </svg>
          Refresh
        </button>
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
    </div>

    <!-- Error -->
    <div v-if="error" class="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
      {{ error }}
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-2">
      <div v-for="i in 3" :key="i" class="h-20 rounded-xl bg-[var(--bg-surface)] animate-pulse" />
    </div>

    <!-- Enhanced empty state with templates -->
    <template v-else-if="rules.length === 0">
      <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-6 py-10">
        <div class="flex flex-col items-center text-center gap-5 mb-8">
          <div class="h-14 w-14 rounded-xl bg-[var(--bg-raised)] flex items-center justify-center">
            <svg class="h-7 w-7 text-[var(--primary)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
            </svg>
          </div>
          <div class="space-y-1.5 max-w-sm">
            <h3 class="text-base font-semibold text-[var(--text-primary)]">Automate device behavior</h3>
            <p class="text-sm text-[var(--text-muted)]">React automatically to device events, variable changes and sensor thresholds.</p>
          </div>
        </div>

        <!-- Quick-start template cards -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
          <button
            v-for="tpl in quickTemplates"
            :key="tpl.name"
            class="flex flex-col gap-2.5 p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-raised)] text-left hover:border-[var(--border-strong)] hover:bg-[var(--bg-raised)] transition-colors group"
            @click="openFromTemplate(tpl)"
          >
            <div
              class="h-8 w-8 rounded-lg flex items-center justify-center"
              :style="{ background: `color-mix(in srgb, ${tpl.color} 15%, transparent)` }"
            >
              <svg class="h-4 w-4" :style="{ color: tpl.color }" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" :d="tpl.icon" />
              </svg>
            </div>
            <div>
              <p class="text-xs font-semibold text-[var(--text-primary)] group-hover:text-[var(--primary)] transition-colors leading-tight">{{ tpl.name }}</p>
              <p class="text-[11px] text-[var(--text-muted)] mt-0.5 leading-tight">{{ tpl.description }}</p>
            </div>
          </button>
        </div>

        <div class="text-center">
          <button
            class="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-[var(--primary)]/10 text-[var(--primary)] hover:bg-[var(--primary)]/20 transition-colors"
            @click="openCreate"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            Start from scratch
          </button>
        </div>
      </div>
    </template>

    <!-- Rules list — compact cards -->
    <div v-else class="space-y-1.5">
      <div
        v-for="rule in rules"
        :key="rule.id"
        :class="[
          'rounded-xl border bg-[var(--bg-surface)] transition-colors',
          rule.enabled ? 'border-[var(--border)]' : 'border-[var(--border)] opacity-60',
        ]"
      >
        <!-- Compact row: name + IF→THEN summary + status + toggle -->
        <button
          class="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-[var(--bg-raised)]/50 transition-colors rounded-xl"
          @click="toggleRuleExpand(rule.id)"
        >
          <!-- Expand chevron -->
          <svg
            :class="['h-3.5 w-3.5 text-[var(--text-muted)] shrink-0 transition-transform duration-200', expandedRuleId === rule.id ? 'rotate-90' : '']"
            fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>

          <!-- Name -->
          <span class="text-sm font-medium text-[var(--text-primary)] truncate min-w-0 shrink">{{ rule.name }}</span>

          <!-- IF→THEN one-liner -->
          <span class="hidden sm:flex items-center gap-1.5 text-xs text-[var(--text-muted)] font-mono truncate flex-1 min-w-0">
            <span class="text-blue-400">IF</span>
            <span class="truncate">{{ triggerSummary(rule) }}</span>
            <svg class="h-3 w-3 text-[var(--primary)] shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
            </svg>
            <span class="text-[var(--primary)]">THEN</span>
            <span class="truncate">{{ actionSummary(rule) }}</span>
          </span>

          <!-- Status badges -->
          <div class="shrink-0 flex items-center gap-2">
            <span v-if="!rule.enabled" class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[var(--bg-raised)] text-[var(--text-muted)]">off</span>
            <span v-if="rule.fire_count > 0" class="text-[10px] text-[var(--text-muted)]">{{ rule.fire_count }}x</span>

            <!-- Toggle (stop propagation to prevent expand) -->
            <button
              :title="rule.enabled ? 'Disable rule' : 'Enable rule'"
              :disabled="togglingId === rule.id"
              :class="[
                'relative h-5 w-9 rounded-full transition-colors focus:outline-none disabled:opacity-50',
                rule.enabled ? 'bg-[var(--primary)]/70' : 'bg-[var(--bg-raised)]',
              ]"
              @click.stop="handleToggle(rule)"
            >
              <span :class="['absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform', rule.enabled ? 'translate-x-4' : 'translate-x-0.5']" />
            </button>
          </div>
        </button>

        <!-- Expanded details -->
        <div v-if="expandedRuleId === rule.id" class="px-4 pb-3 pt-0 border-t border-[var(--border)]">
          <!-- Description -->
          <p v-if="rule.description" class="text-xs text-[var(--text-muted)] mt-2 mb-2">{{ rule.description }}</p>

          <!-- IF → THEN detail (visible on mobile too) -->
          <div class="flex items-center gap-2 flex-wrap mt-2">
            <span class="inline-flex items-center gap-1 text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-blue-500/10 text-blue-400">
              IF {{ rule.trigger_type.replace(/_/g, " ") }}
            </span>
            <span class="text-xs text-[var(--text-muted)] font-mono">{{ triggerSummary(rule) }}</span>
            <svg class="h-3.5 w-3.5 text-[var(--primary)] shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
            </svg>
            <span class="inline-flex items-center gap-1 text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-[var(--primary)]/10 text-[var(--primary)]">
              THEN {{ rule.action_type.replace(/_/g, " ") }}
            </span>
            <span class="text-xs text-[var(--text-muted)] font-mono">{{ actionSummary(rule) }}</span>
          </div>

          <!-- Stats -->
          <div class="mt-2 flex items-center gap-3 text-xs text-[var(--text-muted)]">
            <span>Fired: <span class="text-[var(--text-primary)]">{{ rule.fire_count }}</span></span>
            <span>Last: <span class="text-[var(--text-primary)]">{{ relativeTime(rule.last_fired_at) }}</span></span>
            <span>Cooldown: <span class="text-[var(--text-primary)]">{{ rule.cooldown_seconds }}s</span></span>
          </div>

          <!-- Action buttons -->
          <div class="mt-3 flex items-center gap-1.5">
            <button
              class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
              title="View history"
              @click="openHistory(rule)"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </button>
            <button
              class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
              title="Edit rule"
              @click="openEdit(rule)"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z" />
              </svg>
            </button>
            <button
              class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
              title="Duplicate rule"
              @click="duplicateRule(rule)"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75" />
              </svg>
            </button>
            <button
              :disabled="testingId === rule.id"
              :class="[
                'px-2.5 py-1 rounded-lg text-xs font-medium transition-colors disabled:opacity-50',
                testConfirmId === rule.id
                  ? 'bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30'
                  : 'text-[var(--text-muted)] hover:text-[var(--primary)] hover:bg-[var(--primary)]/10',
              ]"
              title="Test fire rule"
              @click="handleTest(rule.id)"
            >
              {{ testingId === rule.id ? '...' : testConfirmId === rule.id ? 'Confirm?' : 'Test' }}
            </button>
            <button
              :disabled="deletingId === rule.id"
              :class="[
                'px-2.5 py-1 rounded-lg text-xs font-medium transition-colors disabled:opacity-50',
                deletingConfirmId === rule.id
                  ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                  : 'text-[var(--text-muted)] hover:text-red-400 hover:bg-red-500/10',
              ]"
              title="Delete rule"
              @click="handleDelete(rule.id)"
            >
              {{ deletingId === rule.id ? '...' : deletingConfirmId === rule.id ? 'Confirm?' : 'Delete' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Create/Edit Modal ─────────────────────────────────────────────────── -->
    <Teleport to="body">
      <div
        v-if="modalOpen"
        class="fixed inset-0 z-50 flex items-start justify-center p-4 overflow-y-auto"
        @keydown.escape="closeModal"
      >
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-black/60" @click="closeModal" />

        <!-- Modal card -->
        <div class="relative z-10 w-full max-w-lg my-8 rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] shadow-2xl p-6 space-y-5">
          <h3 class="text-base font-semibold text-[var(--text-primary)]">
            {{ modalMode === "create" ? "New Automation Rule" : "Edit Automation Rule" }}
          </h3>

          <!-- Name & Description -->
          <div class="space-y-3">
            <div class="space-y-1">
              <label :class="labelClass">Name <span class="text-red-400">*</span></label>
              <input v-model="formName" type="text" placeholder="e.g. High temperature alert" :class="inputClass" />
            </div>
            <div class="space-y-1">
              <label :class="labelClass">Description <span class="text-[var(--text-muted)]">(optional)</span></label>
              <input v-model="formDescription" type="text" placeholder="What does this rule do?" :class="inputClass" />
            </div>
          </div>

          <!-- Divider -->
          <div class="border-t border-[var(--border)]" />

          <!-- Trigger Section -->
          <div class="space-y-3">
            <h4 class="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">IF (Trigger)</h4>

            <!-- Trigger type selector -->
            <div class="grid grid-cols-2 gap-2">
              <button
                v-for="t in TRIGGER_TYPES"
                :key="t.value"
                :class="[
                  'text-left px-3 py-2.5 rounded-lg border text-xs transition-colors',
                  formTriggerType === t.value
                    ? 'border-blue-500/50 bg-blue-500/10 text-blue-400'
                    : 'border-[var(--border)] bg-[var(--bg-raised)] text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:border-[var(--border-hover)]',
                ]"
                @click="formTriggerType = t.value"
              >
                <div class="flex items-center gap-2 mb-0.5">
                  <svg class="h-3.5 w-3.5 shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" :d="t.icon" />
                  </svg>
                  <span class="font-medium">{{ t.label }}</span>
                </div>
                <p class="text-[10px] leading-tight opacity-70">{{ t.desc }}</p>
              </button>
            </div>

            <!-- Variable Threshold config -->
            <template v-if="formTriggerType === 'variable_threshold'">
              <UEntitySelect v-model="trigVarKey" entity-type="variable" label="Variable Key" />
              <div class="grid grid-cols-2 gap-2">
                <div class="space-y-1">
                  <label :class="labelClass">Operator</label>
                  <select v-model="trigOperator" :class="inputClass">
                    <option v-for="op in OPERATOR_OPTIONS" :key="op.value" :value="op.value">{{ op.label }}</option>
                  </select>
                </div>
                <div class="space-y-1">
                  <label :class="labelClass">Threshold Value</label>
                  <input v-model.number="trigValue" type="number" step="any" :class="inputClass" />
                </div>
              </div>
              <UEntitySelect v-model="trigDeviceUid" entity-type="device" label="Device UID" placeholder="Leave empty for global variable" :optional="true" />
            </template>

            <!-- Variable Geofence config -->
            <template v-else-if="formTriggerType === 'variable_geofence'">
              <p class="text-[10px] text-[var(--text-muted)] bg-[var(--bg-raised)] rounded px-2 py-1">
                GPS variable should contain <code class="font-mono">{{"{"}}lat: number, lng: number{{"}"}}</code>
              </p>
              <UEntitySelect v-model="trigVarKey" entity-type="variable" label="Variable Key" />
              <UEntitySelect v-model="trigDeviceUid" entity-type="device" label="Device UID" placeholder="Leave empty for any device" :optional="true" />
              <div class="grid grid-cols-2 gap-2">
                <div class="space-y-1">
                  <label :class="labelClass">Geofence Type</label>
                  <select v-model="trigGeoType" :class="inputClass">
                    <option value="circle">Circle</option>
                    <option value="polygon">Polygon</option>
                  </select>
                </div>
                <div class="space-y-1">
                  <label :class="labelClass">Trigger When</label>
                  <select v-model="trigGeoExitEnter" :class="inputClass">
                    <option value="exit">Exits zone</option>
                    <option value="enter">Enters zone</option>
                  </select>
                </div>
              </div>
              <template v-if="trigGeoType === 'circle'">
                <div class="grid grid-cols-2 gap-2">
                  <div class="space-y-1">
                    <label :class="labelClass">Center Lat</label>
                    <input v-model.number="trigGeoLat" type="number" step="any" placeholder="48.137" :class="inputClass" />
                  </div>
                  <div class="space-y-1">
                    <label :class="labelClass">Center Lng</label>
                    <input v-model.number="trigGeoLng" type="number" step="any" placeholder="11.576" :class="inputClass" />
                  </div>
                </div>
                <div class="space-y-1">
                  <label :class="labelClass">Radius: {{ trigGeoRadius }}m</label>
                  <input v-model.number="trigGeoRadius" type="range" min="100" max="50000" step="100" class="w-full accent-[var(--primary)]" />
                  <div class="flex justify-between text-[10px] text-[var(--text-muted)]"><span>100m</span><span>50km</span></div>
                </div>
              </template>
              <template v-else>
                <div class="space-y-1">
                  <label :class="labelClass">Polygon (JSON array of [lat, lng] pairs)</label>
                  <textarea v-model="trigGeoPolygon" rows="3" placeholder='[[48.137, 11.576], [48.140, 11.580], ...]' :class="[inputClass, 'font-mono text-[10px]']" />
                </div>
              </template>
            </template>

            <!-- Device Offline config -->
            <template v-else-if="formTriggerType === 'device_offline'">
              <UEntitySelect v-model="trigDeviceUid" entity-type="device" label="Device UID" placeholder="Leave empty for any device" :optional="true" />
            </template>

            <!-- Telemetry Received config -->
            <template v-else-if="formTriggerType === 'telemetry_received'">
              <UEntitySelect v-model="trigDeviceUid" entity-type="device" label="Device UID" placeholder="Leave empty for any device" :optional="true" />
              <div class="space-y-1">
                <label :class="labelClass">Event Type <span class="text-[var(--text-muted)]">(optional)</span></label>
                <input v-model="trigEventType" type="text" placeholder="e.g. sensor.reading" :class="inputClass" />
              </div>
            </template>
          </div>

          <!-- Divider -->
          <div class="border-t border-[var(--border)]" />

          <!-- Action Section -->
          <div class="space-y-3">
            <h4 class="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">THEN (Action)</h4>

            <!-- Action type selector -->
            <div class="grid grid-cols-2 gap-2">
              <button
                v-for="a in ACTION_TYPES"
                :key="a.value"
                :class="[
                  'text-left px-3 py-2.5 rounded-lg border text-xs transition-colors',
                  formActionType === a.value
                    ? 'border-[var(--primary)]/50 bg-[var(--primary)]/10 text-[var(--primary)]'
                    : 'border-[var(--border)] bg-[var(--bg-raised)] text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:border-[var(--border-hover)]',
                ]"
                @click="formActionType = a.value"
              >
                <div class="flex items-center gap-2 mb-0.5">
                  <svg class="h-3.5 w-3.5 shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" :d="a.icon" />
                  </svg>
                  <span class="font-medium">{{ a.label }}</span>
                </div>
                <p class="text-[10px] leading-tight opacity-70">{{ a.desc }}</p>
              </button>
            </div>

            <!-- Set Variable config -->
            <template v-if="formActionType === 'set_variable'">
              <UEntitySelect v-model="actVarKey" entity-type="variable" label="Variable Key" />
              <div class="space-y-1">
                <label :class="labelClass">Value (JSON)</label>
                <input v-model="actVarValue" type="text" placeholder='"alert"' :class="[inputClass, 'font-mono']" />
              </div>
              <div class="grid grid-cols-2 gap-2">
                <div class="space-y-1">
                  <label :class="labelClass">Scope</label>
                  <select v-model="actVarScope" :class="inputClass">
                    <option value="global">global</option>
                    <option value="device">device</option>
                  </select>
                </div>
                <UEntitySelect v-model="actVarDeviceUid" entity-type="device" label="Device UID" placeholder="device scope only" :optional="true" />
              </div>
            </template>

            <!-- Call Webhook config -->
            <template v-else-if="formActionType === 'call_webhook'">
              <div class="space-y-1">
                <label :class="labelClass">URL <span class="text-red-400">*</span></label>
                <input v-model="actWebhookUrl" type="url" placeholder="https://hooks.example.com/..." :class="inputClass" />
              </div>
              <div class="space-y-1">
                <label :class="labelClass">Method</label>
                <select v-model="actWebhookMethod" :class="inputClass">
                  <option value="POST">POST</option>
                  <option value="GET">GET</option>
                  <option value="PUT">PUT</option>
                </select>
              </div>
              <div class="space-y-1">
                <label :class="labelClass">Headers (JSON)</label>
                <textarea v-model="actWebhookHeaders" rows="2" placeholder='{"Authorization": "Bearer ..."}' :class="[inputClass, 'font-mono text-[10px]']" />
              </div>
              <div class="space-y-1">
                <label :class="labelClass">Payload Template (JSON)</label>
                <textarea v-model="actWebhookPayload" rows="3" placeholder='{"key": "value"}' :class="[inputClass, 'font-mono text-[10px]']" />
              </div>
            </template>

            <!-- Create Alert config -->
            <template v-else-if="formActionType === 'create_alert_event'">
              <div class="space-y-1">
                <label :class="labelClass">Severity</label>
                <select v-model="actAlertSeverity" :class="inputClass">
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="warning">warning</option>
                  <option value="high">high</option>
                  <option value="critical">critical</option>
                </select>
              </div>
              <div class="space-y-1">
                <label :class="labelClass">Message Template</label>
                <textarea v-model="actAlertMessage" rows="2" placeholder="Alert: automation rule fired" :class="inputClass" />
              </div>
            </template>

            <!-- Emit System Event config -->
            <template v-else-if="formActionType === 'emit_system_event'">
              <div class="space-y-1">
                <label :class="labelClass">Event Type</label>
                <input v-model="actEventType" type="text" placeholder="e.g. automation.alert" :class="inputClass" />
              </div>
              <div class="space-y-1">
                <label :class="labelClass">Extra Payload (JSON)</label>
                <textarea v-model="actEventPayload" rows="2" placeholder='{"key": "value"}' :class="[inputClass, 'font-mono text-[10px]']" />
              </div>
            </template>
          </div>

          <!-- Divider -->
          <div class="border-t border-[var(--border)]" />

          <!-- Settings -->
          <div class="space-y-3">
            <h4 class="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">Settings</h4>
            <div class="space-y-1">
              <label :class="labelClass" title="Wartezeit in Sekunden bevor die Regel nach dem Feuern erneut auslösen kann">Cooldown: {{ formCooldown }}s</label>
              <input v-model.number="formCooldown" type="range" min="0" max="3600" step="30" class="w-full accent-[var(--primary)]" />
              <div class="flex justify-between text-[10px] text-[var(--text-muted)]"><span>0s (kein Cooldown)</span><span>1h</span></div>
            </div>
            <div class="flex items-center gap-2">
              <input id="form-enabled" v-model="formEnabled" type="checkbox" class="h-4 w-4 rounded border-[var(--border)] accent-[var(--primary)]" />
              <label for="form-enabled" class="text-sm text-[var(--text-primary)]">Enabled</label>
            </div>
          </div>

          <!-- Inline error -->
          <p v-if="modalError" class="text-xs text-red-400">{{ modalError }}</p>

          <!-- Buttons -->
          <div class="flex justify-end gap-2 pt-1">
            <button
              class="px-4 py-2 rounded-lg text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
              @click="closeModal"
            >
              Cancel
            </button>
            <button
              :disabled="modalSaving"
              class="px-4 py-2 rounded-lg text-sm font-medium bg-[var(--primary)]/10 text-[var(--primary)] hover:bg-[var(--primary)]/20 disabled:opacity-50 transition-colors"
              @click="handleSave"
            >
              {{ modalSaving ? "Saving…" : "Save Rule" }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── History Modal ─────────────────────────────────────────────────────── -->
    <Teleport to="body">
      <div
        v-if="historyOpen"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
        @keydown.escape="closeHistory"
      >
        <div class="fixed inset-0 bg-black/60" @click="closeHistory" />
        <div class="relative z-10 w-full max-w-lg rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] shadow-2xl p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-base font-semibold text-[var(--text-primary)]">Fire History — {{ historyRuleName }}</h3>
            <button class="text-[var(--text-muted)] hover:text-[var(--text-primary)]" @click="closeHistory">
              <svg class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div v-if="historyLoading" class="space-y-2">
            <div v-for="i in 3" :key="i" class="h-12 rounded-lg bg-[var(--bg-raised)] animate-pulse" />
          </div>
          <p v-else-if="historyEntries.length === 0" class="text-sm text-[var(--text-muted)] text-center py-8">
            No fire history yet.
          </p>
          <div v-else class="space-y-2 max-h-96 overflow-y-auto">
            <div
              v-for="entry in historyEntries"
              :key="entry.id"
              class="rounded-lg border border-[var(--border)] bg-[var(--bg-raised)] px-3 py-2.5 flex items-start gap-3"
            >
              <div :class="['h-2 w-2 rounded-full shrink-0 mt-1.5', entry.success ? 'bg-green-400' : 'bg-red-400']" />
              <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between">
                  <span :class="['text-xs font-medium', entry.success ? 'text-green-400' : 'text-red-400']">
                    {{ entry.success ? "Success" : "Failed" }}
                  </span>
                  <span class="text-[10px] text-[var(--text-muted)]">{{ relativeTime(entry.fired_at) }}</span>
                </div>
                <p v-if="entry.error_message" class="text-xs text-red-400 mt-0.5">{{ entry.error_message }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
