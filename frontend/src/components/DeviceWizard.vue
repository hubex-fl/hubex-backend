<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import UButton from "./ui/UButton.vue";
import UInput from "./ui/UInput.vue";
import UModal from "./ui/UModal.vue";
import { apiFetch } from "../lib/api";
import { parseApiError, mapErrorToUserText } from "../lib/errors";
import { useToastStore } from "../stores/toast";

const props = defineProps<{
  open: boolean;
  initialCategory?: "hardware" | "service" | "bridge" | "agent";
}>();

const emit = defineEmits<{
  close: [];
  created: [deviceId: number];
}>();

const router = useRouter();
const toast = useToastStore();
const { t } = useI18n();

// ── State ────────────────────────────────────────────────────────────────────
type Category = "hardware" | "service" | "bridge" | "agent";
type Step = "category" | "setup" | "pairing" | "name" | "done";

const step = ref<Step>(props.initialCategory ? "setup" : "category");
const category = ref<Category>(props.initialCategory ?? "hardware");
const saving = ref(false);
const error = ref<string | null>(null);
const createdDeviceId = ref<number | null>(null);
const createdDeviceUid = ref<string | null>(null);

// Form
const deviceName = ref("");
const deviceLocation = ref("");
const showAdvanced = ref(false);

// Hardware
const hardwareType = ref<"esp32" | "shelly" | "other">("esp32");
const pairingUid = ref("");
const pairingCode = ref<string | null>(null);
const pairingQrSvg = ref<string | null>(null);
const pairingStatus = ref<"idle" | "waiting" | "claimed" | "confirmed" | "expired" | "error">("idle");
const pairingError = ref<string | null>(null);
let pairingPollTimer: number | null = null;
let autoNavTimer: number | null = null;

// Service
const serviceUrl = ref("");
const serviceAuth = ref<"none" | "api_key" | "oauth">("none");
const serviceApiKey = ref("");
const servicePollInterval = ref(60);

// Bridge
const bridgeProtocol = ref<"mqtt" | "modbus_rtu" | "modbus_tcp" | "ble" | "other">("mqtt");
const mqttBroker = ref("");
const mqttTopic = ref("");

// Agent
const agentSystem = ref<"linux" | "windows" | "macos" | "docker">("linux");

// ── Category definitions ─────────────────────────────────────────────────────
const categories = computed(() => [
  { key: "hardware" as Category, label: t("devices.categories.hardware"), desc: t("devices.wizard.hwDesc"), icon: "M11.42 15.17l-4.655-1.45A1.32 1.32 0 016 12.527V12c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0m-9.288 0V5.25A2.25 2.25 0 018.25 3h7.5A2.25 2.25 0 0118 5.25v5.893m-9.644 0A2.25 2.25 0 006 13.5v.75", color: "var(--cat-hardware, #F5A623)" },
  { key: "service" as Category, label: t("devices.categories.service"), desc: t("devices.wizard.svcDesc"), icon: "M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582", color: "var(--cat-service, #60A5FA)" },
  { key: "bridge" as Category, label: t("devices.categories.bridge"), desc: t("devices.wizard.bridgeDesc"), icon: "M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1", color: "var(--cat-bridge, #2DD4BF)" },
  { key: "agent" as Category, label: t("devices.categories.agent"), desc: t("devices.wizard.agentDesc"), icon: "M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-13.5 0v-1.5", color: "var(--cat-agent, #A78BFA)" },
]);

const currentCat = computed(() => categories.value.find(c => c.key === category.value));
const totalSteps = computed(() => category.value === "hardware" ? 4 : 3);
const stepIndex = computed(() => {
  if (step.value === "category") return 1;
  if (step.value === "setup") return 2;
  if (step.value === "pairing") return 3; // hardware only
  if (step.value === "name") return category.value === "hardware" ? 4 : 3;
  return totalSteps.value; // done
});

// ── Navigation ───────────────────────────────────────────────────────────────
function selectCategory(cat: Category) {
  category.value = cat;
  step.value = "setup";
  error.value = null;
}

function goBack() {
  stopPairingPoll();
  if (step.value === "setup" || step.value === "pairing") step.value = "category";
  else if (step.value === "name") step.value = category.value === "hardware" ? "pairing" : "setup";
}

