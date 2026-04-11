import { ref, watch, onMounted, onUnmounted, nextTick } from "vue";
import type { Ref } from "vue";
import { apiFetch } from "../lib/api";
import { mapErrorToUserText, parseApiError } from "../lib/errors";
import { i18n } from "../i18n";

export type DeviceType = "esp32" | "api_device" | "mqtt_bridge" | "software_agent" | "standard_device" | "hardware" | "service" | "bridge" | "agent" | "unknown";

// Sprint 3.8 — DEVICE_TYPE_META was a static module-level English map (ESP32 /
// API Device / MQTT Bridge / etc.). Labels now come from i18n at render time
// via deviceTypeLabel(); icon + color stay in the static map because they
// don't need translation. The `label` field is kept for back-compat with
// call sites that haven't been migrated yet, and shows the raw English key
// as a fallback only if i18n isn't yet initialised.
export const DEVICE_TYPE_META: Record<DeviceType, { label: string; icon: string; color: string }> = {
  esp32:            { label: "ESP32",            icon: "M8.288 15.038a5.25 5.25 0 017.424 0M5.106 11.856c3.807-3.808 9.98-3.808 13.788 0M1.924 8.674c5.565-5.565 14.587-5.565 20.152 0M12.53 18.22l-.53.53-.53-.53a.75.75 0 011.06 0z", color: "var(--cat-hardware)" },
  hardware:         { label: "Hardware",         icon: "M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z", color: "var(--cat-hardware)" },
  api_device:       { label: "API Device",       icon: "M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5", color: "var(--cat-service, #60A5FA)" },
  service:          { label: "Service",          icon: "M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3", color: "var(--cat-service, #60A5FA)" },
  mqtt_bridge:      { label: "MQTT Bridge",      icon: "M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5", color: "var(--cat-bridge, #2DD4BF)" },
  bridge:           { label: "Bridge",           icon: "M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1", color: "var(--cat-bridge, #2DD4BF)" },
  software_agent:   { label: "Software Agent",   icon: "M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-2.47 7.411A1.125 1.125 0 0115.46 23H8.54a1.125 1.125 0 01-1.07-1.089L5 14.5m14 0H5", color: "var(--cat-agent, #A78BFA)" },
  agent:            { label: "Agent",            icon: "M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-13.5 0v-1.5", color: "var(--cat-agent, #A78BFA)" },
  standard_device:  { label: "Standard Device",  icon: "M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z", color: "var(--text-muted)" },
  unknown:          { label: "Unknown",          icon: "M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z", color: "var(--text-muted)" },
};

/**
 * i18n-aware device type label. Looks up `devices.types.<type>` with a
 * fallback to the raw English label from `DEVICE_TYPE_META` and then to
 * the raw string passed in (so it never returns empty).
 *
 * This is the replacement for `DEVICE_TYPE_META[type].label`. Use this
 * everywhere a device type is rendered in UI text. Works outside of
 * Vue setup() scope because it calls `i18n.global.t(...)`.
 */
export function deviceTypeLabel(type: string | null | undefined): string {
  const key = (type || "unknown") as DeviceType;
  const i18nKey = `devices.types.${key}`;
  // i18n.global.t returns the key itself if missing — detect that and fall
  // back to the legacy static label, then to the raw string.
  const translated = i18n.global.t(i18nKey);
  if (translated && translated !== i18nKey) return translated;
  return DEVICE_TYPE_META[key]?.label ?? (type || "Unknown");
}

export type DeviceCategory = "hardware" | "service" | "bridge" | "agent";

export const DEVICE_CATEGORY_META: Record<DeviceCategory, { label: string; emoji: string; color: string }> = {
  hardware: { label: "Hardware", emoji: "🔧", color: "var(--cat-hardware)" },
  service:  { label: "Service",  emoji: "☁️", color: "var(--cat-service)" },
  bridge:   { label: "Bridge",   emoji: "🔗", color: "var(--cat-bridge)" },
  agent:    { label: "Agent",    emoji: "🖥️", color: "var(--cat-agent)" },
};

