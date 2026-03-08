import { afterEach, describe, expect, it, vi } from "vitest";
import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";

async function mountDevicesRoute() {
  vi.resetModules();
  vi.doMock("../../lib/api", () => ({
    apiFetch: vi.fn(async (path: string) => {
      if (path === "/api/v1/devices") {
        return [];
      }
      return {};
    }),
  }));
  vi.doMock("../../lib/errors", () => ({
    mapErrorToUserText: (_info: any, fallback: string) => fallback,
    parseApiError: () => ({}),
  }));

  const Devices = (await import("../Devices.vue")).default;
  const router = createRouter({
    history: createWebHistory(),
    routes: [{ path: "/devices", component: Devices }],
  });
  await router.push("/devices");
  await router.isReady();

  const el = document.createElement("div");
  document.body.appendChild(el);
  const app = createApp(Devices);
  app.use(router);
  app.mount(el);
  await new Promise((r) => setTimeout(r, 0));
  return { app, el };
}

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("Devices route", () => {
  it("renders the devices page content", async () => {
    const { app, el } = await mountDevicesRoute();
    expect(el.textContent).toContain("Devices");
    expect(el.textContent).toContain("No devices.");
    app.unmount();
  });
});