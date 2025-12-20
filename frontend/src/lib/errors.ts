export type ApiErrorInfo = {
  httpStatus?: number;
  code?: string;
  message?: string;
  raw?: string;
};

function safeString(value: unknown): string {
  if (value === null || value === undefined) return "";
  return typeof value === "string" ? value : JSON.stringify(value);
}

export function parseApiError(err: unknown): ApiErrorInfo {
  const message = safeString((err as any)?.message ?? err);
  let httpStatus: number | undefined;
  let code: string | undefined;
  let detailMessage: string | undefined;

  const httpMatch = message.match(/^HTTP\s+(\d{3})(?:\s+([^:]+))?:\s*([\s\S]*)$/i);
  if (httpMatch) {
    httpStatus = Number(httpMatch[1]);
    detailMessage = httpMatch[3] || "";
  } else {
    const trimmed = message.trim();
    if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
      try {
        const parsed = JSON.parse(trimmed);
        if (parsed && typeof parsed === "object" && "detail" in parsed) {
          const d = (parsed as any).detail;
          if (d && typeof d === "object") {
            code = safeString(d.code);
            detailMessage = safeString(d.message ?? d.detail ?? d);
          } else {
            detailMessage = safeString(d);
          }
        }
      } catch {
        detailMessage = message;
      }
    } else {
      detailMessage = message;
    }
  }

  return {
    httpStatus: Number.isFinite(httpStatus) ? httpStatus : undefined,
    code: code || undefined,
    message: detailMessage || undefined,
    raw: message || undefined,
  };
}

export function mapErrorToUserText(
  info: ApiErrorInfo,
  fallback: string
): string {
  const code = (info.code || "").toUpperCase();
  const msg = (info.message || "").toLowerCase();

  if (code === "DEVICE_NOT_FOUND") return "Unknown device UID";
  if (code === "DEVICE_NOT_PROVISIONED") return "Device not provisioned (never seen)";
  if (code === "DEVICE_ALREADY_CLAIMED") return "Device already claimed";
  if (code === "DEVICE_BUSY") return "Device busy (task running)";
  if (code === "PAIRING_CODE_NOT_FOUND") return "Invalid pairing code";
  if (code === "PAIRING_CODE_EXPIRED") return "Pairing code expired";
  if (code === "PAIRING_CODE_USED") return "Pairing code already used";

  if (msg.includes("device not found")) return "Unknown device UID";
  if (msg.includes("device not provisioned")) return "Device not provisioned (never seen)";
  if (msg.includes("device already claimed")) return "Device already claimed";
  if (msg.includes("device busy")) return "Device busy (task running)";
  if (msg.includes("pairing code not found")) return "Invalid pairing code";
  if (msg.includes("pairing code expired")) return "Pairing code expired";
  if (msg.includes("pairing code already used")) return "Pairing code already used";

  if (msg.includes("401")) return "Not logged in (token expired). Refresh/login.";
  if (msg.includes("403")) return "Forbidden.";
  if (msg.includes("404")) return "Not found.";
  if (msg.includes("409")) return "Conflict.";
  if (msg.includes("410")) return "Expired. Start pairing again.";

  return fallback;
}
