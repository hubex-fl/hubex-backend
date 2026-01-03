import { describe, expect, it, vi } from "vitest";
import { fetchJson } from "../request";
import { createPoller } from "../poller";

function makeResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("request/poller hygiene", () => {
  it("dedupes identical GET requests without signal", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(makeResponse({ ok: true }));
    // @ts-expect-error - override global fetch for test
    global.fetch = fetchSpy;

    const p1 = fetchJson<{ ok: boolean }>("/api/v1/test?b=2&a=1");
    const p2 = fetchJson<{ ok: boolean }>("/api/v1/test?a=1&b=2");

    const res = await Promise.all([p1, p2]);
    expect(res[0].ok).toBe(true);
    expect(res[1].ok).toBe(true);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("aborting one subscriber does not cancel the shared request", async () => {
    let capturedSignal: AbortSignal | null = null;
    let resolveFetch: ((value: Response) => void) | null = null;
    const fetchSpy = vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
      capturedSignal = init?.signal || null;
      return new Promise<Response>((resolve) => {
        resolveFetch = resolve;
      });
    });
    // @ts-expect-error - override global fetch for test
    global.fetch = fetchSpy;

    const ac1 = new AbortController();
    const ac2 = new AbortController();

    const p1 = fetchJson("/api/v1/test", {}, ac1.signal);
    const p2 = fetchJson("/api/v1/test", {}, ac2.signal);

    ac1.abort();
    expect(capturedSignal?.aborted).toBe(false);

    resolveFetch?.(makeResponse({ ok: true }));
    await Promise.all([p1, p2]);
  });

  it("poller does not overlap when visibility toggles", async () => {
    vi.useFakeTimers();
    let inFlight = false;
    let calls = 0;
    let resolveRun: (() => void) | null = null;
    const poller = createPoller(async () => {
      calls += 1;
      inFlight = true;
      await new Promise<void>((resolve) => {
        resolveRun = resolve;
      });
      inFlight = false;
    }, 100, { pauseWhenHidden: true });

    Object.defineProperty(document, "visibilityState", {
      value: "visible",
      configurable: true,
    });
    poller.start();
    await vi.advanceTimersByTimeAsync(10);
    expect(calls).toBe(1);
    expect(inFlight).toBe(true);

    document.dispatchEvent(new Event("visibilitychange"));
    await vi.advanceTimersByTimeAsync(10);
    expect(calls).toBe(1);

    resolveRun?.();
    await vi.advanceTimersByTimeAsync(110);
    expect(calls).toBe(2);

    poller.stop();
    vi.useRealTimers();
  });
});
