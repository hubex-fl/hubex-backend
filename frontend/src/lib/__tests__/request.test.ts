import { describe, expect, it, vi } from "vitest";
import { fetchJson } from "../request";

function makeResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("fetchJson dedupe", () => {
  it("dedupes identical GET requests", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(makeResponse({ ok: true }));
    // @ts-expect-error - override global fetch for test
    global.fetch = fetchSpy;

    const p1 = fetchJson<{ ok: boolean }>("/api/v1/test");
    const p2 = fetchJson<{ ok: boolean }>("/api/v1/test");

    const res = await Promise.all([p1, p2]);
    expect(res[0].ok).toBe(true);
    expect(res[1].ok).toBe(true);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("aborts only after all subscribers abort", async () => {
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
    ac2.abort();
    expect(capturedSignal?.aborted).toBe(true);

    resolveFetch?.(makeResponse({ ok: true }));
    await Promise.all([p1, p2]);
  });
});
