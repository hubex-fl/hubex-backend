import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { createApp, nextTick } from "vue";
import Events from "../Events.vue";
import * as capMod from "../../lib/capabilities";

function mountEvents() {
  const el = document.createElement("div");
  document.body.appendChild(el);
  const app = createApp(Events);
  app.mount(el);
  return { app, el };
}

function setInput(el: HTMLElement, value: string) {
  const input = el.querySelector("input") as HTMLInputElement;
  input.value = value;
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
}

function clickStart(el: HTMLElement) {
  const buttons = Array.from(el.querySelectorAll("button"));
  const start = buttons.find((btn) => btn.textContent?.includes("Start"));
  start?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  return start as HTMLButtonElement | undefined;
}

describe("Events view", () => {
  const caps = capMod.useCapabilities();

  beforeEach(() => {
    caps.status = "ready";
    caps.caps = new Set(["events.read"]);
    caps.error = null;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
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

    const { app, el } = mountEvents();
    setInput(el, "tenant.system");
    clickStart(el);
    expect(fetchSpy).toHaveBeenCalled();
    expect(capturedSignal?.aborted).toBe(false);
    app.unmount();
    expect(capturedSignal?.aborted).toBe(true);
  });

  it("pauses polling when hidden and resumes on visible", async () => {
    vi.useFakeTimers();
    const response = new Response(
      JSON.stringify({ stream: "tenant.system", cursor: 0, next_cursor: 0, items: [] }),
      { status: 200 }
    );
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(response);

    const { app, el } = mountEvents();
    try {
      await nextTick();
      expect(el.textContent).not.toContain("Missing capability: events.read");
      expect(capMod.hasCap("events.read")).toBe(true);

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
      expect(document.visibilityState).toBe("visible");

      setInput(el, "tenant.system");
      await nextTick();
      const startBtn = clickStart(el);
      expect(startBtn).toBeTruthy();
      await nextTick();
      expect(startBtn?.disabled).toBe(true);
      expect(el.textContent).not.toContain("Stream required");
      await Promise.resolve();
      expect(fetchSpy.mock.calls.length).toBeGreaterThan(0);
      const afterStart = fetchSpy.mock.calls.length;

      setVisibility("hidden");
      await nextTick();
      await vi.advanceTimersByTimeAsync(3100);
      await Promise.resolve();
      expect(fetchSpy.mock.calls.length).toBe(afterStart);

      setVisibility("visible");
      await vi.advanceTimersByTimeAsync(3100);
      await Promise.resolve();
      expect(fetchSpy.mock.calls.length).toBeGreaterThan(afterStart);
    } finally {
      app.unmount();
      vi.useRealTimers();
    }
  });

  it("hides viewer without events.read capability", () => {
    vi.spyOn(capMod, "hasCap").mockReturnValue(false);
    caps.caps = new Set();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      return Promise.reject(new Error("should not call fetch"));
    });

    const { app, el } = mountEvents();
    expect(el.textContent).toContain("Missing capability: events.read");
    expect(fetchSpy).not.toHaveBeenCalled();
    app.unmount();
  });
});
