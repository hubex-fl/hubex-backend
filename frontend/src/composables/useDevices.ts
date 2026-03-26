import { ref, watch, onMounted, onUnmounted, nextTick } from "vue";
import type { Ref } from "vue";
import { apiFetch } from "../lib/api";
import { mapErrorToUserText, parseApiError } from "../lib/errors";

export type Device = {
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

function deviceSig(d: Device): string {
  return [
    d.id, d.device_uid, d.health, d.state, d.online,
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
  let pollTimer: number | null = null;
  let refreshTimer: number | null = null;

  async function fetchDevices(silent = false): Promise<void> {
    if (inflight) return;
    inflight = true;

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

  return { devices, loading, error, refreshing, reload: () => fetchDevices(false) };
}
