<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiFetch } from "../lib/api";
import { mapErrorToUserText, parseApiError } from "../lib/errors";
import { useCapabilities, hasCap } from "../lib/capabilities";
import { useDevices, DEVICE_TYPE_META } from "../composables/useDevices";
import type { Device, DeviceType } from "../composables/useDevices";
import UCard from "../components/ui/UCard.vue";
import UBadge from "../components/ui/UBadge.vue";
import UButton from "../components/ui/UButton.vue";
import UInput from "../components/ui/UInput.vue";
import USelect from "../components/ui/USelect.vue";
import USkeleton from "../components/ui/USkeleton.vue";
import UEmpty from "../components/ui/UEmpty.vue";
import UModal from "../components/ui/UModal.vue";
import UToggle from "../components/ui/UToggle.vue";
import ContextMenu from "../components/ContextMenu.vue";
import DeviceWizard from "../components/DeviceWizard.vue";
import { useConnectPanel } from "../composables/useConnectPanel";
import type { ContextMenuItem } from "../components/ContextMenu.vue";

const { open: openConnectPanel } = useConnectPanel();

// ── Device Wizard ──────────────────────────────────────────────────────────────
const showDeviceWizard = ref(false);
const wizardCategory = ref<"hardware" | "service" | "bridge" | "agent" | undefined>(undefined);

// ── Context menu per device card ──────────────────────────────────────────────
const openMenuId = ref<number | null>(null);

function toggleMenu(e: MouseEvent, deviceId: number) {
  e.stopPropagation();
  openMenuId.value = openMenuId.value === deviceId ? null : deviceId;
}

function closeMenu() {
  openMenuId.value = null;
}

function deviceMenuItems(d: Device): ContextMenuItem[] {
  return [
    {
      label: "View Details",
      icon: "M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z",
      action: () => router.push(`/devices/${d.id}`),
    },
    {
      label: "Connections",
      icon: "M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1",
      action: () =>
        openConnectPanel({
          type: "device",
          id: d.id,
          name: d.name || d.device_uid,
          deviceUid: d.device_uid,
          deviceId: d.id,
        }),
    },
    { label: "", icon: "", action: () => {}, divider: true },
    {
      label: "Alert Rules",
      icon: "M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0",
      action: () => router.push("/alerts"),
    },
    {
      label: "Automations",
      icon: "M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z",
      action: () => router.push("/automations"),
    },
    { label: "", icon: "", action: () => {}, divider: true },
    {
      label: "Unclaim",
      icon: "M13.5 10.5V6.75a4.5 4.5 0 119 0v3.75M3.75 21.75h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H3.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z",
      action: () => router.push(`/devices/${d.id}`),
      destructive: true,
      disabled: !d.claimed,
    },
  ];
}

const route = useRoute();
const router = useRouter();
const caps = useCapabilities();

// ── Capabilities ──────────────────────────────────────────────────────────────
const showUnclaimedAdmin = ref(false);
const includeUnclaimed = computed(
  () => caps.status === "ready" && hasCap("cap.admin") && showUnclaimedAdmin.value,
);
const canShowPurge = computed(() => caps.status === "ready" && hasCap("devices.purge"));

// ── Data / Polling ─────────────────────────────────────────────────────────────
const { devices, loading, error: fetchError, refreshing, reload } = useDevices(includeUnclaimed);
const isRefreshing = ref(false);
const actionError = ref("");
const displayError = computed(() => actionError.value || fetchError.value || "");

async function handleRefresh() {
  isRefreshing.value = true;
  actionError.value = "";
  try {
    await reload();
  } finally {
    isRefreshing.value = false;
  }
}

// ── Pairing ────────────────────────────────────────────────────────────────────
const pairingOpen = ref(false);
const pairingSectionEl = ref<HTMLElement | null>(null);
const pairingCodeRef = ref<HTMLElement | null>(null);
const pairingDeviceUid = ref("");
const pairingClaimCode = ref("");
const pairingClaimStatus = ref<string | null>(null);
const claimingPairing = ref(false);

type DeviceLookup = { device_uid: string; device_id: number; claimed: boolean };
const pairingLookup = ref<DeviceLookup | null>(null);
const pairingLookupStatus = ref<"idle" | "loading" | "found" | "not_found" | "error">("idle");
let lookupTimer: number | null = null;

// QR code: fetch SVG when pairing code is 8 chars
const pairingQrSvg = ref<string | null>(null);
const pairingQrLoading = ref(false);

