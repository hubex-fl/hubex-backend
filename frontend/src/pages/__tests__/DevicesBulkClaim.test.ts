import { afterEach, describe, expect, it, vi } from "vitest";
import { createApp, nextTick } from "vue";
import { createRouter, createWebHistory } from "vue-router";

const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

async function mountDevices() {
  vi.resetModules();
  const callCodes: string[] = [];
  const apiFetch = vi.fn(async (path: string, opts?: any) => {
    if (path === "/api/v1/devices") {
      return [
        {
          id: 1,
          device_uid: "dev-1",
          claimed: false,
          last_seen: null,
          online: false,
          health: "ok",
          last_seen_age_seconds: 10,
          state: "pairing_active",
          pairing_active: true,
          busy: false,
        },
        {
          id: 2,
          device_uid: "dev-2",
          claimed: false,
          last_seen: null,
          online: false,
          health: "ok",
          last_seen_age_seconds: 12,
          state: "pairing_active",
          pairing_active: true,
          busy: false,
        },
      ];
    }
    if (path === "/api/v1/devices/pairing/claim") {
      const body = JSON.parse(opts?.body || "{}");
      callCodes.push(body.pairing_code);
      return { device_uid: "dev" };
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
  caps.caps = new Set(["pairing.claim"]);
  caps.error = null;

  await nextTick();
  await flushPromises();
  return { app, el, apiFetch, callCodes };
}

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("Devices bulk claim", () => {
  it("claims selected devices sequentially", async () => {
    const { app, callCodes } = await mountDevices();
    const instance = (app as any)._instance;
    const selected = instance?.setupState?.selectedIds;
    const codes = instance?.setupState?.bulkClaimCodes;
    if (!selected || !codes) {
      throw new Error("Bulk claim state not available on Devices component");
    }
    if (Array.isArray(selected)) {
      selected.splice(0, selected.length, 1, 2);
    } else {
      selected.value = [1, 2];
    }
    if (typeof codes === "object" && !("value" in codes)) {
      codes[1] = "CODE1";
      codes[2] = "CODE2";
    } else {
      codes.value = { 1: "CODE1", 2: "CODE2" };
    }

    await nextTick();
    await flushPromises();

    await instance.setupState.bulkClaim();

    expect(callCodes).toEqual(["CODE1", "CODE2"]);
    app.unmount();
  });
});