export type Device = {
  id: number;
  device_uid: string;
  device_type: DeviceType;
  claimed: boolean;
  last_seen: string | null;
  online: boolean;
  health: "ok" | "stale" | "dead";
  last_seen_age_seconds: number | null;
  state: "unprovisioned" | "provisioned_unclaimed" | "pairing_active" | "claimed" | "busy";
  pairing_active: boolean;
  busy: boolean;
  // M15 identity fields
  name: string | null;
  category: DeviceCategory;
  icon: string | null;
  location_name: string | null;
  auto_discovery: boolean;
  is_simulated?: boolean;
  __sig?: string;
};

function deviceSig(d: Device): string {
  return [
    d.id, d.device_uid, d.device_type, d.health, d.state, d.online,
    d.last_seen ?? "", d.pairing_active, d.busy,
  ].join("|");
}

function reconcileById<T extends { id: number; __sig?: string }>(
  target: T[],
  next: T[],
  sigFn: (item: T) => string,
) {
  const byId = new Map<number, T>();
  for (const item of target) byId.set(item.id, item);
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

export function useDevices(includeUnclaimed: Ref<boolean>, intervalMs = 5_000) {
  const devices = ref<Device[]>([]);
  const loading = ref(true);
  const error = ref<string | null>(null);
  const refreshing = ref(false);

  let inflight = false;
  let pendingReload = false;
  let pollTimer: number | null = null;
  let refreshTimer: number | null = null;

  async function fetchDevices(silent = false): Promise<void> {
    if (inflight) return;
    inflight = true;
    pendingReload = false;

    let scrollY = 0;
    if (silent) {
      if (typeof document !== "undefined" && document.visibilityState !== "visible") {
        inflight = false;
        return;
      }
      scrollY = typeof window !== "undefined" ? window.scrollY : 0;
      if (refreshTimer !== null) {
        window.clearTimeout(refreshTimer);
      }
      refreshTimer = window.setTimeout(() => {
        refreshing.value = true;
      }, 350);
    }

    try {
      const path = includeUnclaimed.value
        ? "/api/v1/devices?include_unclaimed=1"
        : "/api/v1/devices";
      const next = await apiFetch<Device[]>(path);
      reconcileById(devices.value, next, deviceSig);
      error.value = null;

      if (silent) {
        await nextTick();
        if (typeof window !== "undefined") {
          const raf =
            typeof window.requestAnimationFrame === "function"
              ? window.requestAnimationFrame.bind(window)
              : (cb: FrameRequestCallback) => window.setTimeout(cb, 0);
          raf(() => window.scrollTo({ top: scrollY }));
        }
      }
    } catch (err: unknown) {
      const info = parseApiError(err);
      error.value = mapErrorToUserText(info, "Failed to load devices");
    } finally {
      loading.value = false;
      if (refreshTimer !== null) {
        window.clearTimeout(refreshTimer);
        refreshTimer = null;
      }
      refreshing.value = false;
      inflight = false;
      if (pendingReload) {
        pendingReload = false;
        const waiters = reloadResolvers.splice(0);
        fetchDevices(false).then(() => {
          for (const r of waiters) r();
        });
      }
    }
  }

  function schedulePoll() {
    if (pollTimer !== null) window.clearTimeout(pollTimer);
    pollTimer = window.setTimeout(async () => {
      pollTimer = null;
      await fetchDevices(true);
      schedulePoll();
    }, intervalMs);
  }

  function onVisibilityChange() {
    if (typeof document !== "undefined" && document.visibilityState === "visible") {
      fetchDevices(true);
    }
  }

  watch(includeUnclaimed, () => {
    loading.value = true;
    fetchDevices(false);
  });

  onMounted(async () => {
    await fetchDevices(false);
    schedulePoll();
    document.addEventListener("visibilitychange", onVisibilityChange);
  });

  onUnmounted(() => {
    if (pollTimer !== null) {
      window.clearTimeout(pollTimer);
      pollTimer = null;
    }
    if (refreshTimer !== null) {
      window.clearTimeout(refreshTimer);
      refreshTimer = null;
    }
    document.removeEventListener("visibilitychange", onVisibilityChange);
  });

  let reloadResolvers: Array<() => void> = [];

  function reload(): Promise<void> {
    if (inflight) {
      return new Promise<void>((resolve) => {
        pendingReload = true;
        reloadResolvers.push(resolve);
      });
    }
    return fetchDevices(false);
  }

  return { devices, loading, error, refreshing, reload };
}
