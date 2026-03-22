<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch, nextTick } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiFetch } from "../lib/api";
import { mapErrorToUserText, parseApiError } from "../lib/errors";
import { useCapabilities, hasCap } from "../lib/capabilities";

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
  __sig?: string;
};

const devices = ref<Device[]>([]);
type DeviceLookup = {
  device_uid: string;
  device_id: number;
  claimed: boolean;
};

const error = ref("");
const loading = ref(false);
const refreshing = ref(false);
const pairingSection = ref<HTMLElement | null>(null);
const pairingClaimInput = ref<HTMLInputElement | null>(null);
const route = useRoute();
const router = useRouter();
const caps = useCapabilities();

const pairingDeviceUid = ref("");
const claimingPairing = ref(false);
const pairingClaimCode = ref("");
const pairingClaimStatus = ref<string | null>(null);
const showUnclaimedAdmin = ref(false);
const searchQuery = ref("");
const sortBy = ref<"last_seen" | "state" | "health">("last_seen");
const filterBy = ref<
  "all" | "recent" | "claimed" | "unclaimed" | "claimable" | "offline" | "offline_old"
>("all");
const RECENT_SECONDS = 300;
const OFFLINE_OLD_SECONDS = 7 * 24 * 60 * 60;
const selectMode = ref<"unclaim" | "purge">("unclaim");
const selectedIds = ref<number[]>([]);
const bulkUnclaimBusy = ref(false);
const bulkUnclaimConfirm = ref(false);
const bulkUnclaimStatus = ref<Record<number, string>>({});
const bulkPurgeBusy = ref(false);
const bulkPurgeConfirm = ref(false);
const bulkPurgeConfirmText = ref("");
const bulkPurgeStatus = ref<Record<number, string>>({});

const pairingLookup = ref<DeviceLookup | null>(null);
const pairingLookupStatus = ref<"idle" | "loading" | "found" | "not_found" | "error">("idle");
const includeUnclaimed = computed(
  () => caps.status === "ready" && hasCap("cap.admin") && showUnclaimedAdmin.value
);
const canShowPurge = computed(() => caps.status === "ready" && hasCap("devices.purge"));

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
  if (!pairingDevice.value.online) {
    return "Device offline; pairing code will be visible on device dashboard when online.";
  }
  switch (pairingDevice.value.state) {
    case "unprovisioned":
      return "Device not provisioned (never seen)";
    case "busy":
      return "Device busy (task running)";
    case "claimed":
      return "Device already claimed";
    case "pairing_active":
      return "Pairing already active (check device dashboard)";
    default:
      return null;
  }
});

const canClaimPairing = computed(() => {
  if (claimingPairing.value) return false;
  if (caps.status !== "ready") return false;
  if (!hasCap("pairing.claim")) return false;
  if (!pairingDeviceUid.value.trim()) return false;
  return pairingClaimCode.value.trim().length > 0;
});

const selectableIds = computed(() => {
  const mode = selectMode.value;
  return visibleDevices.value
    .filter((d) => (mode === "unclaim" ? isBulkUnclaimable(d) : isBulkPurgeable(d)))
    .map((d) => d.id);
});

const allSelected = computed(() => {
  const ids = selectableIds.value;
  if (!ids.length) return false;
  return ids.every((id) => selectedIds.value.includes(id));
});

const canBulkUnclaim = computed(() => {
  if (bulkUnclaimBusy.value) return false;
  if (selectMode.value !== "unclaim") return false;
  if (caps.status !== "ready") return false;
  if (!hasCap("devices.unclaim")) return false;
  return selectedIds.value.length > 0;
});

const canBulkPurge = computed(() => {
  if (bulkPurgeBusy.value) return false;
  if (selectMode.value !== "purge") return false;
  if (caps.status !== "ready") return false;
  if (!hasCap("devices.purge")) return false;
  return selectedIds.value.length > 0;
});