// ── Pairing (Hardware ESP32 flow) ────────────────────────────────────────────
async function startPairing() {
  if (!pairingUid.value.trim()) {
    error.value = t("devices.wizard.enterUid");
    return;
  }
  error.value = null;
  pairingStatus.value = "waiting";
  pairingError.value = null;
  step.value = "pairing";

  try {
    const res = await apiFetch<{ pairing_code: string; device_uid: string; expires_at: string; ttl_seconds: number }>(
      "/api/v1/devices/pairing/start",
      { method: "POST", body: JSON.stringify({ device_uid: pairingUid.value.trim() }) }
    );
    pairingCode.value = res.pairing_code;
    createdDeviceUid.value = res.device_uid;

    // Load QR code
    try {
      const qrRes = await fetch(`/api/v1/devices/pairing/${encodeURIComponent(res.pairing_code)}/qr`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("hubex_access_token") ?? ""}` },
      });
      if (qrRes.ok) pairingQrSvg.value = await qrRes.text();
    } catch { /* QR optional */ }

    // Start polling for claim status
    startPairingPoll(res.pairing_code);
  } catch (e: unknown) {
    const info = parseApiError(e);
    pairingError.value = mapErrorToUserText(info, t("devices.wizard.error"));
    pairingStatus.value = "error";
  }
}

function startPairingPoll(code: string) {
  stopPairingPoll();
  let attempts = 0;
  const maxAttempts = 150; // 5 min at 2s intervals
  pairingPollTimer = window.setInterval(async () => {
    attempts++;
    if (attempts > maxAttempts) {
      stopPairingPoll();
      pairingStatus.value = "expired";
      pairingError.value = t("devices.wizard.pairingExpired");
      return;
    }
    try {
      const status = await apiFetch<{ status: string; claimed: boolean; device_id?: number }>(
        `/api/v1/devices/pairing/status?code=${encodeURIComponent(code)}`
      );
      if (status.claimed && status.device_id) {
        stopPairingPoll();
        pairingStatus.value = "confirmed";
        createdDeviceId.value = status.device_id;
        // Auto-advance to name step after short celebration
        autoNavTimer = window.setTimeout(() => { step.value = "name"; }, 1500);
      }
    } catch {
      // Polling error — keep trying
    }
  }, 2000);
}

function stopPairingPoll() {
  if (pairingPollTimer !== null) {
    clearInterval(pairingPollTimer);
    pairingPollTimer = null;
  }
}

onUnmounted(() => {
  stopPairingPoll();
  if (autoNavTimer !== null) { clearTimeout(autoNavTimer); autoNavTimer = null; }
});

// ── Create Device (for non-hardware flows) ───────────────────────────────────
async function createDevice() {
  saving.value = true;
  error.value = null;
  try {
    const body: Record<string, unknown> = {
      device_uid: pairingUid.value.trim() || createdDeviceUid.value || `${category.value}-${Date.now()}`,
      name: deviceName.value.trim() || null,
      device_type: category.value === "hardware" ? hardwareType.value : category.value === "service" ? "api_device" : category.value,
      category: category.value,
      location_name: deviceLocation.value.trim() || null,
      auto_discovery: true,
    };

    // For hardware that already paired, update name + type
    if (category.value === "hardware" && createdDeviceId.value) {
      await apiFetch(`/api/v1/devices/${createdDeviceId.value}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: deviceName.value.trim() || null,
          device_type: hardwareType.value,
          category: "hardware",
          location_name: deviceLocation.value.trim() || null,
        }),
      });
    } else {
      // Step 1: Register device via /hello
      const uid = body.device_uid as string;
      const hello = await apiFetch<{ device_id: number; claimed: boolean }>("/api/v1/devices/hello", {
        method: "POST",
        body: JSON.stringify({ device_uid: uid }),
      });
      createdDeviceId.value = hello.device_id;
      createdDeviceUid.value = uid;

      // Step 2: Start pairing to get a code
      const pairing = await apiFetch<{ pairing_code: string }>("/api/v1/devices/pairing/start", {
        method: "POST",
        body: JSON.stringify({ device_uid: uid }),
      });

      // Step 3: Immediately claim the code (user is the one creating it)
      await apiFetch("/api/v1/devices/pairing/claim", {
        method: "POST",
        body: JSON.stringify({ device_uid: uid, pairing_code: pairing.pairing_code }),
      });

      // Step 4: Confirm pairing (NO auth — device-initiated endpoint)
      try {
        await fetch("/api/v1/devices/pairing/confirm", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ device_uid: uid, pairing_code: pairing.pairing_code }),
        });
      } catch {
        // Confirm may fail — OK for virtual devices
      }

      // Step 5: Update name, category, type, location (device is now claimed)
      const deviceType = category.value === "hardware"
        ? hardwareType.value
        : category.value === "service"
          ? "api_device"
          : category.value;
      await apiFetch(`/api/v1/devices/${hello.device_id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: deviceName.value.trim() || null,
          device_type: deviceType,
          category: category.value,
          location_name: deviceLocation.value.trim() || null,
        }),
      });
    }
    step.value = "done";
    toast.addToast(t("devices.wizard.success"), "success");
    // Auto-navigate to device detail after 2 seconds
    autoNavTimer = window.setTimeout(() => { if (step.value === "done") goToDevice(); }, 2000);
  } catch (e: unknown) {
    const info = parseApiError(e);
    error.value = mapErrorToUserText(info, t("devices.wizard.error"));
  } finally {
    saving.value = false;
  }
}

// ── Done actions ─────────────────────────────────────────────────────────────
function goToDevice() {
  if (createdDeviceId.value) emit("created", createdDeviceId.value);
  emit("close");
  if (createdDeviceId.value) router.push(`/devices/${createdDeviceId.value}`);
}
function goToAutomation() {
  if (createdDeviceId.value) emit("created", createdDeviceId.value);
  emit("close");
  router.push({ path: "/automations", query: { create: "true", ...(createdDeviceUid.value ? { device_uid: createdDeviceUid.value } : {}) } });
}
function goToDashboard() {
  if (createdDeviceId.value) emit("created", createdDeviceId.value);
  emit("close");
  router.push({ path: "/dashboards", query: { create: "true" } });
}
function closeWizard() {
  stopPairingPoll();
  if (autoNavTimer !== null) { clearTimeout(autoNavTimer); autoNavTimer = null; }
  step.value = "category";
  category.value = props.initialCategory ?? "hardware";
  error.value = null;
  pairingCode.value = null;
  pairingStatus.value = "idle";
  pairingQrSvg.value = null;
  createdDeviceId.value = null;
  createdDeviceUid.value = null;
  deviceName.value = "";
  deviceLocation.value = "";
  pairingUid.value = "";
  serviceUrl.value = "";
  serviceApiKey.value = "";
  serviceAuth.value = "none";
  mqttBroker.value = "";
  mqttTopic.value = "";
  showAdvanced.value = false;
  emit("close");
}

// Sync initial category from prop
watch(() => props.initialCategory, (cat) => { if (cat) category.value = cat; });
</script>

<template>
  <UModal :open="open" :title="t('devices.wizard.title', { step: Math.min(stepIndex, totalSteps), total: totalSteps })" size="lg" @close="closeWizard">

    <!-- ── Step 1: Category ───────────────────────────────────────────── -->
    <div v-if="step === 'category'" class="space-y-4">
      <p class="text-sm text-[var(--text-muted)]">{{ t('devices.wizard.whatToConnect') }}</p>
      <div class="grid grid-cols-2 gap-3">
        <button
          v-for="cat in categories"
          :key="cat.key"
          class="flex flex-col items-center gap-2.5 p-5 rounded-xl border-2 transition-all text-center hover:scale-[1.02]"
          :class="category === cat.key ? 'border-[var(--primary)] bg-[var(--primary)]/5' : 'border-[var(--border)] bg-[var(--bg-raised)] hover:border-[var(--primary)]/40'"
          @click="selectCategory(cat.key)"
        >
          <div class="h-10 w-10 rounded-lg flex items-center justify-center" :style="{ background: `color-mix(in srgb, ${cat.color} 15%, transparent)` }">
            <svg class="h-5 w-5" :style="{ color: cat.color }" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" :d="cat.icon" />
            </svg>
          </div>
          <div>
            <p class="text-sm font-semibold text-[var(--text-primary)]">{{ cat.label }}</p>
            <p class="text-[10px] text-[var(--text-muted)] mt-0.5">{{ cat.desc }}</p>
          </div>
        </button>
      </div>
    </div>

    <!-- ── Step 2: Setup ──────────────────────────────────────────────── -->
    <div v-else-if="step === 'setup'" class="space-y-4">
      <div class="flex items-center gap-2 mb-2">
        <button class="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]" @click="goBack">← {{ t('devices.wizard.back') }}</button>
        <span class="text-xs font-semibold" :style="{ color: currentCat?.color }">{{ currentCat?.label }}</span>
      </div>

      <!-- Hardware -->
      <template v-if="category === 'hardware'">
        <p class="text-sm text-[var(--text-muted)]">{{ t('devices.wizard.howConnect') }}</p>
        <div class="grid grid-cols-3 gap-2">
          <button
            v-for="hw in [{ key: 'esp32', label: 'ESP32 (WiFi)' }, { key: 'shelly', label: 'Shelly (MQTT)' }, { key: 'other', label: 'Other' }]"
            :key="hw.key"
            :class="['px-3 py-2 rounded-lg border text-xs font-medium transition-colors', hardwareType === hw.key ? 'border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)]' : 'border-[var(--border)] text-[var(--text-muted)] hover:border-[var(--primary)]/40']"
            @click="hardwareType = hw.key as typeof hardwareType"
          >{{ hw.label }}</button>
        </div>
        <UInput v-model="pairingUid" :label="t('devices.deviceUid')" :placeholder="t('devices.wizard.uidPlaceholder')" />
        <p class="text-[10px] text-[var(--text-muted)]">{{ t('devices.wizard.enterUid') }}</p>
        <div v-if="error" class="text-xs text-[var(--status-bad)] px-3 py-2 rounded-lg bg-[var(--status-bad)]/10">{{ error }}</div>
        <div class="flex justify-between mt-2">
          <button class="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]" @click="step = 'name'">{{ t('devices.wizard.skip') }} →</button>
          <UButton size="sm" @click="startPairing">{{ t('devices.wizard.startPairing') }}</UButton>
        </div>
      </template>

      <!-- Service -->
      <template v-else-if="category === 'service'">
        <p class="text-sm text-[var(--text-muted)]">{{ t('devices.wizard.whichApi') }}</p>
        <UInput v-model="serviceUrl" :label="t('devices.wizard.apiUrl')" :placeholder="t('devices.wizard.apiUrlPlaceholder')" />
        <div class="flex gap-2">
          <button
            v-for="auth in [{ key: 'none', label: t('devices.wizard.noAuth') }, { key: 'api_key', label: t('devices.wizard.apiKey') }, { key: 'oauth', label: t('devices.wizard.oauth') }]"
            :key="auth.key"
            :class="['px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors', serviceAuth === auth.key ? 'border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)]' : 'border-[var(--border)] text-[var(--text-muted)]']"
            @click="serviceAuth = auth.key as typeof serviceAuth"
          >{{ auth.label }}</button>
        </div>
        <UInput v-if="serviceAuth === 'api_key'" v-model="serviceApiKey" :label="t('devices.wizard.apiKey')" placeholder="sk-..." />
        <button class="text-[10px] text-[var(--text-muted)] hover:text-[var(--primary)]" @click="showAdvanced = !showAdvanced">
          {{ showAdvanced ? '▾' : '▸' }} {{ t('devices.wizard.advanced') }}
        </button>
        <UInput v-if="showAdvanced" v-model.number="servicePollInterval" :label="t('devices.wizard.pollInterval')" type="number" placeholder="60" class="w-32" />
        <div class="flex justify-between mt-2">
          <button class="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]" @click="step = 'name'">{{ t('devices.wizard.skip') }} →</button>
          <UButton size="sm" @click="step = 'name'">{{ t('common.next') }}</UButton>
        </div>
      </template>

      <!-- Bridge -->
      <template v-else-if="category === 'bridge'">
        <p class="text-sm text-[var(--text-muted)]">{{ t('devices.wizard.whichProtocol') }}</p>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="proto in [{ key: 'mqtt', label: 'MQTT' }, { key: 'modbus_rtu', label: 'Modbus RTU' }, { key: 'modbus_tcp', label: 'Modbus TCP' }, { key: 'ble', label: 'BLE' }, { key: 'other', label: 'Other' }]"
            :key="proto.key"
            :class="['px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors', bridgeProtocol === proto.key ? 'border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)]' : 'border-[var(--border)] text-[var(--text-muted)]']"
            @click="bridgeProtocol = proto.key as typeof bridgeProtocol"
          >{{ proto.label }}</button>
        </div>
        <template v-if="bridgeProtocol === 'mqtt'">
          <UInput v-model="mqttBroker" :label="t('devices.wizard.mqttBroker')" placeholder="mqtt://broker.example.com:1883" />
          <UInput v-model="mqttTopic" :label="t('devices.wizard.mqttTopic')" placeholder="devices/my-sensor/#" />
        </template>
        <p v-else class="text-xs text-[var(--text-muted)] italic">{{ t('devices.wizard.configLater') }}</p>
        <div class="flex justify-between mt-2">
          <button class="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]" @click="step = 'name'">{{ t('devices.wizard.skip') }} →</button>
          <UButton size="sm" @click="step = 'name'">{{ t('common.next') }}</UButton>
        </div>
      </template>

      <!-- Agent -->
      <template v-else-if="category === 'agent'">
        <p class="text-sm text-[var(--text-muted)]">{{ t('devices.wizard.whichSystem') }}</p>
        <div class="grid grid-cols-2 gap-2">
          <button
            v-for="sys in [{ key: 'linux', label: 'Linux' }, { key: 'windows', label: 'Windows' }, { key: 'macos', label: 'macOS' }, { key: 'docker', label: 'Docker' }]"
            :key="sys.key"
            :class="['px-3 py-2 rounded-lg border text-xs font-medium transition-colors', agentSystem === sys.key ? 'border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)]' : 'border-[var(--border)] text-[var(--text-muted)]']"
            @click="agentSystem = sys.key as typeof agentSystem"
          >{{ sys.label }}</button>
        </div>
        <div class="rounded-lg border border-[var(--border)] bg-[var(--bg-base)] p-3">
          <p class="text-[10px] text-[var(--text-muted)] uppercase tracking-wide mb-1">{{ t('devices.wizard.installCommand') }}</p>
          <code class="text-xs text-[var(--primary)] font-mono select-all">pip install hubex-agent && hubex-agent --server {{ window.location.origin }}</code>
        </div>
        <div class="flex justify-between mt-2">
          <button class="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]" @click="step = 'name'">{{ t('devices.wizard.skip') }} →</button>
          <UButton size="sm" @click="step = 'name'">{{ t('common.next') }}</UButton>
        </div>
      </template>
    </div>

    <!-- ── Step 2b: Pairing (Hardware only, live status) ──────────────── -->
    <div v-else-if="step === 'pairing'" class="space-y-4">
      <div class="flex items-center gap-2 mb-2">
        <button class="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]" @click="goBack">← {{ t('devices.wizard.back') }}</button>
        <span class="text-xs font-semibold" :style="{ color: currentCat?.color }">{{ currentCat?.label }}</span>
      </div>

      <!-- Error display when pairing failed before code was generated -->
      <div v-if="!pairingCode && pairingStatus === 'error'" class="text-center space-y-4 py-6">
        <div class="h-12 w-12 mx-auto rounded-xl bg-[var(--status-bad)]/10 flex items-center justify-center">
          <svg class="h-6 w-6 text-[var(--status-bad)]" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
        </div>
        <p class="text-sm text-[var(--status-bad)]">{{ pairingError || 'Pairing could not be started. Check the Device UID and try again.' }}</p>
        <UButton size="sm" variant="secondary" @click="step = 'setup'">{{ t('devices.wizard.back') }}</UButton>
      </div>

      <!-- Waiting indicator when no code yet -->
      <div v-else-if="!pairingCode && pairingStatus === 'waiting'" class="text-center space-y-4 py-6">
        <span class="h-3 w-3 rounded-full bg-[var(--primary)] animate-pulse inline-block" />
        <p class="text-sm text-[var(--text-muted)]">Starting pairing...</p>
      </div>

      <!-- Pairing code display -->
      <div v-else-if="pairingCode" class="text-center space-y-4">
        <p class="text-sm text-[var(--text-muted)]">{{ t('devices.wizard.pairingCodeHint') }}</p>

        <!-- Big code display -->
        <div class="py-4 px-6 rounded-xl border-2 border-dashed border-[var(--primary)]/40 bg-[var(--primary)]/5 inline-block">
          <p class="text-3xl font-mono font-bold tracking-[0.3em] text-[var(--primary)]">{{ pairingCode }}</p>
        </div>

        <!-- QR Code -->
        <div v-if="pairingQrSvg" class="flex justify-center" v-html="pairingQrSvg" />

        <!-- Status indicator -->
        <div class="flex items-center justify-center gap-2 py-2">
          <template v-if="pairingStatus === 'waiting'">
            <span class="h-2 w-2 rounded-full bg-[var(--primary)] animate-pulse" />
            <span class="text-sm text-[var(--text-muted)]">{{ t('devices.wizard.waitingForDevice') }}</span>
          </template>
          <template v-else-if="pairingStatus === 'confirmed'">
            <svg class="h-5 w-5 text-[var(--status-ok)]" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
            <span class="text-sm font-semibold text-[var(--status-ok)]">{{ t('devices.wizard.connectionEstablished') }}</span>
          </template>
          <template v-else-if="pairingStatus === 'expired'">
            <span class="text-sm text-[var(--status-bad)]">{{ t('devices.wizard.pairingExpired') }}</span>
            <UButton size="sm" variant="secondary" @click="startPairing">{{ t('common.refresh') }}</UButton>
          </template>
          <template v-else-if="pairingStatus === 'error'">
            <span class="text-sm text-[var(--status-bad)]">{{ pairingError }}</span>
          </template>
        </div>
      </div>

      <!-- Skip to manual creation -->
      <div class="flex justify-between mt-4">
        <button class="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]" @click="step = 'name'">{{ t('devices.wizard.skip') }} →</button>
      </div>
    </div>

    <!-- ── Step 3: Name ───────────────────────────────────────────────── -->
    <div v-else-if="step === 'name'" class="space-y-4">
      <div class="flex items-center gap-2 mb-2">
        <button class="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]" @click="goBack">← {{ t('devices.wizard.back') }}</button>
        <span class="text-xs font-semibold" :style="{ color: currentCat?.color }">{{ currentCat?.label }}</span>
      </div>
      <p class="text-sm text-[var(--text-muted)]">{{ t('devices.wizard.nameYourDevice') }}</p>
      <UInput v-model="deviceName" :label="t('common.name')" :placeholder="t('devices.wizard.namePlaceholder')" autofocus />
      <button class="text-[10px] text-[var(--text-muted)] hover:text-[var(--primary)]" @click="showAdvanced = !showAdvanced">
        {{ showAdvanced ? '▾' : '▸' }} {{ t('devices.wizard.addLocation') }}
      </button>
      <UInput v-if="showAdvanced" v-model="deviceLocation" :placeholder="t('devices.wizard.locationPlaceholder')" />
      <div v-if="error" class="text-xs text-[var(--status-bad)] px-3 py-2 rounded-lg bg-[var(--status-bad)]/10">{{ error }}</div>
      <div class="flex justify-between mt-4">
        <button class="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]" @click="closeWizard">{{ t('common.cancel') }}</button>
        <UButton size="sm" :loading="saving" @click="createDevice">{{ t('devices.wizard.createDevice') }}</UButton>
      </div>
    </div>

    <!-- ── Step 4: Done ───────────────────────────────────────────────── -->
    <div v-else-if="step === 'done'" class="space-y-5 text-center py-4">
      <div class="h-14 w-14 mx-auto rounded-xl bg-[var(--status-ok)]/10 flex items-center justify-center">
        <svg class="h-7 w-7 text-[var(--status-ok)]" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
        </svg>
      </div>
      <div>
        <h3 class="text-base font-semibold text-[var(--text-primary)]">{{ t('devices.wizard.done') }}</h3>
        <p class="text-sm text-[var(--text-muted)] mt-1">{{ t('devices.wizard.doneMessage', { name: deviceName || 'Device' }) }}</p>
      </div>
      <div class="grid grid-cols-3 gap-3">
        <button class="flex flex-col items-center gap-2 p-3 rounded-xl border border-[var(--border)] bg-[var(--bg-raised)] hover:border-[var(--primary)]/40 transition-colors" @click="goToDevice">
          <svg class="h-5 w-5 text-[var(--primary)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" /></svg>
          <span class="text-[10px] font-medium text-[var(--text-primary)]">{{ t('devices.wizard.viewData') }}</span>
        </button>
        <button class="flex flex-col items-center gap-2 p-3 rounded-xl border border-[var(--border)] bg-[var(--bg-raised)] hover:border-[var(--primary)]/40 transition-colors" @click="goToAutomation">
          <svg class="h-5 w-5 text-[var(--primary)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" /></svg>
          <span class="text-[10px] font-medium text-[var(--text-primary)]">{{ t('devices.wizard.createAutomation') }}</span>
        </button>
        <button class="flex flex-col items-center gap-2 p-3 rounded-xl border border-[var(--border)] bg-[var(--bg-raised)] hover:border-[var(--primary)]/40 transition-colors" @click="goToDashboard">
          <svg class="h-5 w-5 text-[var(--primary)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625" /></svg>
          <span class="text-[10px] font-medium text-[var(--text-primary)]">{{ t('devices.wizard.createDashboard') }}</span>
        </button>
      </div>
    </div>
  </UModal>
</template>
