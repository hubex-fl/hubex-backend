import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createApp, nextTick } from "vue";
import Effects from "../Effects.vue";
import * as capMod from "../../lib/capabilities";

function mountEffects() {
  const el = document.createElement("div");
  document.body.appendChild(el);
  const app = createApp(Effects);
  app.mount(el);
  return { app, el };
}

function clickButton(el: HTMLElement, label: string) {
  const buttons = Array.from(el.querySelectorAll("button"));
  const btn = buttons.find((b) => b.textContent?.includes(label));
  btn?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  return btn as HTMLButtonElement | undefined;
}

describe("Effects view", () => {
  const caps = capMod.useCapabilities();

  beforeEach(() => {
    caps.status = "ready";
    caps.caps = new Set(["effects.read"]);
    caps.error = null;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("does not fetch without effects.read capability", () => {
    vi.spyOn(capMod, "hasCap").mockReturnValue(false);
    caps.caps = new Set();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      return Promise.reject(new Error("should not call fetch"));
    });

    const { app, el } = mountEffects();
    expect(el.textContent).toContain("Missing capability: effects.read");
    expect(fetchSpy).not.toHaveBeenCalled();
    app.unmount();
  });

  it("aborts request on unmount", () => {
    let capturedSignal: AbortSignal | null = null;
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((_, init) => {
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

    const { app, el } = mountEffects();
    clickButton(el, "Retry");
    expect(fetchSpy).toHaveBeenCalled();
    expect(capturedSignal?.aborted).toBe(false);
    app.unmount();
    expect(capturedSignal?.aborted).toBe(true);
  });

  it("pauses polling when hidden and resumes on visible", async () => {
    vi.useFakeTimers();
    const response = new Response(JSON.stringify([]), { status: 200 });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(response);

    const { app, el } = mountEffects();
    try {
      await nextTick();
      let visibility: "visible" | "hidden" = "visible";
      Object.defineProperty(document, "visibilityState", {
        get: () => visibility,
        configurable: true,
      });
      const setVisibility = (state: "visible" | "hidden") => {
        visibility = state;
        document.dispatchEvent(new Event("visibilitychange"));
        window.dispatchEvent(new Event("visibilitychange"));
      };

      setVisibility("hidden");
      await nextTick();
      const beforeHiddenStart = fetchSpy.mock.calls.length;
      clickButton(el, "Start");
      await vi.advanceTimersByTimeAsync(3100);
      await Promise.resolve();
      expect(fetchSpy.mock.calls.length).toBe(beforeHiddenStart);

      setVisibility("visible");
      await vi.advanceTimersByTimeAsync(3100);
      await Promise.resolve();
      expect(fetchSpy.mock.calls.length).toBeGreaterThan(0);
    } finally {
      app.unmount();
      vi.useRealTimers();
    }
  });
});
