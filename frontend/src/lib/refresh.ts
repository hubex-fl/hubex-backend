import { mapErrorToUserText, parseApiError } from "./errors";

type RefreshOptions<T> = {
  fallback: string;
  setBusy?: (value: boolean) => void;
  setError?: (value: string | null) => void;
  action: () => Promise<T>;
};

export async function runRefresh<T>(opts: RefreshOptions<T>): Promise<T | null> {
  opts.setError?.(null);
  opts.setBusy?.(true);
  try {
    return await opts.action();
  } catch (err: any) {
    const info = parseApiError(err);
    const status = err?.status;
    if (!info.httpStatus && typeof status === "number") {
      info.httpStatus = status;
    }
    if (!info.message && err?.message) {
      info.message = String(err.message);
    }
    const mapped = mapErrorToUserText(info, opts.fallback);
    const statusLabel = info.httpStatus ? `HTTP ${info.httpStatus}` : "HTTP ?";
    const detail = info.message ? `: ${info.message}` : "";
    const suffix = info.httpStatus || info.message ? ` (${statusLabel}${detail})` : "";
    opts.setError?.(`${mapped}${suffix}`);
    return null;
  } finally {
    opts.setBusy?.(false);
  }
}