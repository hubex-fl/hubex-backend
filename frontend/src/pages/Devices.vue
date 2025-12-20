<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { apiFetch } from "../lib/api";

type Device = {
  id: number;
  device_uid: string;
  claimed: boolean;
  last_seen: string | null;
  online: boolean;
  health: "ok" | "stale" | "dead";
  last_seen_age_seconds: number | null;
  state: "unprovisioned" | "provisioned_unclaimed" | "pairing_active" | "claimed" | "busy";
  pairing_active: boolean;
  busy: boolean;
};

const devices = ref<Device[]>([]);
const error = ref("");

const pairingDeviceUid = ref("");
const pairingStartCode = ref("");
const pairingConfirmCode = ref("");
const pairingExpiresAt = ref<string | null>(null);
const startingPairing = ref(false);
const confirmingPairing = ref(false);
const pairingRemainingSeconds = ref<number | null>(null);
const pairingExpired = ref(false);

const pairingDevice = computed(() => {
  const uid = pairingDeviceUid.value.trim();
  if (!uid) return null;
  return devices.value.find((d) => d.device_uid === uid) ?? null;
});

const pairingStateWarning = computed(() => {
  if (!pairingDeviceUid.value.trim()) return null;
  if (!pairingDevice.value) return "Unknown device UID";
  switch (pairingDevice.value.state) {
    case "unprovisioned":
      return "Device not provisioned (never seen)";
    case "busy":
      return "Device busy (task running)";
    case "claimed":
      return "Device already claimed";
    case "pairing_active":
      return "Pairing already active";
    default:
      return null;
  }
});

const canStartPairing = computed(() => {
  if (startingPairing.value) return false;
  if (!pairingDeviceUid.value.trim()) return false;
  return pairingDevice.value?.state === "provisioned_unclaimed";
});

const canConfirmPairing = computed(() => {
  if (confirmingPairing.value) return false;
  if (!pairingStartCode.value || !pairingConfirmCode.value) return false;
  if (pairingExpired.value) return false;
  if (!pairingDevice.value) return false;
  return !["busy", "claimed", "unprovisioned"].includes(pairingDevice.value.state);
});

let timer: number | null = null;
let pairingTimer: number | null = null;

async function load(opts?: { silent?: boolean }) {
  if (opts?.silent !== true) {
    error.value = "";
  }
  try {
    devices.value = await apiFetch<Device[]>("/api/v1/devices");
  } catch (err: any) {
    error.value = err?.message || "Failed to load devices";
  }
}

function mapPairingError(codeOrMessage: string, fallback: string): string {
  const msg = String(codeOrMessage || "").toLowerCase();
  if (msg.includes("device_not_found")) return "Unknown device UID";
  if (msg.includes("device_not_provisioned")) return "Device not provisioned (never seen)";
  if (msg.includes("device_already_claimed")) return "Device already claimed";
  if (msg.includes("device_busy")) return "Device busy (task running)";
  if (msg.includes("pairing_code_not_found")) return "Invalid pairing code";
  if (msg.includes("pairing_code_expired")) return "Pairing code expired";
  if (msg.includes("pairing_code_used")) return "Pairing code already used";
  if (msg.includes("pairing code not found")) return "Invalid pairing code";
  if (msg.includes("pairing code expired")) return "Pairing code expired";
  if (msg.includes("pairing code already used")) return "Pairing code already used";
  if (msg.includes("device not found")) return "Unknown device UID";
  if (msg.includes("device not provisioned")) return "Device not provisioned (never seen)";
  if (msg.includes("device already claimed")) return "Device already claimed";
  if (msg.includes("device busy")) return "Device busy (task running)";
  if (msg.includes("401")) return "Not logged in (token expired). Refresh/login.";
  if (msg.includes("403")) return "Forbidden.";
  if (msg.includes("404")) return "Not found / wrong code.";
  if (msg.includes("409")) return "Conflict (already confirmed / replay).";
  if (msg.includes("410")) return "Expired. Start pairing again.";
  return fallback;
}

function truncate(text: string, max = 300) {
  if (text.length <= max) return text;
  return text.slice(0, max) + "...";
}

