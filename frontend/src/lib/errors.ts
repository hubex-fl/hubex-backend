export type ApiErrorInfo = {
  httpStatus?: number;
  code?: string;
  message?: string;
  meta?: Record<string, unknown>;
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
  let meta: Record<string, unknown> | undefined;

  // Extract HTTP status prefix if present (e.g. "HTTP 422: {...}")
  let body = message;
  const httpMatch = message.match(/^HTTP\s+(\d{3})(?:\s+[^:]+)?:\s*([\s\S]*)$/i);
  if (httpMatch) {
    httpStatus = Number(httpMatch[1]);
    body = (httpMatch[2] || "").trim();
  }

  // Try to parse the body as JSON
  const trimmed = body.trim();
  if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
    try {
      const parsed = JSON.parse(trimmed);
      if (parsed && typeof parsed === "object" && "detail" in parsed) {
        const d = (parsed as any).detail;
        if (Array.isArray(d)) {
          // Pydantic validation error: detail is an array of error objects
          const msgs = d.map((e: any) => safeString(e.msg || e.message || e)).filter(Boolean);
          detailMessage = msgs.join("; ") || "Validation error";
        } else if (d && typeof d === "object") {
          code = safeString(d.code);
          detailMessage = safeString(d.message ?? d.detail ?? d);
          if ("meta" in d && d.meta && typeof d.meta === "object") {
            meta = d.meta as Record<string, unknown>;
          }
        } else {
          detailMessage = safeString(d);
        }
      }
    } catch {
      detailMessage = body || message;
    }
  }

  if (!detailMessage) {
    detailMessage = body || message;
  }

  return {
    httpStatus: Number.isFinite(httpStatus) ? httpStatus : undefined,
    code: code || undefined,
    message: detailMessage || undefined,
    meta,
    raw: message || undefined,
  };
}

export function mapErrorToUserText(
  info: ApiErrorInfo,
  fallback: string
): string {
  const code = (info.code || "").toUpperCase();
  const msg = (info.message || "").toLowerCase();

  // ── Specific error codes ──────────────────────────────────────────────
  if (code === "DEVICE_UNKNOWN_UID") return "Unknown device UID";
  if (code === "DEVICE_NOT_PROVISIONED") return "Device not provisioned (never seen)";
  if (code === "DEVICE_ALREADY_CLAIMED") return "Device already claimed";
  if (code === "DEVICE_BUSY") return "Device busy (task running)";
  if (code === "PAIRING_CODE_NOT_FOUND") return "Invalid pairing code";
  if (code === "PAIRING_CODE_EXPIRED") return "Pairing code expired";
  if (code === "PAIRING_CODE_ALREADY_USED") return "Pairing code already used";
  if (code === "PAIRING_ALREADY_ACTIVE") return "Pairing already active";
  if (code === "CAP_FORBIDDEN") return "You don't have permission for this action.";
  if (code === "INSUFFICIENT_CAPABILITY") return "Missing permissions for this action.";

  // ── Message pattern matching ──────────────────────────────────────────
  if (msg.includes("unknown device uid")) return "Unknown device UID";
  if (msg.includes("device not found")) return "Device not found";
  if (msg.includes("device not provisioned")) return "Device not provisioned (never seen)";
  if (msg.includes("device already claimed")) return "Device already claimed";
  if (msg.includes("device busy")) return "Device busy (task running)";
  if (msg.includes("pairing code not found")) return "Invalid pairing code";
  if (msg.includes("pairing code expired")) return "Pairing code expired";
  if (msg.includes("pairing code already used")) return "Pairing code already used";
  if (msg.includes("cannot acknowledge event")) return "This alert was already resolved or acknowledged.";
  if (msg.includes("cannot resolve event")) return "This alert was already resolved.";
  if (msg.includes("alert event not found")) return "This alert event no longer exists.";
  if (msg.includes("validation error")) return "Please check your input — some fields are invalid.";
  if (msg.includes("not found")) return "The requested resource was not found.";
  if (msg.includes("already exists")) return "This item already exists.";
  if (msg.includes("insufficient capability")) return "You don't have permission for this action.";

  // ── HTTP status based ─────────────────────────────────────────────────
  if (info.httpStatus === 400) return "Invalid request. Please check your input.";
  if (info.httpStatus === 401) return "Session expired. Please sign in again.";
  if (info.httpStatus === 403) return "You don't have permission for this action.";
  if (info.httpStatus === 404) return "The requested resource was not found.";
  if (info.httpStatus === 409) return "Conflict — this item may already exist.";
  if (info.httpStatus === 422) return "Please check your input — some fields are invalid.";
  if (info.httpStatus === 429) return "Too many requests. Please wait a moment.";
  if (info.httpStatus === 500) return "Server error. Please try again later.";
  if (info.httpStatus === 502) return "Server temporarily unavailable.";
  if (info.httpStatus === 503) return "Service temporarily unavailable.";

  // ── Legacy message matching ───────────────────────────────────────────
  if (msg.includes("401")) return "Session expired. Please sign in again.";
  if (msg.includes("403")) return "You don't have permission for this action.";
  if (msg.includes("404")) return "Not found.";
  if (msg.includes("409")) return "Conflict.";
  if (msg.includes("410")) return "Expired. Get a new pairing code from the device.";

  return fallback;
}

/**
 * Convenience: parse + map in one call.
 */
export function friendlyError(err: unknown, fallback: string): string {
  return mapErrorToUserText(parseApiError(err), fallback);
}
