<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiFetch } from "../lib/api";
import { mapErrorToUserText, parseApiError } from "../lib/errors";

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
type DeviceLookup = {
  device_uid: string;
  device_id: number;
  claimed: boolean;
};

const error = ref("");
const pairingSection = ref<HTMLElement | null>(null);
const pairingConfirmInput = ref<HTMLInputElement | null>(null);
const route = useRoute();
const router = useRouter();

const pairingDeviceUid = ref("");
const pairingStartCode = ref("");
const pairingConfirmCode = ref("");
const pairingExpiresAt = ref<string | null>(null);
const startingPairing = ref(false);
const confirmingPairing = ref(false);
const pairingRemainingSeconds = ref<number | null>(null);
const pairingExpired = ref(false);
const searchQuery = ref("");
const sortBy = ref<"last_seen" | "state" | "health">("last_seen");
const actionableOnly = ref(false);

const pairingLookup = ref<DeviceLookup | null>(null);
const pairingLookupStatus = ref<"idle" | "loading" | "found" | "not_found" | "error">("idle");

const pairingDevice = computed(() => {
  const uid = pairingDeviceUid.value.trim();
  if (!uid) return null;
  return devices.value.find((d) => d.device_uid === uid) ?? null;
});

const pairingStateWarning = computed(() => {
  if (!pairingDeviceUid.value.trim()) return null;
  if (pairingLookupStatus.value === "not_found") return "Unknown device UID";
  if (!pairingDevice.value) {
    if (pairingLookupStatus.value === "found" && pairingLookup.value?.claimed) {
      return "Device already claimed";
    }
    return null;
  }
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
  if (pairingDevice.value) return pairingDevice.value.state === "provisioned_unclaimed";
  if (pairingLookupStatus.value !== "found") return false;
  return pairingLookup.value?.claimed === false;
});

const canConfirmPairing = computed(() => {
  if (confirmingPairing.value) return false;
  if (!pairingStartCode.value || !pairingConfirmCode.value) return false;
  if (pairingExpired.value) return false;
  if (pairingDevice.value) {
    return !["busy", "claimed", "unprovisioned"].includes(pairingDevice.value.state);
  }
  if (pairingLookupStatus.value !== "found") return false;
  return pairingLookup.value?.claimed === false;
});

const visibleDevices = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  let list = devices.value.slice();
  if (q) {
    list = list.filter((d) => d.device_uid.toLowerCase().includes(q));
  }
  if (actionableOnly.value) {
    list = list.filter((d) => ["provisioned_unclaimed", "pairing_active"].includes(d.state));
  }
  const statePriority: Record<Device["state"], number> = {
    busy: 5,
    pairing_active: 4,
    provisioned_unclaimed: 3,
    claimed: 2,
    unprovisioned: 1,
  };
  const healthPriority: Record<Device["health"], number> = {
    ok: 3,
    stale: 2,
    dead: 1,
  };
  if (sortBy.value === "last_seen") {
    list.sort((a, b) => {
      const av = a.last_seen_age_seconds ?? Number.POSITIVE_INFINITY;
      const bv = b.last_seen_age_seconds ?? Number.POSITIVE_INFINITY;
      return av - bv;
    });
  } else if (sortBy.value === "state") {
    list.sort((a, b) => statePriority[b.state] - statePriority[a.state]);
  } else if (sortBy.value === "health") {
    list.sort((a, b) => healthPriority[b.health] - healthPriority[a.health]);
  }
  return list;
});

let timer: number | null = null;
let pairingTimer: number | null = null;
let lookupTimer: number | null = null;

async function load(opts?: { silent?: boolean }) {
  if (opts?.silent !== true) {
    error.value = "";
  }
  try {
    devices.value = await apiFetch<Device[]>("/api/v1/devices");
  } catch (err: any) {
    error.value = formatPairingError(err, "Failed to load devices");
  }
}

async function lookupDevice(uid: string) {
  pairingLookupStatus.value = "loading";
  pairingLookup.value = null;
  try {
    const res = await apiFetch<DeviceLookup>(`/api/v1/devices/lookup/${encodeURIComponent(uid)}`);
    pairingLookup.value = res;
    pairingLookupStatus.value = "found";
  } catch (err: any) {
    const info = parseApiError(err);
    if (info.httpStatus === 404) {
      pairingLookupStatus.value = "not_found";
      pairingLookup.value = null;
      return;
    }
    pairingLookupStatus.value = "error";
    error.value = formatPairingError(err, "Failed to lookup device");
  }
}

function scheduleLookup(uid: string) {
  if (lookupTimer !== null) {
    window.clearTimeout(lookupTimer);
    lookupTimer = null;
  }
  const trimmed = uid.trim();
  if (!trimmed) {
    pairingLookupStatus.value = "idle";
    pairingLookup.value = null;
    return;
  }
  lookupTimer = window.setTimeout(() => {
    lookupTimer = null;
    lookupDevice(trimmed);
  }, 300);
}

function truncate(text: string, max = 300) {
  if (text.length <= max) return text;
  return text.slice(0, max) + "...";
}

