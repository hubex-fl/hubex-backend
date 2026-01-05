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

function setHostname(hostname: string) {
  Object.defineProperty(window, "location", {
    value: { hostname },
    configurable: true,
  });
}

function setTestEnv(env: Record<string, unknown>) {
  (globalThis as any).__HUBEX_ENV__ = env;
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
  delete (globalThis as any).__HUBEX_ENV__;
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
    const fetchJson = vi.fn();
    const mod = await loadModule(() => token, fetchJson as any);
    const state = mod.useCapabilities();
    await mod.refreshCapabilities();
    expect(state.status).toBe("ready");
    expect(mod.hasCap("events.read")).toBe(true);
    expect(fetchJson).not.toHaveBeenCalled();
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

  it("token no caps + /users/me 403 => unavailable", async () => {
    const token = makeToken({});
    const fetchJson = vi.fn().mockRejectedValue({ status: 403, message: "forbidden" });
    const mod = await loadModule(() => token, fetchJson as any);
    const state = mod.useCapabilities();
    await mod.refreshCapabilities();
    expect(state.status).toBe("unavailable");
    expect(state.error).toContain("no caps");
  });

  it("dev caps override on localhost => ready", async () => {
    setHostname("localhost");
    setTestEnv({ DEV: true, VITE_HUBEX_DEV_CAPS: "events.read,devices.read" });
    const token = makeToken({});
    const fetchJson = vi.fn();
    const mod = await loadModule(() => token, fetchJson as any);
    const state = mod.useCapabilities();
    await mod.refreshCapabilities();
    expect(state.status).toBe("ready");
    expect(mod.hasCap("events.read")).toBe(true);
    expect(state.error).toContain("DEV CAPS ACTIVE");
    expect(fetchJson).not.toHaveBeenCalled();
  });

  it("dev caps ignored on non-local host", async () => {
    setHostname("example.com");
    setTestEnv({ DEV: true, VITE_HUBEX_DEV_CAPS: "events.read" });
    const token = makeToken({});
    const fetchJson = vi.fn().mockRejectedValue({ status: 403, message: "forbidden" });
    const mod = await loadModule(() => token, fetchJson as any);
    const state = mod.useCapabilities();
    await mod.refreshCapabilities();
    expect(state.status).toBe("unavailable");
    expect(mod.hasCap("events.read")).toBe(false);
  });

  it("dev caps '*' allows any cap on localhost", async () => {
    setHostname("127.0.0.1");
    setTestEnv({ DEV: true, VITE_HUBEX_DEV_CAPS: "*" });
    const token = makeToken({});
    const fetchJson = vi.fn();
    const mod = await loadModule(() => token, fetchJson as any);
    await mod.refreshCapabilities();
    expect(mod.hasCap("anything.read")).toBe(true);
  });
});
