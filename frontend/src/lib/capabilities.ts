import { reactive } from "vue";
import { fetchJson, ApiError } from "./request";
import { getToken } from "./api";

export type CapStatus = "idle" | "loading" | "ready" | "error" | "unavailable";

type CapState = {
  status: CapStatus;
  caps: Set<string>;
  error: string | null;
};

const state: CapState = reactive({
  status: "idle",
  caps: new Set<string>(),
  error: null,
});

const ENV = (globalThis as any).__HUBEX_ENV__ ?? (import.meta as any).env ?? {};
const DEV_ENABLED = Boolean(ENV.DEV);
const DEV_CAPS_ENV = DEV_ENABLED ? ENV.VITE_HUBEX_DEV_CAPS ?? "" : "";
const DEV_CAPS_RAW = String(DEV_CAPS_ENV).trim();
const DEV_ALL = DEV_CAPS_RAW === "*";
const DEV_CAPS = DEV_ALL
  ? []
  : DEV_CAPS_RAW.split(",").map((cap) => cap.trim()).filter(Boolean);

function isLocalHost(): boolean {
  if (typeof window === "undefined") return false;
  const host = window.location.hostname;
  return host === "localhost" || host === "127.0.0.1";
}

function decodeTokenCaps(token: string | null): string[] {
  if (!token) return [];
  const parts = token.split(".");
  if (parts.length < 2) return [];
  try {
    const json = atob(parts[1].replace(/-/g, "+").replace(/_/g, "/"));
    const payload = JSON.parse(json);
    if (Array.isArray(payload.caps)) return payload.caps;
    if (Array.isArray(payload.capabilities)) return payload.capabilities;
    return [];
  } catch {
    return [];
  }
}

export async function refreshCapabilities(signal?: AbortSignal): Promise<void> {
  const token = getToken();
  if (!token) {
    state.status = "unavailable";
    state.caps.clear();
    state.error = "No token";
    return;
  }
  const tokenCaps = decodeTokenCaps(token);
  if (tokenCaps.length > 0) {
    state.caps = new Set(tokenCaps);
    state.status = "ready";
    state.error = null;
    return;
  } else if (DEV_CAPS_RAW && isLocalHost()) {
    state.caps = new Set(DEV_CAPS);
    state.status = "ready";
    state.error = "DEV CAPS ACTIVE (local override)";
    return;
  } else {
    state.status = "loading";
    state.error = null;
  }

  try {
    await fetchJson("/api/v1/users/me", { method: "GET" }, signal);
  } catch (err) {
    const e = err as ApiError;
    if (e.status === 401) {
      state.status = "error";
      state.caps.clear();
      state.error = "Auth failed (401). Paste a fresh token.";
      return;
    }
    if (e.status === 403) {
      state.status = "unavailable";
      state.caps.clear();
      state.error = "Token valid, but no caps present (deny-by-default).";
      return;
    }
    state.status = "error";
    state.caps.clear();
    state.error = `Capabilities probe failed: ${e.message}`;
    return;
  }

  state.status = "unavailable";
  state.caps.clear();
  state.error = "No caps in token. UI is deny-by-default.";
}

export function hasCap(cap: string): boolean {
  if (state.status !== "ready") return false;
  if (DEV_ALL && isLocalHost()) return true;
  return state.caps.has(cap);
}

export function useCapabilities() {
  return state;
}
