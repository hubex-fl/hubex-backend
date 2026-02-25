import { afterEach, describe, expect, it, vi } from "vitest";
import { createApp, nextTick } from "vue";
import { createRouter, createWebHistory } from "vue-router";

const flushPromises = () => Promise.resolve();

async function mountDevices(apiFetch: ReturnType<typeof vi.fn>) {
  vi.resetModules();
  vi.doMock("../../lib/api", () => ({ apiFetch }));
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
  await flushPromises();
  return { app, el, router };
}

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("Devices refresh behavior", () => {
  it("skips polling refresh while tab is hidden", async () => {
    vi.useFakeTimers();
    Object.defineProperty(document, "visibilityState", {
      value: "hidden",
      configurable: true,
    });

    const apiFetch = vi.fn(async () => [
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
    ]);

    const { app } = await mountDevices(apiFetch);
    expect(apiFetch).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(6000);
    expect(apiFetch).toHaveBeenCalledTimes(1);

    Object.defineProperty(document, "visibilityState", {
      value: "visible",
      configurable: true,
    });
    window.scrollTo = () => undefined;
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    document.dispatchEvent(new Event("visibilitychange"));
    await flushPromises();
    expect(apiFetch).toHaveBeenCalledTimes(2);

    app.unmount();
    vi.useRealTimers();
  });

  it("restores scroll position after silent refresh", async () => {
    vi.useFakeTimers();
    Object.defineProperty(document, "visibilityState", {
      value: "visible",
      configurable: true,
    });
    Object.defineProperty(window, "scrollY", {
      configurable: true,
      get() {
        return 200;
      },
    });
    window.requestAnimationFrame = (cb: FrameRequestCallback) => {
      cb(0);
      return 0;
    };
    const scrollToSpy = vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);

    const apiFetch = vi.fn(async () => [
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
    ]);

    const { app } = await mountDevices(apiFetch);
    await vi.advanceTimersByTimeAsync(6000);
    await flushPromises();
    expect(scrollToSpy).toHaveBeenCalledWith({ top: 200 });

    app.unmount();
    vi.useRealTimers();
  });

  it("keeps table mounted when device list is empty", async () => {
    Object.defineProperty(document, "visibilityState", {
      value: "visible",
      configurable: true,
    });
    const apiFetch = vi.fn(async () => []);
    const { app, el } = await mountDevices(apiFetch);
    const table = el.querySelector("table");
    expect(table).toBeTruthy();
    expect(el.textContent).toContain("No devices.");
    app.unmount();
  });

  it("keeps table element across refresh and shows refreshing indicator", async () => {
    vi.useFakeTimers();
    Object.defineProperty(document, "visibilityState", {
      value: "visible",
      configurable: true,
    });
    window.requestAnimationFrame = (cb: FrameRequestCallback) => {
      cb(0);
      return 0;
    };

    let resolveSecond: ((value: unknown) => void) | null = null;
    let callCount = 0;
    const apiFetch = vi.fn((path: string) => {
      if (path !== "/api/v1/devices") return Promise.resolve([]);
      callCount += 1;
      if (callCount === 1) {
        return Promise.resolve([
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
        ]);
      }
      return new Promise((resolve) => {
        resolveSecond = resolve;
      });
    });

    const { app, el } = await mountDevices(apiFetch);
    const tableBefore = el.querySelector("table");
    expect(tableBefore).toBeTruthy();
    const beforeText = el.textContent || "";

    await vi.advanceTimersByTimeAsync(6000);
    await vi.advanceTimersByTimeAsync(400);
    await flushPromises();
    expect(el.textContent).toContain("Refreshing...");

    resolveSecond?.([
      {
        id: 1,
        device_uid: "dev-1",
        claimed: false,
        last_seen: null,
        online: false,
        health: "ok",
        last_seen_age_seconds: 9,
        state: "provisioned_unclaimed",
        pairing_active: false,
        busy: false,
      },
    ]);
    await flushPromises();
    await nextTick();
    await flushPromises();

    const tableAfter = el.querySelector("table");
    expect(tableAfter).toBe(tableBefore);
    expect(el.textContent).not.toContain("Refreshing...");
    expect(el.textContent).toContain("10s ago");
    expect(el.textContent).not.toContain("9s ago");
    expect(el.textContent?.replace("Refreshing...", "")).toContain(beforeText.replace("Refreshing...", ""));

    app.unmount();
    vi.useRealTimers();
  });
});