function formatPairingError(err: any, fallback: string): string {
  const info = parseApiError(err);
  const mapped = mapErrorToUserText(info, fallback);
  const statusLabel = info.httpStatus ? `HTTP ${info.httpStatus}` : "HTTP ?";
  const detailText = truncate(info.message || "");
  const codeText = info.code ? ` ${info.code}` : "";
  const metaText = info.meta ? ` ${JSON.stringify(info.meta)}` : "";
  const suffix = detailText ? `${statusLabel}: ${detailText}` : statusLabel;
  if (mapped !== fallback) return `${mapped} (${suffix}${codeText}${metaText})`;
  return `${fallback} (${suffix}${codeText}${metaText})`;
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
    pairingStartCode.value = "";
    pairingExpiresAt.value = null;
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
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
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

function stateClass(state: Device["state"]) {
  if (state === "busy" || state === "unprovisioned") return "pill-bad";
  if (state === "claimed") return "pill-ok";
  if (state === "pairing_active" || state === "provisioned_unclaimed") return "pill-warn";
  return "pill-warn";
}

function onRowAction(device: Device) {
  if (device.state === "claimed") {
    router.push(`/devices/${device.id}`);
    return;
  }
  pairingDeviceUid.value = device.device_uid;
  pairingSection.value?.scrollIntoView({ behavior: "smooth", block: "start" });
  if (device.state === "pairing_active") {
    requestAnimationFrame(() => {
      pairingConfirmInput.value?.focus();
    });
  }
  if (device.state === "provisioned_unclaimed") {
    startPairing();
  }
}

function rowActionLabel(device: Device) {
  switch (device.state) {
    case "unprovisioned":
      return "Waiting for first contact";
    case "provisioned_unclaimed":
      return "Start pairing";
    case "pairing_active":
      return "Continue pairing";
    case "claimed":
      return "Open";
    case "busy":
      return "Busy";
    default:
      return "Open";
  }
}

function rowActionDisabled(device: Device) {
  return device.state === "unprovisioned" || device.state === "busy";
}

watch(pairingDeviceUid, () => {
  pairingStartCode.value = "";
  pairingConfirmCode.value = "";
  pairingExpiresAt.value = null;
  pairingRemainingSeconds.value = null;
  pairingExpired.value = false;
  stopPairingCountdown();
  scheduleLookup(pairingDeviceUid.value);
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
  const uid = typeof route.query.uid === "string" ? route.query.uid : "";
  if (uid) {
    pairingDeviceUid.value = uid;
    pairingSection.value?.scrollIntoView({ behavior: "smooth", block: "start" });
    requestAnimationFrame(() => {
      pairingConfirmInput.value?.focus();
    });
  }
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
  if (lookupTimer !== null) {
    window.clearTimeout(lookupTimer);
    lookupTimer = null;
  }
  stopPairingCountdown();
});
</script>

<template>
  <div class="card">
    <h2>Devices</h2>
    <div v-if="error" class="error">{{ error }}</div>

    <div ref="pairingSection" class="pairing-section">
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
      <div v-if="pairingExpired" class="pairing-expired">
        Expired. Start pairing again.
      </div>

      <div v-if="pairingStartCode" class="pairing-row">
        <span class="code-badge">
          {{ pairingStartCode }}
          <span v-if="pairingRemainingSeconds !== null" class="pairing-countdown-inline">
            {{ fmtRemaining(pairingRemainingSeconds) }}
          </span>
        </span>
        <input
          v-model="pairingConfirmCode"
          ref="pairingConfirmInput"
          class="input pairing-input"
          placeholder="Pairing code"
        />
        <button class="btn secondary" :disabled="!canConfirmPairing" @click="confirmPairing">
          {{ confirmingPairing ? "Confirming..." : "Confirm" }}
        </button>
      </div>
      <div v-if="pairingStartCode && !pairingExpired" class="pairing-countdown">
        <span>Expires in: {{ fmtRemaining(pairingRemainingSeconds) }}</span>
      </div>
      <div v-if="pairingExpiresAt" class="pairing-help">
        Expires: {{ fmtIso(pairingExpiresAt) }}
      </div>
    </div>

    <div class="toolbar">
      <input
        v-model="searchQuery"
        class="input toolbar-input"
        placeholder="Search UID"
      />
      <select v-model="sortBy" class="input toolbar-select">
        <option value="last_seen">Last seen (newest)</option>
        <option value="state">State priority</option>
        <option value="health">Health</option>
      </select>
      <label class="toolbar-toggle">
        <input type="checkbox" v-model="actionableOnly" />
        Show only actionable
      </label>
    </div>

    <table v-if="visibleDevices.length" class="table">
      <thead>
        <tr>
          <th>UID</th>
          <th>Health</th>
          <th>State</th>
          <th>Online</th>
          <th>Last seen</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="d in visibleDevices" :key="d.id">
          <td>
            <router-link :to="`/devices/${d.id}`">
              {{ d.device_uid }}
            </router-link>
          </td>
          <td>
            <span :class="['pill', healthClass(d.health)]">
              {{ d.health }}
            </span>
          </td>
          <td>
            <span :class="['pill', stateClass(d.state)]">
              {{ d.state }}
            </span>
          </td>
          <td>
            <span :class="['pill', d.online ? 'pill-ok' : 'pill-bad']">
              {{ d.online ? "online" : "offline" }}
            </span>
          </td>
          <td>
            {{ fmtTime(d.last_seen) }}
            <span v-if="d.last_seen_age_seconds !== null">({{ fmtAge(d.last_seen_age_seconds) }})</span>
          </td>
          <td>
            <button
              class="btn cta-btn"
              :disabled="rowActionDisabled(d)"
              @click="onRowAction(d)"
            >
              {{ rowActionLabel(d) }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else>No devices.</div>
  </div>
</template>