function extractErrorDetail(err: any) {
  const message = String(err?.message || "");
  let detail = message;
  let code: string | null = null;
  let status: string | null = null;
  let statusText: string | null = null;

  const httpMatch = message.match(/^HTTP\s+(\d{3})(?:\s+([^:]+))?:\s*([\s\S]*)$/i);
  if (httpMatch) {
    status = httpMatch[1];
    statusText = (httpMatch[2] || "").trim() || null;
    detail = httpMatch[3] || "";
  } else {
    const trimmed = message.trim();
    if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
      try {
        const parsed = JSON.parse(message);
        if (parsed && typeof parsed === "object" && "detail" in parsed) {
          const d = (parsed as any).detail;
          if (d && typeof d === "object") {
            code = String(d.code ?? "");
            detail = String(d.message ?? JSON.stringify(d));
          } else {
            detail = String(d ?? "");
          }
        }
      } catch {
        // keep message as detail
      }
    }
  }

  return { detail, status, statusText, code };
}

function formatPairingError(err: any, fallback: string): string {
  const info = extractErrorDetail(err);
  const codeOrMessage = info.code || info.detail || info.status || "";
  const mapped = mapPairingError(codeOrMessage, fallback);
  const statusLabel = info.status
    ? `HTTP ${info.status}${info.statusText ? " " + info.statusText : ""}`
    : "HTTP ?";
  const detailText = truncate(info.detail || "");
  const suffix = detailText ? `${statusLabel}: ${detailText}` : statusLabel;
  if (mapped !== fallback) {
    return `${mapped} (${suffix})`;
  }
  return `${fallback} (${suffix})`;
}

function stopPairingCountdown() {
  if (pairingTimer !== null) {
    window.clearInterval(pairingTimer);
    pairingTimer = null;
  }
}

function updatePairingCountdown() {
  if (!pairingStartCode.value || !pairingExpiresAt.value) {
    pairingRemainingSeconds.value = null;
    pairingExpired.value = false;
    stopPairingCountdown();
    return;
  }
  const now = Date.now();
  const expiresMs = new Date(pairingExpiresAt.value).getTime();
  if (!Number.isFinite(expiresMs)) {
    pairingRemainingSeconds.value = null;
    pairingExpired.value = false;
    stopPairingCountdown();
    return;
  }
  const remaining = Math.floor((expiresMs - now) / 1000);
  if (remaining <= 0) {
    pairingRemainingSeconds.value = 0;
    pairingExpired.value = true;
    stopPairingCountdown();
    return;
  }
  pairingRemainingSeconds.value = remaining;
  pairingExpired.value = false;
}

function startPairingCountdown() {
  stopPairingCountdown();
  updatePairingCountdown();
  if (pairingExpiresAt.value && pairingStartCode.value && !pairingExpired.value) {
    pairingTimer = window.setInterval(updatePairingCountdown, 1000);
  }
}