const visibleDevices = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  let list = devices.value.slice();
  if (q) {
    list = list.filter((d) => d.device_uid.toLowerCase().includes(q));
  }
  if (filterBy.value === "claimed") {
    list = list.filter((d) => d.state === "claimed");
  } else if (filterBy.value === "recent") {
    list = list.filter(
      (d) => d.last_seen_age_seconds !== null && d.last_seen_age_seconds <= RECENT_SECONDS
    );
  } else if (filterBy.value === "unclaimed") {
    list = list.filter((d) => d.state !== "claimed");
  } else if (filterBy.value === "claimable") {
    list = list.filter((d) => !d.claimed && d.pairing_active);
  } else if (filterBy.value === "offline") {
    list = list.filter((d) => !d.online);
  } else if (filterBy.value === "offline_old") {
    list = list.filter(
      (d) =>
        !d.online &&
        d.last_seen_age_seconds !== null &&
        d.last_seen_age_seconds > OFFLINE_OLD_SECONDS
    );
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
let lookupTimer: number | null = null;
let refreshTimer: number | null = null;

function scheduleScrollRestore(y: number) {
  if (typeof window === "undefined") return;
  const schedule = typeof window.requestAnimationFrame === "function"
    ? window.requestAnimationFrame.bind(window)
    : (cb: FrameRequestCallback) => window.setTimeout(cb, 0);
  schedule(() => window.scrollTo({ top: y }));
}

function deviceSig(d: Device): string {
  return [
    d.id,
    d.device_uid,
    d.health,
    d.state,
    d.online,
    d.last_seen ?? "",
    d.pairing_active,
    d.busy,
  ].join("|");
}

function reconcileById<T extends { id: number; __sig?: string }>(
  target: T[],
  next: T[],
  sigFn: (item: T) => string
) {
  const byId = new Map<number, T>();
  for (const item of target) {
    byId.set(item.id, item);
  }
  const ordered: T[] = [];
  for (const item of next) {
    const existing = byId.get(item.id);
    if (existing) {
      const nextSig = sigFn(item);
      if (existing.__sig !== nextSig) {
        Object.assign(existing, item);
        existing.__sig = nextSig;
      }
      ordered.push(existing);
    } else {
      item.__sig = sigFn(item);
      ordered.push(item);
    }
  }
  target.splice(0, target.length, ...ordered);
}

async function load(opts?: { silent?: boolean }) {
  if (opts?.silent !== true) {
    error.value = "";
    loading.value = true;
  } else {
    refreshing.value = false;
    if (refreshTimer !== null) {
      window.clearTimeout(refreshTimer);
      refreshTimer = null;
    }
    refreshTimer = window.setTimeout(() => {
      refreshing.value = true;
    }, 350);
  }
  if (opts?.silent && document.visibilityState !== "visible") {
    if (refreshTimer !== null) {
      window.clearTimeout(refreshTimer);
      refreshTimer = null;
    }
    refreshing.value = false;
    return;
  }
  const scrollY = opts?.silent && typeof window !== "undefined" ? window.scrollY : 0;
  try {
    const path = includeUnclaimed.value
      ? "/api/v1/devices?include_unclaimed=1"
      : "/api/v1/devices";
    const next = await apiFetch<Device[]>(path);
    reconcileById(devices.value, next, deviceSig);
    const nextIds = new Set(next.map((d) => d.id));
    if (selectedIds.value.length) {
      selectedIds.value = selectedIds.value.filter((id) => nextIds.has(id));
    }
    if (opts?.silent) {
      await nextTick();
      scheduleScrollRestore(scrollY);
    }
  } catch (err: any) {
    error.value = formatPairingError(err, "Failed to load devices");
  } finally {
    loading.value = false;
    if (refreshTimer !== null) {
      window.clearTimeout(refreshTimer);
      refreshTimer = null;
    }
    refreshing.value = false;
  }
}

function isSelected(id: number) {
  return selectedIds.value.includes(id);
}

function isBulkUnclaimable(d: Device) {
  if (caps.status !== "ready") return false;
  if (!hasCap("devices.unclaim")) return false;
  return d.state === "claimed";
}

function isBulkPurgeable(d: Device) {
  if (caps.status !== "ready") return false;
  if (!canShowPurge.value) return false;
  return true;
}

function toggleSelectAll() {
  if (allSelected.value) {
    selectedIds.value = [];
    return;
  }
  selectedIds.value = selectableIds.value.slice();
}

function toggleRow(d: Device) {
  const selectable = selectMode.value === "unclaim" ? isBulkUnclaimable(d) : isBulkPurgeable(d);
  if (!selectable) return;
  const ids = new Set(selectedIds.value);
  if (ids.has(d.id)) {
    ids.delete(d.id);
  } else {
    ids.add(d.id);
  }
  selectedIds.value = Array.from(ids);
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

async function claimPairing() {
  const code = pairingClaimCode.value.trim();
  const uid = pairingDeviceUid.value.trim();
  if (!uid) {
    error.value = "device_uid required";
    return;
  }
  if (!code) {
    error.value = "pairing_code required";
    return;
  }
  if (caps.status !== "ready" || !hasCap("pairing.claim")) {
    error.value = "Missing capability: pairing.claim";
    return;
  }
  claimingPairing.value = true;
  pairingClaimStatus.value = null;
  try {
    const res: any = await apiFetch("/api/v1/devices/pairing/claim", {
      method: "POST",
      body: JSON.stringify({ pairing_code: code }),
    });
    pairingClaimStatus.value = res?.device_uid ? `Claimed ${res.device_uid}` : "Claimed";
    pairingClaimCode.value = "";
    pairingDeviceUid.value = "";
    pairingLookupStatus.value = "idle";
    pairingLookup.value = null;
    if (filterBy.value !== "all") {
      filterBy.value = "all";
    }
    await load({ silent: true });
    await router.replace("/devices");
  } catch (err: any) {
    error.value = formatPairingError(err, "Failed to claim pairing");
  } finally {
    claimingPairing.value = false;
  }
}

function startBulkUnclaimConfirm() {
  bulkUnclaimConfirm.value = true;
  bulkPurgeConfirm.value = false;
}

function cancelBulkUnclaimConfirm() {
  bulkUnclaimConfirm.value = false;
}

async function bulkUnclaim() {
  if (selectedIds.value.length === 0) return;
  bulkUnclaimBusy.value = true;
  bulkUnclaimStatus.value = {};
  const ids = selectedIds.value.slice();
  for (const id of ids) {
    try {
      const res: any = await apiFetch(`/api/v1/devices/${id}/unclaim`, {
        method: "POST",
      });
      bulkUnclaimStatus.value[id] = res?.device_uid
        ? `Unclaimed ${res.device_uid}`
        : "Unclaimed";
    } catch (err: any) {
      bulkUnclaimStatus.value[id] = formatPairingError(err, "Unclaim failed");
    }
  }
  selectedIds.value = [];
  bulkUnclaimConfirm.value = false;
  await load({ silent: true });
  bulkUnclaimBusy.value = false;
}

function startBulkPurgeConfirm() {
  bulkPurgeConfirm.value = true;
  bulkPurgeConfirmText.value = "";
  bulkUnclaimConfirm.value = false;
}

function cancelBulkPurgeConfirm() {
  bulkPurgeConfirm.value = false;
  bulkPurgeConfirmText.value = "";
}

async function bulkPurge() {
  if (selectedIds.value.length === 0) return;
  if (bulkPurgeConfirmText.value !== "PURGE") return;
  bulkPurgeBusy.value = true;
  bulkPurgeStatus.value = {};
  try {
    const res: any = await apiFetch("/api/v1/devices/purge", {
      method: "POST",
      body: JSON.stringify({ device_ids: selectedIds.value, reason: "ui" }),
    });
    const results = Array.isArray(res?.results) ? res.results : [];
    for (const item of results) {
      if (!item || typeof item.id !== "number") continue;
      bulkPurgeStatus.value[item.id] = item.ok ? "Purged" : item.error || "Purge failed";
    }
  } catch (err: any) {
    error.value = formatPairingError(err, "Bulk purge failed");
  } finally {
    selectedIds.value = [];
    bulkPurgeConfirm.value = false;
    bulkPurgeConfirmText.value = "";
    await load({ silent: true });
    bulkPurgeBusy.value = false;
  }
}

async function purgeDevice(device: Device) {
  if (caps.status !== "ready") return;
  if (!hasCap("devices.purge")) {
    error.value = "Missing capability: devices.purge";
    return;
  }
  const confirmText = window.prompt(
    `Permanently delete ${device.device_uid}? Type PURGE to confirm.`
  );
  if (confirmText !== "PURGE") return;
  try {
    await apiFetch(`/api/v1/devices/${device.id}/purge`, {
      method: "POST",
      body: JSON.stringify({ reason: "ui" }),
    });
    bulkPurgeStatus.value[device.id] = "Purged";
    await load({ silent: true });
  } catch (err: any) {
    bulkPurgeStatus.value[device.id] = formatPairingError(err, "Purge failed");
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
  let bucket = seconds;
  if (seconds < 60) {
    bucket = Math.floor(seconds / 5) * 5;
  } else if (seconds < 600) {
    bucket = Math.floor(seconds / 30) * 30;
  } else {
    bucket = Math.floor(seconds / 60) * 60;
  }
  if (bucket < 60) return `${bucket}s ago`;
  if (bucket < 3600) return `${Math.floor(bucket / 60)}m ago`;
  return `${Math.floor(bucket / 3600)}h ago`;
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

function stateLabel(device: Device) {
  if (!includeUnclaimed.value && device.state === "claimed") return "ready";
  return device.state;
}

function useUidFromRow(device: Device) {
  pairingDeviceUid.value = device.device_uid;
  const el = pairingSection.value;
  if (el && typeof el.scrollIntoView === "function") {
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function onRowAction(device: Device) {
  if (device.state === "claimed") {
    router.push(`/devices/${device.id}`);
    return;
  }
  useUidFromRow(device);
  requestAnimationFrame(() => {
    pairingClaimInput.value?.focus();
  });
}

function onRowClick(device: Device) {
  if (device.state !== "claimed") return;
  router.push(`/devices/${device.id}`);
}

function rowActionLabel(device: Device) {
  switch (device.state) {
    case "unprovisioned":
      return "Use UID";
    case "provisioned_unclaimed":
      return "Use UID";
    case "pairing_active":
      return "Use UID";
    case "claimed":
      return "Open";
    case "busy":
      return "Busy";
    default:
      return "Open";
  }
}

function rowActionDisabled(device: Device) {
  return device.state === "busy";
}

watch(pairingDeviceUid, () => {
  scheduleLookup(pairingDeviceUid.value);
});

watch(selectMode, () => {
  selectedIds.value = [];
  bulkUnclaimConfirm.value = false;
  bulkPurgeConfirm.value = false;
  bulkPurgeConfirmText.value = "";
});

watch(canShowPurge, () => {
  if (!canShowPurge.value && selectMode.value === "purge") {
    selectMode.value = "unclaim";
  }
});

watch(showUnclaimedAdmin, () => {
  if (!showUnclaimedAdmin.value) {
    if (filterBy.value === "unclaimed" || filterBy.value === "claimable" || filterBy.value === "claimed") {
      filterBy.value = "all";
    }
  }
  load();
});

function onVisibilityChange() {
  if (document.visibilityState === "visible") {
    load({ silent: true });
  }
}

onMounted(() => {
  const uid = typeof route.query.uid === "string" ? route.query.uid : "";
  if (uid) {
    pairingDeviceUid.value = uid;
    pairingSection.value?.scrollIntoView({ behavior: "smooth", block: "start" });
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
});
</script>

<template>
  <div class="card">
    <h2>Devices</h2>
    <div class="status-line">
      <span v-if="error" class="error">{{ error }}</span>
      <span v-else-if="refreshing" class="muted">Refreshing...</span>
    </div>

    <div ref="pairingSection" class="pairing-section">
      <div class="pairing-row">
        <input
          v-model="pairingDeviceUid"
          class="input pairing-input"
          placeholder="Device UID"
        />
      </div>
      <div v-if="pairingStateWarning" class="pairing-warn">
        {{ pairingStateWarning }}
      </div>
      <div class="pairing-row">
        <input
          v-model="pairingClaimCode"
          ref="pairingClaimInput"
          class="input pairing-input"
          placeholder="Pairing code (claim)"
        />
        <button class="btn secondary" :disabled="!canClaimPairing" @click="claimPairing">
          {{ claimingPairing ? "Claiming..." : "Claim" }}
        </button>
      </div>
      <div v-if="caps.status === 'ready' && !hasCap('pairing.claim')" class="muted">
        Missing capability: pairing.claim
      </div>
      <div v-if="pairingClaimStatus" class="pairing-help">
        {{ pairingClaimStatus }}
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
      <select v-model="filterBy" class="input toolbar-select" data-testid="devices-filter">
        <option value="all">All</option>
        <option value="recent">Active recently</option>
        <option v-if="includeUnclaimed" value="claimed">Claimed</option>
        <option v-if="includeUnclaimed" value="unclaimed">Unclaimed</option>
        <option v-if="includeUnclaimed" value="claimable">Claimable</option>
        <option value="offline">Offline</option>
        <option value="offline_old">Offline old</option>
      </select>
      <label
        v-if="caps.status === 'ready' && hasCap('cap.admin')"
        class="toolbar-toggle"
      >
        <input type="checkbox" v-model="showUnclaimedAdmin" />
        Show unclaimed (admin)
      </label>
      <span v-if="includeUnclaimed" class="muted">
        Admin view: including unclaimed devices.
      </span>
    </div>
    <div class="bulk-toolbar">
      <label class="toolbar-toggle">
        Mode:
        <select v-model="selectMode" class="input toolbar-select">
          <option value="unclaim">Cleanup (Unclaim)</option>
          <option v-if="canShowPurge" value="purge">Cleanup (Purge)</option>
        </select>
      </label>
      <label class="toolbar-toggle">
        <input type="checkbox" :checked="allSelected" @change="toggleSelectAll" />
        Select all
      </label>
      <template v-if="selectMode === 'unclaim'">
        <button
          v-if="!bulkUnclaimConfirm"
          class="btn secondary"
          :disabled="!canBulkUnclaim"
          @click="startBulkUnclaimConfirm"
        >
          Bulk unclaim
        </button>
        <button
          v-else
          class="btn danger"
          :disabled="bulkUnclaimBusy"
          @click="bulkUnclaim"
        >
          {{ bulkUnclaimBusy ? "Unclaiming..." : "Confirm unclaim" }}
        </button>
        <button
          v-if="bulkUnclaimConfirm"
          class="btn ghost"
          :disabled="bulkUnclaimBusy"
          @click="cancelBulkUnclaimConfirm"
        >
          Cancel
        </button>
        <span v-if="bulkUnclaimConfirm" class="muted">
          Unclaim {{ selectedIds.length }} devices? This revokes all device tokens.
        </span>
      </template>

      <template v-else>
        <button
          v-if="!bulkPurgeConfirm"
          class="btn danger"
          :disabled="!canBulkPurge"
          @click="startBulkPurgeConfirm"
        >
          Bulk purge
        </button>
        <div v-else class="bulk-confirm">
          <input
            v-model="bulkPurgeConfirmText"
            class="input"
            placeholder="Type PURGE to confirm"
          />
          <button
            class="btn danger"
            :disabled="bulkPurgeBusy || bulkPurgeConfirmText !== 'PURGE'"
            @click="bulkPurge"
          >
            {{ bulkPurgeBusy ? "Purging..." : "Confirm purge" }}
          </button>
          <button class="btn ghost" :disabled="bulkPurgeBusy" @click="cancelBulkPurgeConfirm">
            Cancel
          </button>
          <span class="muted">
            Permanently deletes {{ selectedIds.length }} devices and all related data.
          </span>
        </div>
      </template>
    </div>

    <table class="table table-fixed devices-table">
      <thead>
        <tr>
          <th class="col-select"></th>
          <th>UID</th>
          <th>Health</th>
          <th>State</th>
          <th>Online</th>
          <th>Last seen</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="error">
          <td colspan="7" class="muted">{{ error }}</td>
        </tr>
        <template v-else-if="loading && !visibleDevices.length">
          <tr v-for="n in 5" :key="`loading-${n}`">
            <td colspan="7" class="muted">Loading...</td>
          </tr>
        </template>
        <tr v-else-if="!visibleDevices.length">
          <td colspan="7" class="muted">No devices.</td>
        </tr>
        <template v-else>
          <tr
            v-for="d in visibleDevices"
            :key="d.id"
            v-memo="[d.__sig]"
            :class="d.state === 'claimed' ? 'row-clickable' : ''"
            @click="onRowClick(d)"
          >
            <td>
              <input
                type="checkbox"
                :checked="isSelected(d.id)"
                :disabled="selectMode === 'unclaim' ? !isBulkUnclaimable(d) : !isBulkPurgeable(d)"
                @change="toggleRow(d)"
                @click.stop
              />
            </td>
            <td>
              <router-link :to="`/devices/${d.id}`" @click.stop>
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
                {{ stateLabel(d) }}
              </span>
            </td>
            <td>
              <span :class="['pill', d.online ? 'pill-ok' : 'pill-bad']">
                {{ d.online ? "online" : "offline" }}
              </span>
            </td>
            <td>
              {{ fmtTime(d.last_seen) }}
              <span v-if="d.last_seen_age_seconds !== null" class="age"
                >({{ fmtAge(d.last_seen_age_seconds) }})</span
              >
            </td>
            <td>
              <button
                class="btn cta-btn"
                :disabled="rowActionDisabled(d)"
                @click.stop="onRowAction(d)"
              >
                {{ rowActionLabel(d) }}
              </button>
              <button
                v-if="d.state !== 'claimed'"
                class="btn ghost"
                @click.stop="useUidFromRow(d)"
              >
                Use UID
              </button>
              <button
              v-if="canShowPurge"
              class="btn danger"
              @click.stop="purgeDevice(d)"
            >
                Purge
              </button>
              <div v-if="bulkUnclaimStatus[d.id]" class="muted bulk-status">
                {{ bulkUnclaimStatus[d.id] }}
              </div>
              <div v-if="bulkPurgeStatus[d.id]" class="muted bulk-status">
                {{ bulkPurgeStatus[d.id] }}
              </div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.row-clickable {
  cursor: pointer;
}
.status-line {
  min-height: 24px;
  display: flex;
  align-items: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.bulk-confirm {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.bulk-status {
  margin-top: 4px;
}
.table-fixed {
  table-layout: fixed;
  width: 100%;
}
.col-select {
  width: 40px;
}
.devices-table th:nth-child(1),
.devices-table td:nth-child(1) {
  width: 40px;
}
.devices-table th:nth-child(2),
.devices-table td:nth-child(2) {
  width: 240px;
}
.devices-table th:nth-child(3),
.devices-table td:nth-child(3) {
  width: 90px;
}
.devices-table th:nth-child(4),
.devices-table td:nth-child(4) {
  width: 140px;
}
.devices-table th:nth-child(5),
.devices-table td:nth-child(5) {
  width: 90px;
}
.devices-table th:nth-child(6),
.devices-table td:nth-child(6) {
  width: 200px;
}
.devices-table th:nth-child(7),
.devices-table td:nth-child(7) {
  width: 180px;
}
.bulk-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 8px 0 12px;
}
.bulk-status {
  margin-top: 4px;
  font-size: 12px;
}
.devices-table th,
.devices-table td {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: middle;
}
.devices-table tbody tr {
  height: 36px;
}
.devices-table td {
  line-height: 36px;
}
.devices-table .pill {
  display: inline-block;
  white-space: nowrap;
}
.age {
  display: inline-block;
  min-width: 80px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  text-align: right;
}
</style>
