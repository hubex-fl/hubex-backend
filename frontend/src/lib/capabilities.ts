import { reactive } from "vue";
import { fetchJson, ApiError } from "./request";
import { getToken, fetchMe } from "./api";

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
    try {
      await fetchMe();
    } catch (err) {
      const e = err as ApiError;
      if (e.status === 401) {
        state.status = "error";
        state.caps.clear();
        state.error = "Auth failed (401). Paste a fresh token.";
      }
    }
    return;
  }

  state.status = "loading";
  state.error = null;
  state.caps.clear();

  try {
    await fetchJson("/api/v1/users/me", { method: "GET" }, signal);
  } catch (err) {
    const e = err as ApiError;
    if (e.status === 401) {
      state.status = "error";
      state.error = "Auth failed (401). Paste a fresh token.";
      return;
    }
    if (e.status === 403) {
      state.status = "unavailable";
      state.error = "Token valid but no capabilities present (deny-by-default).";
      return;
    }
    state.status = "error";
    state.error = `Capabilities probe failed: ${e.message}`;
    return;
  }

  state.status = "unavailable";
  state.error = "No caps in token (deny-by-default).";
}

export function hasCap(cap: string): boolean {
  if (state.status !== "ready") return false;
  return state.caps.has(cap);
}

export function useCapabilities() {
  return state;
}