function fmtRemaining(seconds: number | null) {
  if (seconds === null) return "-";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

async function startPairing() {
  error.value = "";
  pairingStartCode.value = "";
  pairingConfirmCode.value = "";
  pairingExpiresAt.value = null;
  pairingExpired.value = false;
  pairingRemainingSeconds.value = null;
  stopPairingCountdown();
  const uid = pairingDeviceUid.value.trim();
  if (!uid) {
    error.value = "device_uid required";
    return;
  }
  if (!canStartPairing.value) return;
  startingPairing.value = true;
  try {
    const res: any = await apiFetch("/api/v1/devices/pairing/start", {
      method: "POST",
      body: JSON.stringify({ device_uid: uid }),
    });
    if (!res?.pairing_code) {
      throw new Error("pairing/start did not return pairing_code");
    }
    pairingStartCode.value = res.pairing_code;
    pairingConfirmCode.value = "";
    pairingExpiresAt.value = res.expires_at ?? null;
    pairingExpired.value = false;
    startPairingCountdown();
  } catch (err: any) {
    error.value = formatPairingError(err, "Failed to start pairing");
  } finally {
    startingPairing.value = false;
  }
}

async function confirmPairing() {
  error.value = "";
  const uid = pairingDeviceUid.value.trim();
  const code = pairingConfirmCode.value.trim();
  if (!uid) {
    error.value = "device_uid required";
    return;
  }
  if (!code) {
    error.value = "pairing_code required";
    return;
  }
  if (!canConfirmPairing.value) return;
  confirmingPairing.value = true;
  try {
    await apiFetch("/api/v1/devices/pairing/confirm", {
      method: "POST",
      body: JSON.stringify({ device_uid: uid, pairing_code: code }),
    });
    pairingDeviceUid.value = "";
    pairingStartCode.value = "";
    pairingConfirmCode.value = "";
    pairingExpiresAt.value = null;
    pairingExpired.value = false;
    pairingRemainingSeconds.value = null;
    stopPairingCountdown();
    await load();
  } catch (err: any) {
    error.value = formatPairingError(err, "Failed to confirm pairing");
  } finally {
    confirmingPairing.value = false;
  }
}

function fmtTime(iso: string | null) {
  if (!iso) return "-";
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

function fmtIso(iso: string | null) {
  if (!iso) return "-";
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

function fmtAge(seconds: number | null) {
  if (seconds === null || seconds === undefined) return "-";
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}

function healthClass(health: Device["health"]) {
  if (health === "ok") return "pill-ok";
  if (health === "stale") return "pill-warn";
  return "pill-bad";
}

watch(pairingDeviceUid, () => {
  pairingStartCode.value = "";
  pairingConfirmCode.value = "";
  pairingExpiresAt.value = null;
  pairingRemainingSeconds.value = null;
  pairingExpired.value = false;
  stopPairingCountdown();
});

function onVisibilityChange() {
  if (document.visibilityState === "visible") {
    updatePairingCountdown();
    if (pairingStartCode.value && !pairingExpired.value) {
      startPairingCountdown();
    }
    load({ silent: true });
  }
}

onMounted(() => {
  load();
  timer = window.setInterval(() => load({ silent: true }), 5000);
  document.addEventListener("visibilitychange", onVisibilityChange);
});

onUnmounted(() => {
  document.removeEventListener("visibilitychange", onVisibilityChange);
  if (timer !== null) {
    window.clearInterval(timer);
    timer = null;
  }
  stopPairingCountdown();
});
</script>

<template>
  <div class="card">
    <h2>Devices</h2>
    <div v-if="error" class="error">{{ error }}</div>

    <div class="pairing-section">
      <div class="pairing-row">
        <input
          v-model="pairingDeviceUid"
          class="input pairing-input"
          placeholder="Device UID"
        />
        <button class="btn" :disabled="!canStartPairing" @click="startPairing">
          {{ startingPairing ? "Starting..." : "Start pairing" }}
        </button>
      </div>
      <div v-if="pairingStateWarning" class="pairing-warn">
        {{ pairingStateWarning }}
      </div>

      <div v-if="pairingStartCode" class="pairing-row">
        <span class="code-badge">{{ pairingStartCode }}</span>
        <input
          v-model="pairingConfirmCode"
          class="input pairing-input"
          placeholder="Pairing code"
        />
        <button class="btn secondary" :disabled="!canConfirmPairing" @click="confirmPairing">
          {{ confirmingPairing ? "Confirming..." : "Confirm" }}
        </button>
      </div>
      <div v-if="pairingStartCode" class="pairing-countdown">
        <span v-if="pairingExpired" class="pairing-expired">Expired. Start pairing again.</span>
        <span v-else>Expires in: {{ fmtRemaining(pairingRemainingSeconds) }}</span>
      </div>
      <div v-if="pairingExpiresAt" class="pairing-help">
        Expires: {{ fmtIso(pairingExpiresAt) }}
      </div>
    </div>

    <table v-if="devices.length" class="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>UID</th>
          <th>Status</th>
          <th>Health</th>
          <th>Last seen</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="d in devices" :key="d.id">
          <td>{{ d.id }}</td>
          <td>
            <router-link :to="`/devices/${d.id}`">
              {{ d.device_uid }}
            </router-link>
          </td>
          <td>
            <span :class="['pill', d.online ? 'pill-ok' : 'pill-bad']">
              {{ d.online ? "online" : "offline" }}
            </span>
          </td>
          <td>
            <span :class="['pill', healthClass(d.health)]">
              {{ d.health }}
            </span>
          </td>
          <td>
            {{ fmtTime(d.last_seen) }}
            <span v-if="d.last_seen_age_seconds !== null">({{ fmtAge(d.last_seen_age_seconds) }})</span>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else>No devices.</div>
  </div>
</template>
