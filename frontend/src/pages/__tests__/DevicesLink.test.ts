import { afterEach, describe, expect, it, vi } from "vitest";
import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";

async function mountDevices() {
  vi.resetModules();
  vi.doMock("../../lib/api", () => ({
    apiFetch: vi.fn(async (path: string) => {
      if (path === "/api/v1/devices") {
        return [
          {
            id: 1,
            device_uid: "dev-1",
            claimed: true,
            last_seen: null,
            online: false,
            health: "ok",
            last_seen_age_seconds: 10,
            state: "claimed",
            pairing_active: false,
            busy: false,
          },
        ];
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
    routes: [
      { path: "/devices", component: Devices },
      { path: "/devices/:id", component: Devices },
    ],
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

describe("Devices list link", () => {
  it("links to device detail from UID", async () => {
    const { app, el } = await mountDevices();
    const link = el.querySelector("a") as HTMLAnchorElement | null;
    expect(link).not.toBeNull();
    expect(link?.getAttribute("href")).toBe("/devices/1");
    app.unmount();
  });
});
