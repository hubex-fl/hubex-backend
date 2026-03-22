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
          device_uid: "dev-1",
          claimed: false,
          last_seen: null,
          online: false,
          health: "ok",
          last_seen_age_seconds: 10,
          state: "provisioned_unclaimed",
          pairing_active: false,
          busy: false,
        },
      ];
    }
    if (path === "/api/v1/devices/pairing/claim") {
      return { device_uid: "dev-1" };
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
  return { app, el, router, apiFetch };
}

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("Devices claim flow", () => {
  it("claims pairing code and refreshes devices", async () => {
    const { app, el, router, apiFetch } = await mountDevices();
    const input = el.querySelector('input[placeholder="Pairing code (claim)"]') as HTMLInputElement;
    const uidInput = el.querySelector('input[placeholder="Device UID"]') as HTMLInputElement;
    expect(input).not.toBeNull();
    expect(uidInput).not.toBeNull();
    const instance = (app as any)._instance;
    if (instance?.setupState?.pairingClaimCode) {
      instance.setupState.pairingClaimCode.value = "ABC12345";
      instance.setupState.pairingDeviceUid.value = "dev-1";
    }
    input.value = "ABC12345";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    uidInput.value = "dev-1";
    uidInput.dispatchEvent(new Event("input", { bubbles: true }));
    await nextTick();
    await flushPromises();

    const buttons = Array.from(el.querySelectorAll("button"));
    const claimButton = buttons.find((b) => b.textContent?.includes("Claim"));
    expect(claimButton).toBeTruthy();
    if (instance?.setupState?.claimPairing) {
      await instance.setupState.claimPairing();
    } else {
      claimButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    }

    await flushPromises();
    const calls = apiFetch.mock.calls.map((c) => c[0]);
    expect(calls).toContain("/api/v1/devices/pairing/claim");
    expect(calls).toContain("/api/v1/devices");
    expect(el.textContent).toContain("Claimed");
    if (instance?.setupState?.pairingClaimCode) {
      expect(instance.setupState.pairingClaimCode.value).toBe("");
      expect(instance.setupState.pairingDeviceUid.value).toBe("");
    }
    expect(router.currentRoute.value.fullPath).toBe("/devices");
    app.unmount();
  });

  it("fills device UID from row action", async () => {
    const { app, el } = await mountDevices();
    const useButton = Array.from(el.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("Use UID")
    ) as HTMLButtonElement | undefined;
    expect(useButton).toBeTruthy();
    useButton?.click();
    await nextTick();
    await flushPromises();
    const uidInput = el.querySelector('input[placeholder="Device UID"]') as HTMLInputElement | null;
    expect(uidInput?.value).toBe("dev-1");
    app.unmount();
  });

  it("uses include_unclaimed when admin toggle enabled", async () => {
    const { app, apiFetch } = await mountDevices();
    const { useCapabilities } = await import("../../lib/capabilities");
    const caps = useCapabilities();
    caps.status = "ready";
    caps.caps = new Set(["pairing.claim", "cap.admin"]);
    caps.error = null;
    const instance = (app as any)._instance;
    if (instance?.setupState?.showUnclaimedAdmin !== undefined) {
      instance.setupState.showUnclaimedAdmin = true;
    }
    await nextTick();
    await flushPromises();
    const calls = apiFetch.mock.calls.map((c) => c[0]);
    expect(calls).toContain("/api/v1/devices?include_unclaimed=1");
    app.unmount();
  });

  it("does not render Start Pairing controls", async () => {
    const { app, el } = await mountDevices();
    await nextTick();
    await flushPromises();
    const startButtons = Array.from(el.querySelectorAll("button")).filter((b) =>
      b.textContent?.includes("Start pairing")
    );
    expect(startButtons.length).toBe(0);
    app.unmount();
  });
});
