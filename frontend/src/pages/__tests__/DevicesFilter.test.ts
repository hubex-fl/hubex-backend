import { afterEach, describe, expect, it, vi } from "vitest";
import { createApp, nextTick } from "vue";
import { createRouter, createWebHistory } from "vue-router";

const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

async function mountDevices() {
  vi.resetModules();
  const apiFetch = vi.fn(async (path: string) => {
    if (path === "/api/v1/devices") {
      return [
        {
          id: 1,
          device_uid: "dev-unc",
          claimed: false,
          last_seen: null,
          online: true,
          health: "ok",
          last_seen_age_seconds: 5,
          state: "provisioned_unclaimed",
          pairing_active: false,
          busy: false,
        },
      ];
    }
    return {};
  });
  vi.doMock("../../lib/api", () => ({
    apiFetch,
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

  await nextTick();
  await flushPromises();
  return { app, el };
}

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("Devices filters", () => {
  it("renders unclaimed device rows and keeps All filter visible", async () => {
    const { app, el } = await mountDevices();
    expect(el.textContent).toContain("dev-unc");
    const filter = el.querySelector('[data-testid="devices-filter"]') as HTMLSelectElement;
    expect(filter).not.toBeNull();
    expect(filter.value).toBe("all");
    app.unmount();
  });
});
