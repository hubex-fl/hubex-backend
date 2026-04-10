/**
 * Code Generator — client helpers for POST /api/v1/codegen/project
 *
 * Unlike `apiFetch` (which always JSON-decodes), this module fetches a binary
 * ZIP response and triggers a browser download. Used by the HardwareWizard.
 */

import { getToken } from "./api";

export interface ProjectSpec {
  device_name: string;
  board_key: string;         // "esp32" / "esp32s3" / "esp32c3" / "rp2040"
  framework: "platformio" | "arduino" | "micropython";
  component_keys: string[];
  wifi_ssid?: string;
  wifi_pass?: string;
  server_url?: string;
  read_interval_s?: number;
}

export interface ProjectDownloadResult {
  device_id: number | null;
  device_uid: string | null;
  device_name: string;
  filename: string;
}

export interface CodegenErrorPayload {
  code: string;
  message: string;
  [k: string]: unknown;
}

export class CodegenError extends Error {
  code: string;
  payload: CodegenErrorPayload | null;
  constructor(code: string, message: string, payload: CodegenErrorPayload | null = null) {
    super(message);
    this.code = code;
    this.payload = payload;
  }
}

/**
 * POST the wizard spec, download the returned ZIP, and trigger a browser
 * download prompt. Returns metadata about the newly created device (the
 * backend includes these in custom X-HubEx-* response headers).
 */
export async function downloadProjectZip(
  spec: ProjectSpec
): Promise<ProjectDownloadResult> {
  const token = getToken();
  if (!token) throw new CodegenError("NO_SESSION", "Not logged in");

  const body = JSON.stringify({
    device_name: spec.device_name,
    board_key: spec.board_key,
    framework: spec.framework,
    component_keys: spec.component_keys,
    wifi_ssid: spec.wifi_ssid ?? "",
    wifi_pass: spec.wifi_pass ?? "",
    server_url: spec.server_url ?? window.location.origin,
    read_interval_s: spec.read_interval_s ?? 10,
  });

  const res = await fetch("/api/v1/codegen/project", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body,
  });

  if (!res.ok) {
    // Error responses are always JSON
    let payload: CodegenErrorPayload | null = null;
    try {
      const data = await res.json();
      payload = data?.detail ?? data;
    } catch {
      /* ignore */
    }
    const code = payload?.code ?? `HTTP_${res.status}`;
    const message = payload?.message ?? `Request failed (${res.status})`;
    throw new CodegenError(code, message, payload);
  }

  // Parse the Content-Disposition filename so the download dialog shows
  // the server-suggested name, not a random hash.
  const cd = res.headers.get("Content-Disposition") || "";
  const match = cd.match(/filename="?([^"]+)"?/);
  const suggestedFilename =
    match?.[1] ||
    `HUBEX_${spec.device_name.replace(/[^A-Za-z0-9_-]/g, "_")}.zip`;

  // Custom response headers populated by the backend
  const deviceIdStr = res.headers.get("X-HubEx-Device-Id");
  const deviceUid = res.headers.get("X-HubEx-Device-Uid");

  const blob = await res.blob();
  triggerBrowserDownload(blob, suggestedFilename);

  return {
    device_id: deviceIdStr ? Number(deviceIdStr) : null,
    device_uid: deviceUid,
    device_name: spec.device_name,
    filename: suggestedFilename,
  };
}

function triggerBrowserDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  // Must be in the DOM for Firefox to honor the download attribute
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, 0);
}
