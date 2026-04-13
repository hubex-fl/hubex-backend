import { useServerHealthStore } from "../stores/serverHealth";

const TOKEN_KEY = "hubex_access_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function hasToken(): boolean {
  return Boolean(getToken());
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  // New token → drop cached /users/me so the next caller re-fetches fresh data
  // under the new auth context (fresh login, MFA verify, org switch).
  clearMeCache();
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  clearMeCache();
}

// Sprint 8 R4 Perf-01 cleanup: /users/me was being fetched twice on
// every session bootstrap — once by the auth capabilities layer and
// once by the preferences store. Both fire in parallel during app
// mount, so caching the inflight promise collapses them into one
// network call. Cache is cleared on logout and on token change.
//
// Cache lifetime is short (60 s) — long enough to dedupe the bootstrap
// wave but short enough that settings edits to the user profile
// propagate within a minute.
let _meInflight: Promise<unknown> | null = null;
let _meCacheTime = 0;
const ME_CACHE_MS = 60_000;

export function fetchMe<T = unknown>(): Promise<T> {
  const now = Date.now();
  if (_meInflight && now - _meCacheTime < ME_CACHE_MS) {
    return _meInflight as Promise<T>;
  }
  _meCacheTime = now;
  _meInflight = apiFetch<T>("/api/v1/users/me");
  // If the request fails, invalidate so the next caller retries.
  (_meInflight as Promise<unknown>).catch(() => { _meInflight = null; });
  return _meInflight as Promise<T>;
}

export function clearMeCache(): void {
  _meInflight = null;
  _meCacheTime = 0;
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const headers = new Headers(init.headers || {});
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  let res: Response;
  try {
    res = await fetch(path, { ...init, headers });
  } catch (err) {
    // Network error — server unreachable
    useServerHealthStore().markOffline();
    throw err;
  }
  // 502/503/504 = gateway/upstream down
  if ([502, 503, 504].includes(res.status)) {
    useServerHealthStore().markOffline();
    throw new Error(`${res.status} ${res.statusText}`);
  }
  // Server responded — it's reachable
  useServerHealthStore().markOnline();
  if (res.status === 401) {
    clearToken();
    window.location.href = "/login";
    throw new Error("unauthorized");
  }
  if (res.status === 403) {
    const text = await res.text();
    // Provide user-friendly permission error instead of raw JSON
    const i18nMsg = (typeof window !== "undefined" && document.documentElement.lang === "de")
      ? "Du hast nicht die Berechtigung f\u00fcr diese Aktion."
      : "You don't have permission for this action.";
    throw new Error(i18nMsg);
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export type DeviceTokenReissueOut = {
  device_id: number;
  device_uid: string;
  device_token: string;
  revoked_count: number;
};

export async function reissueDeviceToken(
  deviceId: number,
  reason: string
): Promise<DeviceTokenReissueOut> {
  return apiFetch<DeviceTokenReissueOut>(`/api/v1/devices/${deviceId}/token/reissue`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export type DeviceUnclaimOut = {
  device_id: number;
  device_uid: string;
  revoked_count: number;
  unclaimed: boolean;
};

export async function unclaimDevice(deviceId: number): Promise<DeviceUnclaimOut> {
  return apiFetch<DeviceUnclaimOut>(`/api/v1/devices/${deviceId}/unclaim`, {
    method: "POST",
  });
}
