import { afterEach, describe, expect, it, vi } from "vitest";
import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";

async function loadPage(caps: string[]) {
  vi.resetModules();
  const apiFetch = vi.fn(async (path: string) => {
    if (path.includes("/current-task")) {
      return {
        has_active_lease: false,
        device_id: 1,
        task_id: null,
        task_name: null,
        task_type: null,
        task_status: null,
        claimed_at: null,
        lease_expires_at: null,
        lease_seconds_remaining: null,
        lease_token_hint: null,
        context_key: null,
      };
    }
    if (path.includes("/task-history")) return [];
    if (path.startsWith("/api/v1/devices/")) {
      return {
        id: 1,
        device_uid: "dev-1",
        last_seen_at: null,
        health: "ok",
        last_seen_age_seconds: 10,
        state: "claimed",
        pairing_active: false,
        busy: false,
      };
    }
    return {};
  });
  const reissueDeviceToken = vi.fn().mockResolvedValue({
    device_id: 1,
    device_uid: "dev-1",
    device_token: "token-123",
    revoked_count: 1,
  });

  vi.doMock("../../lib/api", () => ({
    apiFetch,
    getToken: () => null,
    reissueDeviceToken,
    setToken: vi.fn(),
    clearToken: vi.fn(),
  }));
  vi.doMock("../../lib/variables", () => ({
    getEffectiveVariables: vi.fn().mockResolvedValue({ items: [], snapshot_id: null }),
    putValue: vi.fn(),
  }));
  vi.doMock("../../lib/errors", () => ({
    mapErrorToUserText: (_info: any, fallback: string) => fallback,
    parseApiError: () => ({}),
  }));
  vi.doMock("../../lib/capabilities", () => {
    const state = { status: "ready", caps: new Set(caps), error: null };
    return {
      useCapabilities: () => state,
      hasCap: (cap: string) => state.caps.has(cap),
      refreshCapabilities: vi.fn(),
    };
  });

  const DeviceDetail = (await import("../DeviceDetail.vue")).default;
  const router = createRouter({
    history: createWebHistory(),
    routes: [{ path: "/devices/:id", component: DeviceDetail }],
  });
  await router.push("/devices/1");
  await router.isReady();

  const el = document.createElement("div");
  document.body.appendChild(el);
  const app = createApp(DeviceDetail);
  app.use(router);
  app.mount(el);

  await new Promise((r) => setTimeout(r, 0));
  await new Promise((r) => setTimeout(r, 0));
  return { app, el, reissueDeviceToken };
}

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("DeviceDetail Recovery", () => {
  it("renders reissue button when cap present", async () => {
    const { app, el } = await loadPage(["devices.token.reissue"]);
    expect(el.textContent).toContain("Reissue Device Token");
    app.unmount();
  });

  it("hides button when cap missing", async () => {
    const { app, el } = await loadPage([]);
    expect(el.textContent).toContain("Missing cap devices.token.reissue");
    expect(el.textContent).not.toContain("Reissue Device Token");
    app.unmount();
  });

  it("shows token once and clears on remount", async () => {
    const promptSpy = vi.spyOn(window, "prompt").mockReturnValue("valid reason");
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const { app, el } = await loadPage(["devices.token.reissue"]);
    const button = Array.from(el.querySelectorAll("button")).find((btn) =>
      btn.textContent?.includes("Reissue Device Token")
    ) as HTMLButtonElement | undefined;
    expect(button).toBeTruthy();
    button?.click();
    await new Promise((r) => setTimeout(r, 0));
    expect(el.textContent).toContain("token-123");
    app.unmount();

    const { app: app2, el: el2 } = await loadPage(["devices.token.reissue"]);
    expect(el2.textContent).not.toContain("token-123");
    app2.unmount();
    promptSpy.mockRestore();
    confirmSpy.mockRestore();
  });
});
