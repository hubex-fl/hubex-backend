import { afterEach, describe, expect, it, vi } from "vitest";
import { createApp, nextTick } from "vue";
import { createRouter, createWebHistory } from "vue-router";

const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

async function mountDevices(capsList: string[] = ["devices.purge"]) {
  vi.resetModules();
  const apiFetch = vi.fn(async (path: string, init?: any) => {
    if (path.startsWith("/api/v1/devices")) {
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
          claimed: false,
          last_seen: null,
          online: false,
          health: "ok",
          last_seen_age_seconds: 5000,
          state: "provisioned_unclaimed",
          pairing_active: false,
          busy: false,
        },
      ];
    }
    if (path === "/api/v1/devices/purge") {
      const body = JSON.parse(init?.body || "{}");
      return {
        results: (body.device_ids || []).map((id: number) => ({ id, ok: true })),
      };
    }
    return {};
  });
  vi.doMock("../../lib/api", () => ({ apiFetch }));
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
  caps.caps = new Set(capsList);
  caps.error = null;

  await nextTick();
  await flushPromises();
  return { app, apiFetch };
}

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("Devices bulk purge", () => {
  it("calls bulk purge endpoint with selected ids", async () => {
    const { app, apiFetch } = await mountDevices();
    const root = document.body;
    const modeSelect = root.querySelector(".bulk-toolbar select") as HTMLSelectElement | null;
    expect(modeSelect).not.toBeNull();
    if (modeSelect) {
      modeSelect.value = "purge";
      modeSelect.dispatchEvent(new Event("change", { bubbles: true }));
    }
    await nextTick();
    await flushPromises();

    const selectAll = root.querySelector(".bulk-toolbar input[type='checkbox']") as
      | HTMLInputElement
      | null;
    selectAll?.click();
    await nextTick();

    const bulkButton = Array.from(root.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("Bulk purge")
    );
    expect(bulkButton).toBeTruthy();
    bulkButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await nextTick();

    const confirmInput = root.querySelector(
      '.bulk-confirm input[placeholder="Type PURGE to confirm"]'
    ) as HTMLInputElement | null;
    expect(confirmInput).not.toBeNull();
    if (confirmInput) {
      confirmInput.value = "PURGE";
      confirmInput.dispatchEvent(new Event("input", { bubbles: true }));
    }
    await nextTick();

    const confirmButton = Array.from(root.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("Confirm purge")
    );
    confirmButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await flushPromises();

    const calls = apiFetch.mock.calls.map((c) => c[0]);
    expect(calls).toContain("/api/v1/devices/purge");
    app.unmount();
  });

  it("selects all visible rows in purge mode", async () => {
    const { app } = await mountDevices();
    const root = document.body;
    const modeSelect = root.querySelector(".bulk-toolbar select") as HTMLSelectElement | null;
    expect(modeSelect).not.toBeNull();
    if (modeSelect) {
      modeSelect.value = "purge";
      modeSelect.dispatchEvent(new Event("change", { bubbles: true }));
    }
    await nextTick();
    await flushPromises();

    const selectAll = root.querySelector(".bulk-toolbar input[type='checkbox']") as
      | HTMLInputElement
      | null;
    selectAll?.click();
    await nextTick();

    const instance = (app as any)._instance;
    const selected = instance?.setupState?.selectedIds;
    const ids = Array.isArray(selected) ? selected : selected?.value || [];
    expect(ids).toEqual([1, 2]);
    app.unmount();
  });

  it("hides purge controls without devices.purge cap", async () => {
    const { app } = await mountDevices([]);
    await nextTick();
    const purgeButtons = Array.from(document.querySelectorAll("button")).filter((b) =>
      b.textContent?.includes("Purge")
    );
    expect(purgeButtons.length).toBe(0);
    app.unmount();
  });
});
