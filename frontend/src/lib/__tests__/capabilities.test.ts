import { describe, it, expect, vi, beforeAll, afterEach } from "vitest";

function makeToken(payload: Record<string, unknown>): string {
  const json = JSON.stringify(payload);
  const b64 = Buffer.from(json, "utf8")
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
  return `x.${b64}.y`;
}

async function loadModule(getTokenMock: () => string | null, fetchJsonMock: () => Promise<unknown>) {
  vi.resetModules();
  vi.doMock("../api", () => ({ getToken: getTokenMock }));
  vi.doMock("../request", () => ({ fetchJson: fetchJsonMock, ApiError: {} }));
  return import("../capabilities");
}

beforeAll(() => {
  if (!(globalThis as any).atob) {
    (globalThis as any).atob = (b64: string) => Buffer.from(b64, "base64").toString("binary");
  }
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("capabilities", () => {
  it("no token => unavailable", async () => {
    const fetchJson = vi.fn();
    const mod = await loadModule(() => null, fetchJson as any);
    const state = mod.useCapabilities();
    await mod.refreshCapabilities();
    expect(state.status).toBe("unavailable");
    expect(state.error).toBe("No token");
    expect(fetchJson).not.toHaveBeenCalled();
  });

  it("token with caps => ready without /users/me", async () => {
    const token = makeToken({ caps: ["events.read"] });
    const fetchJson = vi.fn().mockResolvedValue({});
    const mod = await loadModule(() => token, fetchJson as any);
    const state = mod.useCapabilities();
    await mod.refreshCapabilities();
    expect(state.status).toBe("ready");
    expect(mod.hasCap("events.read")).toBe(true);
    expect(fetchJson).toHaveBeenCalledTimes(1);
  });

  it("token no caps + /users/me 401 => error", async () => {
    const token = makeToken({});
    const fetchJson = vi.fn().mockRejectedValue({ status: 401, message: "unauthorized" });
    const mod = await loadModule(() => token, fetchJson as any);
    const state = mod.useCapabilities();
    await mod.refreshCapabilities();
    expect(state.status).toBe("error");
    expect(state.error).toContain("401");
  });

  it("token no caps + /users/me 403 => error", async () => {
    const token = makeToken({});
    const fetchJson = vi.fn().mockRejectedValue({ status: 403, message: "forbidden" });
    const mod = await loadModule(() => token, fetchJson as any);
    const state = mod.useCapabilities();
    await mod.refreshCapabilities();
    expect(state.status).toBe("unavailable");
    expect(state.error).toContain("Token valid but no capabilities present");
  });

  it("token no caps + /users/me 200 => unavailable", async () => {
    const token = makeToken({});
    const fetchJson = vi.fn().mockResolvedValue({});
    const mod = await loadModule(() => token, fetchJson as any);
    const state = mod.useCapabilities();
    await mod.refreshCapabilities();
    expect(state.status).toBe("unavailable");
    expect(state.error).toContain("No caps in token");
  });
});
