import { afterEach, describe, expect, it, vi } from "vitest";
import { createApp, nextTick } from "vue";
import { createRouter, createWebHistory } from "vue-router";

const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

async function mountDevices() {
  vi.resetModules();
  const callIds: number[] = [];
  const apiFetch = vi.fn(async (path: string) => {
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
        {
          id: 2,
          device_uid: "dev-2",
          claimed: true,
          last_seen: null,
          online: false,
          health: "ok",
          last_seen_age_seconds: 12,
          state: "claimed",
          pairing_active: false,
          busy: false,
        },
      ];
    }
    if (path.startsWith("/api/v1/devices/") && path.endsWith("/unclaim")) {
      const id = Number(path.split("/")[4]);
      callIds.push(id);
      return { device_uid: `dev-${id}` };
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

  const { useCapabilities } = await import("../../lib/capabilities");
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

  const caps = useCapabilities();
  caps.status = "ready";
  caps.caps = new Set(["devices.unclaim"]);
  caps.error = null;

  await nextTick();
  await flushPromises();
  return { app, el, callIds };
}

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("Devices bulk unclaim", () => {
  it("unclaims selected devices sequentially", async () => {
    const { app, callIds } = await mountDevices();
    const instance = (app as any)._instance;
    const selected = instance?.setupState?.selectedIds;
    if (!selected) {
      throw new Error("selectedIds not available");
    }
    if (Array.isArray(selected)) {
      selected.splice(0, selected.length, 1, 2);
    } else {
      selected.value = [1, 2];
    }

    await nextTick();
    await flushPromises();

    if (instance?.setupState?.bulkUnclaim) {
      await instance.setupState.bulkUnclaim();
    }

    expect(callIds).toEqual([1, 2]);
    app.unmount();
  });
});
