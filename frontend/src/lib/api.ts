const TOKEN_KEY = "hubex_access_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function hasToken(): boolean {
  return Boolean(getToken());
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
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
  const res = await fetch(path, { ...init, headers });
  if (res.status === 401) {
    clearToken();
    window.location.href = "/login";
    throw new Error("unauthorized");
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
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
