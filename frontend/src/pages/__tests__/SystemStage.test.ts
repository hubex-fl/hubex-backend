import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { createApp } from "vue";
import SystemStage from "../SystemStage.vue";
import { useCapabilities } from "../../lib/capabilities";

function mountSystemStage() {
  const el = document.createElement("div");
  document.body.appendChild(el);
  const app = createApp(SystemStage);
  app.mount(el);
  return { app, el };
}

describe("SystemStage", () => {
  const caps = useCapabilities();

  beforeEach(() => {
    caps.status = "ready";
    caps.caps = new Set(["devices.read"]);
    caps.error = null;
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
});
