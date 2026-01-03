import { getToken } from "./api";

export type ApiError = {
  status?: number;
  message: string;
  body?: string;
};

type InflightEntry<T> = {
  promise: Promise<T>;
  controller: AbortController;
  subscribers: Set<number>;
  aborted: Set<number>;
};

const inflightGet = new Map<string, InflightEntry<unknown>>();
let subCounter = 0;

function normalizeUrl(url: string): string {
  try {
    const parsed = new URL(url, window.location.origin);
    const params = Array.from(parsed.searchParams.entries()).sort(([a], [b]) =>
      a.localeCompare(b)
    );
    parsed.search = params.length
      ? `?${params.map(([k, v]) => `${k}=${v}`).join("&")}`
      : "";
    return parsed.pathname + parsed.search;
  } catch {
    return url;
  }
}

function bodyKey(body: RequestInit["body"]): string {
  if (!body) return "";
  if (typeof body === "string") return body;
  if (body instanceof URLSearchParams) return body.toString();
  return "[body]";
}

function buildKey(method: string, url: string, hasToken: boolean): string {
  return `${method.toUpperCase()} ${normalizeUrl(url)} token=${hasToken ? "1" : "0"}`;
}

async function parseJson<T>(res: Response): Promise<T> {
  const text = await res.text();
  if (!text) {
    return null as T;
  }
  return JSON.parse(text) as T;
}

function toApiError(status: number, statusText: string, body: string | undefined): ApiError {
  const snippet = body ? body.slice(0, 300) : undefined;
  return { status, message: statusText || "request_failed", body: snippet };
}

export async function fetchJson<T>(
  url: string,
  init: RequestInit = {},
  signal?: AbortSignal
): Promise<T> {
  const method = (init.method || "GET").toUpperCase();
  const token = getToken();
  const headers = new Headers(init.headers || {});
  headers.set("Accept", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (method === "GET") {
    const key = `${buildKey(method, url, Boolean(token))} body=${bodyKey(init.body)}`;
    const existing = inflightGet.get(key) as InflightEntry<T> | undefined;
    if (existing) {
      const subId = ++subCounter;
      existing.subscribers.add(subId);
      if (signal) {
        const onAbort = () => {
          existing.aborted.add(subId);
          if (existing.aborted.size >= existing.subscribers.size) {
            existing.controller.abort();
          }
        };
        if (signal.aborted) {
          onAbort();
        } else {
          signal.addEventListener("abort", onAbort, { once: true });
        }
      }
      return existing.promise.finally(() => {
        existing.subscribers.delete(subId);
        existing.aborted.delete(subId);
        if (existing.subscribers.size === 0) {
          inflightGet.delete(key);
        }
      }) as Promise<T>;
    }

    const controller = new AbortController();
    const entry: InflightEntry<T> = {
      promise: Promise.resolve(null as T),
      controller,
      subscribers: new Set<number>(),
      aborted: new Set<number>(),
    };
    inflightGet.set(key, entry as InflightEntry<unknown>);

    const subId = ++subCounter;
    entry.subscribers.add(subId);
    if (signal) {
      const onAbort = () => {
        entry.aborted.add(subId);
        if (entry.aborted.size >= entry.subscribers.size) {
          controller.abort();
        }
      };
      if (signal.aborted) {
        onAbort();
      } else {
        signal.addEventListener("abort", onAbort, { once: true });
      }
    }

    entry.promise = fetch(url, {
      ...init,
      method,
      headers,
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.text();
          throw toApiError(res.status, res.statusText, body);
        }
        return parseJson<T>(res);
      })
      .finally(() => {
        entry.subscribers.delete(subId);
        entry.aborted.delete(subId);
        if (entry.subscribers.size === 0) {
          inflightGet.delete(key);
        }
      });

    return entry.promise;
  }

  const res = await fetch(url, { ...init, method, headers, signal });
  if (!res.ok) {
    const body = await res.text();
    throw toApiError(res.status, res.statusText, body);
  }
  return parseJson<T>(res);
}
