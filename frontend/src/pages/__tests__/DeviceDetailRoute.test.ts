import { afterEach, describe, expect, it, vi } from "vitest";
import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";

async function mountRoute() {
  vi.resetModules();
  vi.doMock("../../lib/api", () => ({
    apiFetch: vi.fn(async (path: string) => {
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
    }),
    getToken: () => null,
    reissueDeviceToken: vi.fn(),
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
    const state = { status: "ready", caps: new Set<string>(), error: null };
    return {
      useCapabilities: () => state,
      hasCap: () => false,
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
  return { app, el };
}

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("DeviceDetail route", () => {
  it("renders device detail page on /devices/:id", async () => {
    const { app, el } = await mountRoute();
    expect(el.textContent).toContain("Device Detail");
    app.unmount();
  });
});
