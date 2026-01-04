import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createApp, nextTick } from "vue";
import Observability from "../Observability.vue";
import * as capMod from "../../lib/capabilities";

function mountObservability() {
  const el = document.createElement("div");
  document.body.appendChild(el);
  const app = createApp(Observability);
  app.mount(el);
  return { app, el };
}

function clickButton(el: HTMLElement, label: string) {
  const buttons = Array.from(el.querySelectorAll("button"));
  const btn = buttons.find((b) => b.textContent?.includes(label));
  btn?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  return btn as HTMLButtonElement | undefined;
}

describe("Observability view", () => {
  const caps = capMod.useCapabilities();

  beforeEach(() => {
    caps.status = "ready";
    caps.caps = new Set(["devices.read", "effects.read", "events.read"]);
    caps.error = null;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("does not fetch without capabilities", () => {
    vi.spyOn(capMod, "hasCap").mockReturnValue(false);
    caps.caps = new Set();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      return Promise.reject(new Error("should not call fetch"));
    });

    const { app, el } = mountObservability();
    expect(el.textContent).toContain("No capabilities available");
    expect(fetchSpy).not.toHaveBeenCalled();
    app.unmount();
  });

  it("does not fetch when capabilities are unavailable", () => {
    caps.status = "unavailable";
    caps.caps = new Set(["devices.read", "effects.read", "events.read"]);
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      return Promise.reject(new Error("should not call fetch"));
    });

    const { app, el } = mountObservability();
    expect(el.textContent).toContain("Capabilities unavailable");
    expect(fetchSpy).not.toHaveBeenCalled();
    app.unmount();
  });

  it("aborts inflight request on unmount", () => {
    let capturedSignal: AbortSignal | null = null;
    vi.spyOn(globalThis, "fetch").mockImplementation((_, init) => {
      capturedSignal = (init as RequestInit)?.signal as AbortSignal;
      return new Promise<Response>((_resolve, reject) => {
        const signal = capturedSignal;
        if (!signal) return;
        if (signal.aborted) {
          reject(Object.assign(new Error("Aborted"), { name: "AbortError" }));
          return;
        }
        signal.addEventListener(
          "abort",
          () => reject(Object.assign(new Error("Aborted"), { name: "AbortError" })),
          { once: true }
        );
      });
    });

    const { app, el } = mountObservability();
    clickButton(el, "Retry");
    expect(capturedSignal?.aborted).toBe(false);
    app.unmount();
    expect(capturedSignal?.aborted).toBe(true);
  });

  it("pauses polling when hidden and resumes on visible", async () => {
    vi.useFakeTimers();
    const response = new Response(JSON.stringify([]), { status: 200 });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(response);

    let visibility: "visible" | "hidden" = "hidden";
    Object.defineProperty(document, "visibilityState", {
      get: () => visibility,
      configurable: true,
    });
    const setVisibility = (state: "visible" | "hidden") => {
      visibility = state;
      document.dispatchEvent(new Event("visibilitychange"));
      window.dispatchEvent(new Event("visibilitychange"));
    };

    const { app, el } = mountObservability();
    try {
      await nextTick();
      clickButton(el, "Retry");
      await vi.advanceTimersByTimeAsync(5100);
      await Promise.resolve();
      expect(fetchSpy.mock.calls.length).toBe(0);

      setVisibility("visible");
      await vi.advanceTimersByTimeAsync(5100);
      await Promise.resolve();
      expect(fetchSpy.mock.calls.length).toBeGreaterThan(0);
    } finally {
      app.unmount();
      vi.useRealTimers();
    }
  });

  it("manual retry triggers a single refresh", async () => {
    vi.useFakeTimers();
    const response = new Response(JSON.stringify([]), { status: 200 });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(response);

    Object.defineProperty(document, "visibilityState", {
      get: () => "visible",
      configurable: true,
    });

    const { app, el } = mountObservability();
    try {
      await nextTick();
      clickButton(el, "Retry");
      await Promise.resolve();
      expect(fetchSpy.mock.calls.length).toBeGreaterThan(0);
      const afterRetry = fetchSpy.mock.calls.length;
      await vi.advanceTimersByTimeAsync(100);
      expect(fetchSpy.mock.calls.length).toBe(afterRetry);
    } finally {
      app.unmount();
      vi.useRealTimers();
    }
  });
});
