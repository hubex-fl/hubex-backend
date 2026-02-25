import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { createApp, nextTick } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import SystemStage from "../SystemStage.vue";
import { useCapabilities } from "../../lib/capabilities";

const flushPromises = () => Promise.resolve();

function mountSystemStage() {
  const el = document.createElement("div");
  document.body.appendChild(el);
  const app = createApp(SystemStage);
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: "/system-stage", component: SystemStage },
      { path: "/devices/:id", component: { template: "<div>Device</div>" } },
    ],
  });
  app.use(router);
  app.mount(el);
  return { app, el, router };
}

describe("SystemStage", () => {
  const caps = useCapabilities();

  beforeEach(() => {
    caps.status = "ready";
    caps.caps = new Set(["devices.read", "vars.read"]);
    caps.error = null;
    (window as Window & { scrollTo?: () => void }).scrollTo = () => undefined;
    window.requestAnimationFrame = (cb: FrameRequestCallback) => {
      cb(0);
      return 0;
    };
    Object.defineProperty(document, "visibilityState", {
      value: "visible",
      configurable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("aborts requests on unmount", () => {
    let capturedSignal: AbortSignal | null = null;
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((_, init) => {
      capturedSignal = (init as RequestInit)?.signal as AbortSignal;
      return Promise.resolve(
        new Response("[]", {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );
    });

    const { app } = mountSystemStage();
    expect(fetchSpy).toHaveBeenCalled();
    expect(capturedSignal?.aborted).toBe(false);
    app.unmount();
    expect(capturedSignal?.aborted).toBe(true);
  });

  it("shows missing capability notice when devices.read is absent", () => {
    caps.caps = new Set();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      return Promise.reject(new Error("should not call fetch"));
    });

    const { app, el } = mountSystemStage();
    expect(el.textContent).toContain("Missing capability: devices.read");
    expect(fetchSpy).not.toHaveBeenCalled();
    app.unmount();
  });

  it("does not fetch when capabilities are unavailable", () => {
    caps.status = "unavailable";
    caps.caps = new Set(["devices.read"]);
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      return Promise.reject(new Error("should not call fetch"));
    });

    const { app, el } = mountSystemStage();
    expect(el.textContent).toContain("Capabilities unavailable");
    expect(fetchSpy).not.toHaveBeenCalled();
    app.unmount();
  });

  it("pauses polling when hidden and resumes on visible", async () => {
    vi.useFakeTimers();
    caps.caps = new Set(["devices.read"]);
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("[]", {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    Object.defineProperty(document, "visibilityState", {
      value: "hidden",
      configurable: true,
    });

    const { app } = mountSystemStage();
    expect(fetchSpy).not.toHaveBeenCalled();

    Object.defineProperty(document, "visibilityState", {
      value: "visible",
      configurable: true,
    });
    document.dispatchEvent(new Event("visibilitychange"));
    await vi.advanceTimersByTimeAsync(5100);
    expect(fetchSpy).toHaveBeenCalled();

    const callsBefore = fetchSpy.mock.calls.length;
    Object.defineProperty(document, "visibilityState", {
      value: "hidden",
      configurable: true,
    });
    document.dispatchEvent(new Event("visibilitychange"));
    await vi.advanceTimersByTimeAsync(6000);
    expect(fetchSpy.mock.calls.length).toBe(callsBefore);

    app.unmount();
    vi.useRealTimers();
  });

  it("links device UID to detail route", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("[]", {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    const { app, el, router } = mountSystemStage();
    const pushSpy = vi.spyOn(router, "push").mockResolvedValue();
    await router.push("/system-stage");
    await router.isReady();
    await nextTick();
    await flushPromises();
    const instance = (app as any)._instance;
    if (instance.setupState.loading && "value" in instance.setupState.loading) {
      instance.setupState.loading.value = false;
    } else {
      instance.setupState.loading = false;
    }
    if (instance.setupState.devicesError && "value" in instance.setupState.devicesError) {
      instance.setupState.devicesError.value = null;
    } else {
      instance.setupState.devicesError = null;
    }
    const seeded = [{ id: 1, device_uid: "dev-1", state: "claimed", __sig: "1|dev-1|claimed|" }];
    if (Array.isArray(instance.setupState.devices)) {
      instance.setupState.devices = seeded;
    } else {
      instance.setupState.devices.value = seeded;
    }
    await nextTick();
    await flushPromises();
    const link = el.querySelector('a[href="/devices/1"]') as HTMLAnchorElement | null;
    expect(link).toBeTruthy();
    const currentDevices = Array.isArray(instance.setupState.devices)
      ? instance.setupState.devices
      : instance.setupState.devices.value;
    instance?.setupState?.onRowClick(currentDevices[0]);
    await nextTick();
    expect(pushSpy).toHaveBeenCalledWith("/devices/1");
    app.unmount();
  });

  it("preserves scroll position on refresh", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response('[{"id":1,"device_uid":"dev-1","state":"claimed"}]', {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    const scrollToSpy = vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    Object.defineProperty(window, "scrollY", {
      configurable: true,
      get() {
        return 120;
      },
    });
    const { app, router } = mountSystemStage();
    await router.push("/system-stage");
    await nextTick();
    await flushPromises();
    expect(fetchSpy).toHaveBeenCalled();
    expect(scrollToSpy).toHaveBeenCalledWith({ top: 120 });
    app.unmount();
  });

  it("keeps devices table mounted when empty", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("[]", {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    const { app, el, router } = mountSystemStage();
    await router.push("/system-stage");
    await router.isReady();
    await nextTick();
    await flushPromises();
    const tables = el.querySelectorAll("table");
    expect(tables.length).toBeGreaterThan(0);
    expect(el.textContent).toContain("No devices.");
    app.unmount();
  });

  it("keeps devices table element across refresh", async () => {
    vi.useFakeTimers();
    let callCount = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/devices")) {
        callCount += 1;
        const payload = callCount === 1
          ? '[{"id":1,"device_uid":"dev-1","state":"claimed"}]'
          : '[{"id":1,"device_uid":"dev-1","state":"claimed","last_seen_at":"2026-02-01T00:00:00Z"}]';
        return Promise.resolve(
          new Response(payload, {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        );
      }
      return Promise.resolve(
        new Response("[]", {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );
    });

    const { app, el, router } = mountSystemStage();
    await router.push("/system-stage");
    await router.isReady();
    await nextTick();
    await flushPromises();

    const tableBefore = el.querySelector("table");
    expect(tableBefore).toBeTruthy();

    await vi.advanceTimersByTimeAsync(6000);
    await flushPromises();

    const tableAfter = el.querySelector("table");
    expect(tableAfter).toBe(tableBefore);

    app.unmount();
    vi.useRealTimers();
  });
});