watch(pairingClaimCode, async (code) => {
  pairingQrSvg.value = null;
  if (code.trim().length < 6) return;
  pairingQrLoading.value = true;
  try {
    const res = await fetch(`/api/v1/devices/pairing/${encodeURIComponent(code.trim())}/qr`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("hubex_access_token") ?? ""}` },
    });
    if (res.ok) {
      pairingQrSvg.value = await res.text();
    }
  } catch {
    // QR not available — silently ignore
  } finally {
    pairingQrLoading.value = false;
  }
});

// ── Toolbar ────────────────────────────────────────────────────────────────────
const searchQuery = ref("");
const sortBy = ref("last_seen");
const filterBy = ref("all");

const RECENT_SECONDS = 300;
const OFFLINE_OLD_SECONDS = 7 * 24 * 60 * 60;

const sortOptions = [
  { value: "last_seen", label: "Last seen" },
  { value: "state", label: "State priority" },
  { value: "health", label: "Health" },
];

const filterOptions = computed(() => {
  const opts: Array<{ value: string; label: string }> = [
    { value: "all", label: "All" },
    { value: "recent", label: "Recently active" },
  ];
  if (includeUnclaimed.value) {
    opts.push(
      { value: "claimed", label: "Claimed" },
      { value: "unclaimed", label: "Unclaimed" },
      { value: "claimable", label: "Claimable" },
    );
  }
  opts.push(
    { value: "offline", label: "Offline" },
    { value: "offline_old", label: "Offline (old)" },
  );
  // Device type filters (only show types that exist)
  const presentTypes = new Set(devices.value.map((d) => d.device_type));
  for (const dt of Object.keys(DEVICE_TYPE_META) as DeviceType[]) {
    if (dt !== "unknown" && presentTypes.has(dt)) {
      opts.push({ value: `type:${dt}`, label: DEVICE_TYPE_META[dt].label });
    }
  }
  return opts;
});

// ── Bulk / Selection ──────────────────────────────────────────────────────────
const selectMode = ref("unclaim");
const selectedIds = ref<number[]>([]);
const bulkUnclaimBusy = ref(false);
const bulkUnclaimConfirm = ref(false);
const bulkUnclaimStatus = ref<Record<number, string>>({});

const bulkPurgeBusy = ref(false);
const showBulkPurgeModal = ref(false);
const bulkPurgeConfirmText = ref("");
const bulkPurgeStatus = ref<Record<number, string>>({});

const showSinglePurgeModal = ref(false);
const singlePurgeDevice = ref<Device | null>(null);
const singlePurgeConfirmText = ref("");

const selectModeOptions = computed(() => {
  const opts: Array<{ value: string; label: string }> = [{ value: "unclaim", label: "Unclaim mode" }];
  if (canShowPurge.value) opts.push({ value: "purge", label: "Delete mode" });
  return opts;
});

// ── Derived ───────────────────────────────────────────────────────────────────
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
    return "Device offline — pairing code visible on device when online.";
  }
  switch (pairingDevice.value.state) {
    case "unprovisioned": return "Device not provisioned (never seen)";
    case "busy": return "Device busy (task running)";
    case "claimed": return "Device already claimed";
    case "pairing_active": return "Pairing already active (check device dashboard)";
    default: return null;
  }
});

const canClaimPairing = computed(() => {
  if (claimingPairing.value) return false;
  if (caps.status !== "ready" || !hasCap("pairing.claim")) return false;
  if (!pairingDeviceUid.value.trim()) return false;
  return pairingClaimCode.value.trim().length > 0;
});

const visibleDevices = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  let list = devices.value.slice();
  if (q) list = list.filter((d) =>
    d.device_uid.toLowerCase().includes(q) ||
    (DEVICE_TYPE_META[d.device_type as DeviceType]?.label ?? d.device_type).toLowerCase().includes(q),
  );

  switch (filterBy.value) {
    case "claimed":
      list = list.filter((d) => d.state === "claimed");
      break;
    case "recent":
      list = list.filter(
        (d) => d.last_seen_age_seconds !== null && d.last_seen_age_seconds <= RECENT_SECONDS,
      );
      break;
    case "unclaimed":
      list = list.filter((d) => d.state !== "claimed");
      break;
    case "claimable":
      list = list.filter((d) => !d.claimed && d.pairing_active);
      break;
    case "offline":
      list = list.filter((d) => !d.online);
      break;
    case "offline_old":
      list = list.filter(
        (d) =>
          !d.online &&
          d.last_seen_age_seconds !== null &&
          d.last_seen_age_seconds > OFFLINE_OLD_SECONDS,
      );
      break;
    default:
      if (filterBy.value.startsWith("type:")) {
        const dt = filterBy.value.slice(5);
        list = list.filter((d) => d.device_type === dt);
      }
      break;
  }

  const statePriority: Record<Device["state"], number> = {
    busy: 5, pairing_active: 4, provisioned_unclaimed: 3, claimed: 2, unprovisioned: 1,
  };
  const healthPriority: Record<Device["health"], number> = { ok: 3, stale: 2, dead: 1 };

  if (sortBy.value === "state") {
    list.sort((a, b) => statePriority[b.state] - statePriority[a.state]);
  } else if (sortBy.value === "health") {
    list.sort((a, b) => healthPriority[b.health] - healthPriority[a.health]);
  } else {
    list.sort(
      (a, b) => (a.last_seen_age_seconds ?? Infinity) - (b.last_seen_age_seconds ?? Infinity),
    );
  }
  return list;
});

function isBulkUnclaimable(d: Device) {
  return caps.status === "ready" && hasCap("devices.unclaim") && d.state === "claimed";
}

function isBulkPurgeable(_d: Device) {
  return caps.status === "ready" && canShowPurge.value;
}

const selectableIds = computed(() =>
  visibleDevices.value
    .filter((d) => (selectMode.value === "unclaim" ? isBulkUnclaimable(d) : isBulkPurgeable(d)))
    .map((d) => d.id),
);

const allSelected = computed(() => {
  const ids = selectableIds.value;
  return ids.length > 0 && ids.every((id) => selectedIds.value.includes(id));
});

const canBulkUnclaim = computed(
  () =>
    !bulkUnclaimBusy.value &&
    selectMode.value === "unclaim" &&
    caps.status === "ready" &&
    hasCap("devices.unclaim") &&
    selectedIds.value.length > 0,
);

const canBulkPurge = computed(
  () =>
    !bulkPurgeBusy.value &&
    selectMode.value === "purge" &&
    caps.status === "ready" &&
    canShowPurge.value &&
    selectedIds.value.length > 0,
);

// ── Helpers ───────────────────────────────────────────────────────────────────
function truncate(text: string, max = 300) {
  return text.length <= max ? text : `${text.slice(0, max)}...`;
}

function formatError(err: unknown, fallback: string): string {
  const info = parseApiError(err);
  const mapped = mapErrorToUserText(info, fallback);
  const status = info.httpStatus ? `HTTP ${info.httpStatus}` : "HTTP ?";
  const detail = truncate(info.message || "");
  const code = info.code ? ` ${info.code}` : "";
  const suffix = detail ? `${status}: ${detail}` : status;
  return mapped !== fallback ? `${mapped} (${suffix}${code})` : `${fallback} (${suffix}${code})`;
}

function fmtTime(iso: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function fmtAge(seconds: number | null) {
  if (seconds === null || seconds === undefined) return "";
  let s = seconds;
  if (s < 60) s = Math.floor(s / 5) * 5;
  else if (s < 600) s = Math.floor(s / 30) * 30;
  else s = Math.floor(s / 60) * 60;
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

function healthStatus(h: Device["health"]): "ok" | "warn" | "bad" {
  return h === "ok" ? "ok" : h === "stale" ? "warn" : "bad";
}

function stateStatus(s: Device["state"]): "ok" | "warn" | "bad" | "neutral" {
  if (s === "claimed") return "ok";
  if (s === "busy" || s === "unprovisioned") return "bad";
  if (s === "pairing_active" || s === "provisioned_unclaimed") return "warn";
  return "neutral";
}

function stateLabel(d: Device) {
  if (!includeUnclaimed.value && d.state === "claimed") return "ready";
  return d.state.replace(/_/g, " ");
}

function rowActionLabel(d: Device) {
  if (d.state === "claimed") return "Open";
  if (d.state === "busy") return "Busy";
  return "Use UID";
}

function isSelected(id: number) {
  return selectedIds.value.includes(id);
}

// ── Actions ───────────────────────────────────────────────────────────────────
function toggleSelectAll() {
  selectedIds.value = allSelected.value ? [] : selectableIds.value.slice();
}

function toggleRow(d: Device) {
  const ok = selectMode.value === "unclaim" ? isBulkUnclaimable(d) : isBulkPurgeable(d);
  if (!ok) return;
  const ids = new Set(selectedIds.value);
  ids.has(d.id) ? ids.delete(d.id) : ids.add(d.id);
  selectedIds.value = Array.from(ids);
}

async function lookupDevice(uid: string) {
  pairingLookupStatus.value = "loading";
  pairingLookup.value = null;
  try {
    const res = await apiFetch<DeviceLookup>(
      `/api/v1/devices/lookup/${encodeURIComponent(uid)}`,
    );
    pairingLookup.value = res;
    pairingLookupStatus.value = "found";
  } catch (err: unknown) {
    const info = parseApiError(err);
    if (info.httpStatus === 404) {
      pairingLookupStatus.value = "not_found";
      return;
    }
    pairingLookupStatus.value = "error";
    actionError.value = formatError(err, "Failed to lookup device");
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

async function claimPairing() {
  const code = pairingClaimCode.value.trim();
  const uid = pairingDeviceUid.value.trim();
  if (!uid || !code) return;
  if (caps.status !== "ready" || !hasCap("pairing.claim")) {
    actionError.value = "Missing capability: pairing.claim";
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
    if (filterBy.value !== "all") filterBy.value = "all";
    /* Small delay so the backend commit is visible, then force refresh */
    await new Promise((r) => setTimeout(r, 500));
    await reload();
  } catch (err: unknown) {
    actionError.value = formatError(err, "Failed to claim pairing");
  } finally {
    claimingPairing.value = false;
  }
}

function useUidFromRow(d: Device) {
  pairingDeviceUid.value = d.device_uid;
  pairingOpen.value = true;
  nextTick(() => {
    const el = pairingSectionEl.value;
    if (el && typeof el.scrollIntoView === "function") {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    pairingCodeRef.value?.querySelector<HTMLInputElement>("input")?.focus();
  });
}

function onRowAction(d: Device) {
  if (d.state === "claimed") {
    router.push(`/devices/${d.id}`);
    return;
  }
  useUidFromRow(d);
}

function onRowClick(d: Device) {
  if (d.state === "claimed") router.push(`/devices/${d.id}`);
}

// Bulk unclaim
function startBulkUnclaimConfirm() {
  bulkUnclaimConfirm.value = true;
}
function cancelBulkUnclaimConfirm() {
  bulkUnclaimConfirm.value = false;
}

async function bulkUnclaim() {
  if (!selectedIds.value.length) return;
  bulkUnclaimBusy.value = true;
  bulkUnclaimStatus.value = {};
  const ids = selectedIds.value.slice();
  for (const id of ids) {
    try {
      const res: any = await apiFetch(`/api/v1/devices/${id}/unclaim`, { method: "POST" });
      bulkUnclaimStatus.value[id] = res?.device_uid ? `Unclaimed ${res.device_uid}` : "Unclaimed";
    } catch (err: unknown) {
      bulkUnclaimStatus.value[id] = formatError(err, "Unclaim failed");
    }
  }
  selectedIds.value = [];
  bulkUnclaimConfirm.value = false;
  await reload();
  bulkUnclaimBusy.value = false;
}

// Bulk purge
function openBulkPurgeModal() {
  bulkPurgeConfirmText.value = "";
  showBulkPurgeModal.value = true;
}

async function bulkPurge() {
  if (!selectedIds.value.length || bulkPurgeConfirmText.value !== "DELETE") return;
  bulkPurgeBusy.value = true;
  try {
    const res: any = await apiFetch("/api/v1/devices/purge", {
      method: "POST",
      body: JSON.stringify({ device_ids: selectedIds.value, reason: "ui" }),
    });
    const results: any[] = Array.isArray(res?.results) ? res.results : [];
    for (const item of results) {
      if (!item || typeof item.id !== "number") continue;
      bulkPurgeStatus.value[item.id] = item.ok ? "Deleted" : item.error || "Delete failed";
    }
  } catch (err: unknown) {
    actionError.value = formatError(err, "Bulk purge failed");
  } finally {
    selectedIds.value = [];
    showBulkPurgeModal.value = false;
    bulkPurgeConfirmText.value = "";
    await reload();
    bulkPurgeBusy.value = false;
  }
}

// Single purge
function openSinglePurgeModal(d: Device) {
  singlePurgeDevice.value = d;
  singlePurgeConfirmText.value = "";
  showSinglePurgeModal.value = true;
}

async function confirmSinglePurge() {
  if (!singlePurgeDevice.value || singlePurgeConfirmText.value !== "DELETE") return;
  const d = singlePurgeDevice.value;
  try {
    await apiFetch(`/api/v1/devices/${d.id}/purge`, {
      method: "POST",
      body: JSON.stringify({ reason: "ui" }),
    });
    bulkPurgeStatus.value[d.id] = "Deleted";
    showSinglePurgeModal.value = false;
    singlePurgeDevice.value = null;
    await reload();
  } catch (err: unknown) {
    actionError.value = formatError(err, "Delete failed");
  }
}

// ── Watchers ──────────────────────────────────────────────────────────────────
watch(pairingDeviceUid, (v) => scheduleLookup(v));

watch(selectMode, () => {
  selectedIds.value = [];
  bulkUnclaimConfirm.value = false;
  bulkPurgeConfirmText.value = "";
});

watch(canShowPurge, (ok) => {
  if (!ok && selectMode.value === "purge") selectMode.value = "unclaim";
});

watch(showUnclaimedAdmin, (v) => {
  if (!v && ["unclaimed", "claimable", "claimed"].includes(filterBy.value)) {
    filterBy.value = "all";
  }
});

watch(devices, () => {
  if (!selectedIds.value.length) return;
  const validIds = new Set(devices.value.map((d) => d.id));
  selectedIds.value = selectedIds.value.filter((id) => validIds.has(id));
});

// ── View toggle (table / cards) ───────────────────────────────────────────────
const deviceView = ref<"table" | "cards">(
  (localStorage.getItem("hubex:device-view") as "table" | "cards") ?? "table"
);
watch(deviceView, (v) => localStorage.setItem("hubex:device-view", v));

const hasActiveFilter = computed(
  () => searchQuery.value.trim() !== "" || filterBy.value !== "all"
);

function cardHealthBorder(h: Device["health"]): string {
  if (h === "ok") return "var(--status-ok)";
  if (h === "stale") return "var(--status-warn)";
  return "var(--status-bad)";
}

function clearFilters() {
  searchQuery.value = "";
  filterBy.value = "all";
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(() => {
  const uid = typeof route.query.uid === "string" ? route.query.uid : "";
  if (uid) {
    pairingDeviceUid.value = uid;
    pairingOpen.value = true;
  }
  // Open Device Wizard if ?wizard=open
  if (route.query.wizard === "open") {
    showDeviceWizard.value = true;
    const cat = route.query.category as string;
    if (cat && ["hardware", "service", "bridge", "agent"].includes(cat)) {
      wizardCategory.value = cat as typeof wizardCategory.value;
    }
  }
  // On mobile, always expand pairing section by default
  if (window.innerWidth < 768) pairingOpen.value = true;
});

onUnmounted(() => {
  if (lookupTimer !== null) {
    window.clearTimeout(lookupTimer);
    lookupTimer = null;
  }
});
</script>

<template>
  <div class="space-y-6">

    <!-- ── 1. Page Header ──────────────────────────────────────────────────── -->
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-xl font-semibold text-[var(--text-primary)]">Devices</h1>
        <p class="text-xs text-[var(--text-muted)] mt-0.5 flex items-center gap-2">
          <span v-if="refreshing" class="text-[var(--text-muted)]">Refreshing...</span>
          <span v-else>
            Manage and pair IoT devices
            <span v-if="includeUnclaimed" class="ml-1 text-[var(--status-warn)]">
              — admin view (includes unclaimed)
            </span>
          </span>
        </p>
      </div>
      <div class="flex items-center gap-2">
        <UButton size="sm" @click="showDeviceWizard = true">
          <svg class="h-3.5 w-3.5 mr-1" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          + Device
        </UButton>
        <UButton size="sm" variant="secondary" :loading="isRefreshing" @click="handleRefresh">
          <svg v-if="!isRefreshing" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
          </svg>
          Refresh
        </UButton>
      </div>
    </div>

    <!-- ── 2. Error Banner ─────────────────────────────────────────────────── -->
    <div
      v-if="displayError"
      class="flex items-start gap-3 rounded-xl border border-[var(--status-bad)]/30 bg-[var(--status-bad-bg)] px-4 py-3"
    >
      <UBadge status="bad" class="shrink-0 mt-px">Error</UBadge>
      <p class="flex-1 text-sm text-[var(--status-bad)]">{{ displayError }}</p>
      <button
        class="shrink-0 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
        aria-label="Dismiss"
        @click="actionError = ''"
      >
        <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path d="M18 6 6 18M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- ── 3. Pairing Card (hidden — Wizard is primary flow now) ──────────── -->
    <div ref="pairingSectionEl" v-show="false">
      <UCard padding="none">
        <template #header>
          <div class="flex items-center gap-2">
            <svg class="h-4 w-4 text-[var(--primary)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244" />
            </svg>
            <span class="text-sm font-semibold text-[var(--text-primary)]">Pair Device</span>
            <UBadge v-if="pairingStateWarning && pairingOpen" status="warn" class="max-w-[14rem] truncate">
              {{ pairingStateWarning }}
            </UBadge>
          </div>
        </template>
        <template #actions>
          <!-- Collapse toggle: desktop only -->
          <UButton size="sm" variant="ghost" class="hidden md:flex" @click="pairingOpen = !pairingOpen">
            <svg
              class="h-4 w-4 transition-transform duration-200"
              :class="pairingOpen ? 'rotate-180' : ''"
              fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="m19 9-7 7-7-7" />
            </svg>
          </UButton>
        </template>

        <!-- Mobile: always visible; Desktop: collapsible via pairingOpen -->
        <div :class="['p-5 space-y-4', !pairingOpen ? 'md:hidden' : '']">
          <!-- First-time hint when list is empty -->
          <div
            v-if="!loading && devices.length === 0"
            class="flex items-center gap-2 text-xs text-[var(--primary)]"
          >
            <svg class="h-3.5 w-3.5 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7l-.996-.997a5.984 5.984 0 01-1.777-4.21" />
            </svg>
            First time here? Enter your device UID and pairing code to get started.
          </div>
          <!-- UID + code row -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="space-y-1.5">
              <UInput
                v-model="pairingDeviceUid"
                label="Device UID"
                placeholder="Device UID"
              />
              <div v-if="pairingDeviceUid.trim() && pairingLookupStatus !== 'idle'" class="flex items-center gap-1.5 min-h-[1.25rem]">
                <span v-if="pairingLookupStatus === 'loading'" class="text-xs text-[var(--text-muted)]">Looking up…</span>
                <UBadge v-else-if="pairingStateWarning" status="warn">{{ pairingStateWarning }}</UBadge>
                <UBadge v-else-if="pairingLookupStatus === 'found'" status="ok">Device found</UBadge>
              </div>
            </div>
            <div ref="pairingCodeRef" class="space-y-2">
              <UInput
                v-model="pairingClaimCode"
                label="Pairing Code"
                placeholder="Pairing code (claim)"
              />
              <!-- QR code: shown when code is entered and QR is available -->
              <div v-if="pairingQrSvg || pairingQrLoading" class="flex items-start gap-3">
                <div class="rounded-lg border border-[var(--border)] bg-white p-1 shrink-0 w-[88px] h-[88px] flex items-center justify-center">
                  <div v-if="pairingQrLoading" class="text-[var(--text-muted)] text-[10px]">…</div>
                  <!-- eslint-disable-next-line vue/no-v-html -->
                  <div v-else-if="pairingQrSvg" v-html="pairingQrSvg" class="w-full h-full" />
                </div>
                <p class="text-[11px] text-[var(--text-muted)] leading-relaxed pt-1">
                  Scan with a QR reader to auto-fill on devices that support it
                </p>
              </div>
            </div>
          </div>

          <!-- Claim action row -->
          <div class="flex items-center gap-3 flex-wrap">
            <UButton
              :loading="claimingPairing"
              :disabled="!canClaimPairing"
              @click="claimPairing"
            >
              {{ claimingPairing ? "Claiming…" : "Claim" }}
            </UButton>

            <UBadge v-if="pairingClaimStatus" status="ok">
              {{ pairingClaimStatus }}
            </UBadge>

            <span
              v-if="caps.status === 'ready' && !hasCap('pairing.claim')"
              class="text-xs text-[var(--text-muted)]"
            >
              Missing capability: pairing.claim
            </span>
          </div>
        </div>
      </UCard>
    </div>

    <!-- ── 4. Device Table Card ────────────────────────────────────────────── -->
    <UCard padding="none">
      <template #header>
        <div class="flex items-center gap-2">
          <svg class="h-4 w-4 text-[var(--text-muted)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 0 0 2.25-2.25V6.75a2.25 2.25 0 0 0-2.25-2.25H6.75A2.25 2.25 0 0 0 4.5 6.75v10.5a2.25 2.25 0 0 0 2.25 2.25zm.75-12h9v9h-9v-9z" />
          </svg>
          <span class="text-sm font-semibold text-[var(--text-primary)]">Devices</span>
        </div>
      </template>
      <template #actions>
        <UBadge v-if="!loading" status="neutral">
          {{
            visibleDevices.length === devices.length
              ? `${devices.length}`
              : `${visibleDevices.length} / ${devices.length}`
          }}
        </UBadge>
      </template>

      <!-- Toolbar -->
      <div class="px-4 py-3 border-b border-[var(--border)] flex flex-wrap items-end gap-3">
        <div class="flex-1 min-w-[10rem]">
          <UInput
            v-model="searchQuery"
            variant="search"
            placeholder="Search devices…"
          />
        </div>
        <USelect v-model="sortBy" :options="sortOptions" />
        <select
          v-model="filterBy"
          data-testid="devices-filter"
          class="input"
        >
          <option
            v-for="opt in filterOptions"
            :key="opt.value"
            :value="opt.value"
          >{{ opt.label }}</option>
        </select>
        <!-- View toggle -->
        <div class="flex rounded-lg border border-[var(--border)] overflow-hidden shrink-0">
          <button
            :class="['px-3 py-1.5 text-xs transition-colors', deviceView === 'table' ? 'bg-[var(--primary)]/10 text-[var(--primary)]' : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]']"
            title="Table view"
            @click="deviceView = 'table'"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" />
            </svg>
          </button>
          <button
            :class="['px-3 py-1.5 text-xs border-l border-[var(--border)] transition-colors', deviceView === 'cards' ? 'bg-[var(--primary)]/10 text-[var(--primary)]' : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]']"
            title="Card view"
            @click="deviceView = 'cards'"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Bulk mode toolbar (admin only) — compact inline bar -->
      <div
        v-if="caps.status === 'ready' && hasCap('cap.admin') && (canShowPurge || hasCap('devices.unclaim'))"
        class="px-4 py-1.5 border-b border-[var(--border)] flex items-center gap-3 text-xs text-[var(--text-muted)]"
      >
        <span class="text-[10px] uppercase tracking-wide font-semibold text-[var(--text-muted)]">Admin</span>
        <USelect v-model="selectMode" :options="selectModeOptions" class="w-28 text-xs" />
        <label class="flex items-center gap-1.5 cursor-pointer select-none">
          <input
            type="checkbox"
            class="h-3.5 w-3.5 rounded accent-[var(--primary)]"
            :checked="allSelected"
            :disabled="!selectableIds.length"
            @change="toggleSelectAll"
          />
          <span>Select all</span>
        </label>
        <span v-if="selectedIds.length" class="text-[var(--text-secondary)]">
          {{ selectedIds.length }} selected
        </span>
      </div>

      <!-- ── Table View ─────────────────────────────────────────────────────── -->
      <div v-if="deviceView === 'table'" class="overflow-x-auto">
        <table class="w-full text-sm border-collapse">
          <thead>
            <tr class="border-b border-[var(--border)] bg-[var(--bg-raised)]">
              <th class="w-10 px-4 py-3" />
              <th class="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)] text-left min-w-[200px]">
                Device
              </th>
              <th class="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)] text-left w-32">
                Type
              </th>
              <th class="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)] text-left w-24">
                Health
              </th>
              <th class="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)] text-left w-36">
                State
              </th>
              <th class="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)] text-left w-24">
                Online
              </th>
              <th class="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)] text-left min-w-[180px]">
                Last Seen
              </th>
              <th class="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)] text-left min-w-[140px]">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            <!-- Loading skeleton rows -->
            <template v-if="loading && !devices.length">
              <tr
                v-for="i in 5"
                :key="`sk-${i}`"
                class="border-b border-[var(--border)]"
              >
                <td class="px-4 py-3 w-10">
                  <div class="h-4 w-4 rounded animate-pulse bg-[var(--bg-raised)]" />
                </td>
                <td class="px-4 py-3">
                  <USkeleton height="1rem" width="160px" />
                </td>
                <td class="px-4 py-3">
                  <USkeleton height="1.25rem" width="56px" rounded="full" />
                </td>
                <td class="px-4 py-3">
                  <USkeleton height="1.25rem" width="72px" rounded="full" />
                </td>
                <td class="px-4 py-3">
                  <USkeleton height="1.25rem" width="56px" rounded="full" />
                </td>
                <td class="px-4 py-3">
                  <USkeleton height="1rem" width="120px" />
                </td>
                <td class="px-4 py-3">
                  <USkeleton height="1.75rem" width="64px" />
                </td>
              </tr>
            </template>

            <!-- Empty state (table view) -->
            <tr v-else-if="!visibleDevices.length">
              <td colspan="7" class="py-2">
                <UEmpty
                  v-if="hasActiveFilter"
                  title="No devices match"
                  description="Try adjusting your search or filter."
                  icon="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 15.803a7.5 7.5 0 0010.607 10.607z"
                >
                  <UButton size="sm" variant="secondary" @click="clearFilters">Clear filters</UButton>
                </UEmpty>
                <UEmpty
                  v-else
                  title="No devices connected yet"
                  description="Hardware, APIs, bridges, agents — everything connects here."
                  icon="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z"
                >
                  <UButton size="sm" @click="showDeviceWizard = true">Connect your first device</UButton>
                </UEmpty>
              </td>
            </tr>

            <!-- Data rows -->
            <template v-else>
              <tr
                v-for="d in visibleDevices"
                :key="d.id"
                v-memo="[d.__sig, isSelected(d.id)]"
                class="border-b border-[var(--border)] last:border-0 transition-colors hover:bg-[var(--bg-raised)]"
                :class="d.state === 'claimed' ? 'cursor-pointer' : 'cursor-default'"
                @click="onRowClick(d)"
              >
                <!-- Checkbox -->
                <td class="px-4 py-3 w-10">
                  <input
                    type="checkbox"
                    class="h-4 w-4 rounded accent-[var(--primary)]"
                    :checked="isSelected(d.id)"
                    :disabled="selectMode === 'unclaim' ? !isBulkUnclaimable(d) : !isBulkPurgeable(d)"
                    @change="toggleRow(d)"
                    @click.stop
                  />
                </td>

                <!-- UID -->
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <span
                      class="h-2 w-2 shrink-0 rounded-full"
                      :class="d.online ? 'bg-[var(--status-ok)] animate-pulse-slow' : 'bg-[var(--bg-raised)]'"
                    />
                    <router-link
                      :to="`/devices/${d.id}`"
                      class="text-xs text-[var(--text-primary)] hover:text-[var(--primary)] transition-colors truncate max-w-[220px]"
                      :class="d.name ? 'font-medium' : 'font-mono'"
                      :title="d.device_uid"
                      @click.stop
                    >
                      {{ d.name || d.device_uid }}
                    </router-link>
                    <span v-if="d.name" class="text-[10px] font-mono text-[var(--text-muted)] truncate max-w-[140px]">{{ d.device_uid }}</span>
                  </div>
                </td>

                <!-- Type -->
                <td class="px-4 py-3">
                  <div class="flex items-center gap-1.5">
                    <svg class="h-4 w-4 shrink-0" :style="{ color: DEVICE_TYPE_META[d.device_type as DeviceType]?.color ?? 'var(--text-muted)' }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                      <path :d="DEVICE_TYPE_META[d.device_type as DeviceType]?.icon ?? DEVICE_TYPE_META.unknown.icon" />
                    </svg>
                    <span class="text-xs text-[var(--text-secondary)]">{{ DEVICE_TYPE_META[d.device_type as DeviceType]?.label ?? d.device_type }}</span>
                  </div>
                </td>

                <!-- Health -->
                <td class="px-4 py-3">
                  <UBadge :status="healthStatus(d.health)">{{ d.health }}</UBadge>
                </td>

                <!-- State -->
                <td class="px-4 py-3">
                  <UBadge :status="stateStatus(d.state)">{{ stateLabel(d) }}</UBadge>
                </td>

                <!-- Online -->
                <td class="px-4 py-3">
                  <UBadge :status="d.online ? 'ok' : 'bad'" :pulse="d.online">
                    {{ d.online ? "online" : "offline" }}
                  </UBadge>
                </td>

                <!-- Last Seen -->
                <td class="px-4 py-3">
                  <div class="text-xs text-[var(--text-secondary)]">{{ fmtTime(d.last_seen) }}</div>
                  <div
                    v-if="d.last_seen_age_seconds !== null"
                    class="font-mono text-xs text-[var(--text-muted)]"
                  >
                    {{ fmtAge(d.last_seen_age_seconds) }}
                  </div>
                </td>

                <!-- Actions -->
                <td class="px-4 py-3">
                  <div class="flex items-center gap-1.5 flex-wrap">
                    <UButton
                      size="sm"
                      :variant="d.state === 'claimed' ? 'secondary' : 'ghost'"
                      :disabled="d.state === 'busy'"
                      @click.stop="onRowAction(d)"
                    >
                      {{ rowActionLabel(d) }}
                    </UButton>
                    <UButton
                      v-if="canShowPurge"
                      size="sm"
                      variant="danger"
                      @click.stop="openSinglePurgeModal(d)"
                    >
                      Delete
                    </UButton>
                    <span
                      v-if="bulkUnclaimStatus[d.id]"
                      class="text-xs text-[var(--status-ok)]"
                    >
                      {{ bulkUnclaimStatus[d.id] }}
                    </span>
                    <span
                      v-if="bulkPurgeStatus[d.id]"
                      class="text-xs"
                      :class="bulkPurgeStatus[d.id] === 'Deleted' ? 'text-[var(--status-ok)]' : 'text-[var(--status-bad)]'"
                    >
                      {{ bulkPurgeStatus[d.id] }}
                    </span>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- ── Card View ──────────────────────────────────────────────────────── -->
      <div v-else class="p-4">
        <!-- Skeleton cards -->
        <div v-if="loading && !devices.length" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          <div
            v-for="i in 8"
            :key="`csk-${i}`"
            class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-4 space-y-3"
          >
            <USkeleton height="1rem" width="70%" />
            <div class="flex gap-2">
              <USkeleton height="1.25rem" width="3rem" rounded="full" />
              <USkeleton height="1.25rem" width="4rem" rounded="full" />
            </div>
            <USkeleton height="0.75rem" width="50%" />
          </div>
        </div>

        <!-- Empty state cards -->
        <UEmpty
          v-else-if="!visibleDevices.length && hasActiveFilter"
          title="No devices match"
          description="Try adjusting your search or filter."
          icon="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 15.803a7.5 7.5 0 0010.607 10.607z"
        >
          <UButton size="sm" variant="secondary" @click="clearFilters">Clear filters</UButton>
        </UEmpty>
        <!-- Enhanced empty state: first-time guidance + direct action -->
        <div
          v-else-if="!visibleDevices.length"
          class="flex flex-col items-center text-center py-16 px-6 gap-6"
        >
          <div class="h-16 w-16 rounded-2xl bg-[var(--bg-raised)] flex items-center justify-center">
            <svg class="h-8 w-8 text-[var(--text-muted)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z" />
            </svg>
          </div>
          <div class="space-y-1.5 max-w-xs">
            <h3 class="text-base font-semibold text-[var(--text-primary)]">Connect your first device</h3>
            <p class="text-sm text-[var(--text-muted)]">
              Hardware, APIs, bridges, agents — everything connects here.
            </p>
          </div>
          <!-- Primary CTA → opens wizard -->
          <div class="flex flex-col sm:flex-row items-center gap-3">
            <UButton @click="showDeviceWizard = true">
              <svg class="h-4 w-4 mr-1.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
              Connect your first device
            </UButton>
          </div>
          <!-- Helpful hint -->
          <p class="text-xs text-[var(--text-muted)] max-w-sm">
            Devices auto-discover variables from telemetry and integrate with alerts &amp; automations out of the box.
          </p>
        </div>

        <!-- Device cards grid -->
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          <div
            v-for="d in visibleDevices"
            :key="d.id"
            v-memo="[d.__sig, isSelected(d.id)]"
            :class="[
              'rounded-xl border bg-[var(--bg-surface)] p-4 flex flex-col gap-3 transition-shadow hover:shadow-glow',
              d.state === 'claimed' ? 'cursor-pointer' : 'cursor-default',
              isSelected(d.id) ? 'border-[var(--primary)]/40 bg-[var(--primary)]/5' : 'border-[var(--border)]',
            ]"
            :style="{ borderLeftWidth: '3px', borderLeftColor: cardHealthBorder(d.health) }"
            @click="onRowClick(d)"
          >
            <!-- Card header: online dot + UID + actions -->
            <div class="flex items-start justify-between gap-2 min-w-0">
              <div class="flex items-center gap-2 min-w-0">
                <span
                  class="h-2 w-2 shrink-0 rounded-full mt-0.5"
                  :class="d.online ? 'bg-[var(--status-ok)] animate-pulse-slow' : 'bg-[var(--bg-raised)]'"
                />
                <span class="font-mono text-xs font-semibold text-[var(--text-primary)] truncate">
                  {{ d.name || d.device_uid }}
                </span>
              </div>
              <div class="flex items-center gap-1 shrink-0" @click.stop>
                <!-- Bulk checkbox -->
                <input
                  type="checkbox"
                  class="h-4 w-4 shrink-0 rounded accent-[var(--primary)]"
                  :checked="isSelected(d.id)"
                  :disabled="selectMode === 'unclaim' ? !isBulkUnclaimable(d) : !isBulkPurgeable(d)"
                  @change="toggleRow(d)"
                />
                <!-- Context menu trigger -->
                <div class="relative">
                  <button
                    class="h-6 w-6 flex items-center justify-center rounded text-[var(--text-muted)] hover:bg-[var(--bg-raised)] hover:text-[var(--text-primary)] transition-colors"
                    title="Actions"
                    @click="toggleMenu($event, d.id)"
                  >
                    <svg class="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 24 24">
                      <circle cx="12" cy="5" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="12" cy="19" r="1.5" />
                    </svg>
                  </button>
                  <ContextMenu
                    :items="deviceMenuItems(d)"
                    :open="openMenuId === d.id"
                    @close="closeMenu"
                  />
                </div>
              </div>
            </div>

            <!-- Device type -->
            <div class="flex items-center gap-1.5">
              <svg class="h-3.5 w-3.5 shrink-0" :style="{ color: DEVICE_TYPE_META[d.device_type as DeviceType]?.color ?? 'var(--text-muted)' }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path :d="DEVICE_TYPE_META[d.device_type as DeviceType]?.icon ?? DEVICE_TYPE_META.unknown.icon" />
              </svg>
              <span class="text-[10px] text-[var(--text-muted)]">{{ DEVICE_TYPE_META[d.device_type as DeviceType]?.label ?? d.device_type }}</span>
            </div>

            <!-- Badges -->
            <div class="flex gap-2 flex-wrap">
              <UBadge :status="healthStatus(d.health)">{{ d.health }}</UBadge>
              <UBadge :status="stateStatus(d.state)">{{ stateLabel(d) }}</UBadge>
            </div>

            <!-- Last seen -->
            <p class="text-xs text-[var(--text-muted)]">
              <span v-if="d.last_seen_age_seconds !== null" class="font-mono">{{ fmtAge(d.last_seen_age_seconds) }}</span>
              <span v-else>Never seen</span>
            </p>

            <!-- Action row -->
            <div class="flex gap-2 mt-auto pt-1">
              <UButton
                size="sm"
                :variant="d.state === 'claimed' ? 'secondary' : 'ghost'"
                :disabled="d.state === 'busy'"
                class="flex-1"
                @click.stop="onRowAction(d)"
              >
                {{ rowActionLabel(d) }}
              </UButton>
              <UButton
                v-if="canShowPurge"
                size="sm"
                variant="danger"
                @click.stop="openSinglePurgeModal(d)"
              >
                Delete
              </UButton>
            </div>

            <!-- Bulk status feedback -->
            <span v-if="bulkUnclaimStatus[d.id]" class="text-xs text-[var(--status-ok)]">
              {{ bulkUnclaimStatus[d.id] }}
            </span>
            <span
              v-if="bulkPurgeStatus[d.id]"
              class="text-xs"
              :class="bulkPurgeStatus[d.id] === 'Deleted' ? 'text-[var(--status-ok)]' : 'text-[var(--status-bad)]'"
            >
              {{ bulkPurgeStatus[d.id] }}
            </span>
          </div>
        </div>
      </div>
    </UCard>

    <!-- ── 5. Sticky Bulk Actions Bar ─────────────────────────────────────── -->
    <Transition name="bulk-bar">
      <div
        v-if="selectedIds.length"
        class="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 px-5 py-3 rounded-2xl bg-[var(--bg-surface)]/95 backdrop-blur-md border border-[var(--border)] shadow-2xl"
      >
        <UBadge status="neutral">{{ selectedIds.length }} selected</UBadge>

        <!-- Unclaim mode -->
        <template v-if="selectMode === 'unclaim'">
          <template v-if="!bulkUnclaimConfirm">
            <UButton
              size="sm"
              variant="secondary"
              :disabled="!canBulkUnclaim"
              @click="startBulkUnclaimConfirm"
            >
              Bulk unclaim
            </UButton>
          </template>
          <template v-else>
            <span class="text-xs text-[var(--text-muted)]">
              Unclaim {{ selectedIds.length }} device{{ selectedIds.length !== 1 ? "s" : "" }}?
            </span>
            <UButton
              size="sm"
              variant="secondary"
              :loading="bulkUnclaimBusy"
              :disabled="bulkUnclaimBusy"
              @click="bulkUnclaim"
            >
              Confirm unclaim
            </UButton>
            <UButton
              size="sm"
              variant="ghost"
              :disabled="bulkUnclaimBusy"
              @click="cancelBulkUnclaimConfirm"
            >
              Cancel
            </UButton>
          </template>
        </template>

        <!-- Purge mode -->
        <template v-else>
          <UButton
            size="sm"
            variant="danger"
            :disabled="!canBulkPurge"
            @click="openBulkPurgeModal"
          >
            Bulk delete
          </UButton>
        </template>

        <button
          class="ml-1 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
          aria-label="Clear selection"
          @click="selectedIds = []"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      </div>
    </Transition>

    <!-- ── 6. Bulk Purge Modal ─────────────────────────────────────────────── -->
    <UModal
      :open="showBulkPurgeModal"
      title="Confirm Bulk Delete"
      size="sm"
      @close="showBulkPurgeModal = false"
    >
      <div class="space-y-4">
        <p class="text-sm text-[var(--text-secondary)]">
          Permanently delete
          <span class="font-semibold text-[var(--status-bad)]">{{ selectedIds.length }}</span>
          device{{ selectedIds.length !== 1 ? "s" : "" }} and all related data? This cannot be undone.
        </p>
        <div class="bulk-confirm">
          <UInput
            v-model="bulkPurgeConfirmText"
            placeholder="Type DELETE to confirm"
            :error="bulkPurgeConfirmText && bulkPurgeConfirmText !== 'DELETE' ? 'Type DELETE in uppercase' : undefined"
          />
        </div>
      </div>
      <template #footer>
        <div class="flex gap-3 justify-end">
          <UButton variant="ghost" :disabled="bulkPurgeBusy" @click="showBulkPurgeModal = false">
            Cancel
          </UButton>
          <UButton
            variant="danger"
            :loading="bulkPurgeBusy"
            :disabled="bulkPurgeConfirmText !== 'DELETE' || bulkPurgeBusy"
            @click="bulkPurge"
          >
            Confirm delete
          </UButton>
        </div>
      </template>
    </UModal>

    <!-- ── 7. Single Device Purge Modal ───────────────────────────────────── -->
    <UModal
      :open="showSinglePurgeModal"
      title="Confirm Device Delete"
      size="sm"
      @close="showSinglePurgeModal = false"
    >
      <div class="space-y-4">
        <p class="text-sm text-[var(--text-secondary)]">
          Permanently delete
          <span class="font-mono text-[var(--text-primary)]">{{ singlePurgeDevice?.device_uid }}</span>
          and all related data? This cannot be undone.
        </p>
        <UInput
          v-model="singlePurgeConfirmText"
          placeholder="Type DELETE to confirm"
          :error="singlePurgeConfirmText && singlePurgeConfirmText !== 'DELETE' ? 'Type DELETE in uppercase' : undefined"
        />
      </div>
      <template #footer>
        <div class="flex gap-3 justify-end">
          <UButton variant="ghost" @click="showSinglePurgeModal = false">Cancel</UButton>
          <UButton
            variant="danger"
            :disabled="singlePurgeConfirmText !== 'DELETE'"
            @click="confirmSinglePurge"
          >
            Delete device
          </UButton>
        </div>
      </template>
    </UModal>

    <!-- Device Wizard -->
    <DeviceWizard
      :open="showDeviceWizard"
      :initial-category="wizardCategory"
      @close="showDeviceWizard = false"
      @created="(id) => { showDeviceWizard = false; loadDevices(); }"
    />

  </div>
</template>

<style scoped>
.bulk-bar-enter-active,
.bulk-bar-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.bulk-bar-enter-from,
.bulk-bar-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(0.75rem);
}
</style>
