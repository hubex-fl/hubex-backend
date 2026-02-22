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

function clickButton(el: HTMLElement, label: string) {
  const buttons = Array.from(el.querySelectorAll("button"));
  const btn = buttons.find((b) => b.textContent?.trim() === label);
  btn?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  return btn as HTMLButtonElement | undefined;
}

async function flushUi() {
  await Promise.resolve();
  await nextTick();
}

async function flushAsyncUi() {
  await new Promise((resolve) => setTimeout(resolve, 0));
  await nextTick();
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

  it("does not fetch when capabilities are unavailable", () => {
    caps.status = "unavailable";
    caps.caps = new Set(["events.read"]);
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      return Promise.reject(new Error("should not call fetch"));
    });

    const { app, el } = mountEvents();
    expect(el.textContent).toContain("Capabilities unavailable");
    expect(fetchSpy).not.toHaveBeenCalled();
    app.unmount();
  });

  it("cursor controls do not fetch unless polling or retry", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      return Promise.reject(new Error("should not call fetch"));
    });

    const { app, el } = mountEvents();
    setInput(el, "tenant.system");
    await nextTick();
    const cursorInput = el.querySelector('input[type="number"]') as HTMLInputElement;
    cursorInput.value = "10";
    cursorInput.dispatchEvent(new Event("input", { bubbles: true }));
    cursorInput.dispatchEvent(new Event("change", { bubbles: true }));
    clickButton(el, "Set cursor");
    clickButton(el, "Jump to next");
    expect(fetchSpy).not.toHaveBeenCalled();
    app.unmount();
  });

  it("hides ack button without events.ack capability", () => {
    caps.caps = new Set(["events.read"]);
    const { app, el } = mountEvents();
    expect(el.textContent).not.toContain("ACK");
    app.unmount();
  });

  it("ack posts and shows success on 200", async () => {
    caps.caps = new Set(["events.read", "events.ack"]);
    const okResponse = new Response(
      JSON.stringify({ ok: true, stored_cursor: 5, status: "OK" }),
      { status: 200 }
    );
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(okResponse);

    const { app, el } = mountEvents();
    setInput(el, "tenant.system");
    await nextTick();
    clickButton(el, "ACK");
    await flushAsyncUi();
    expect(fetchSpy).toHaveBeenCalled();
    expect(el.textContent).toContain("ACK OK");
    app.unmount();
  });

  it("ack shows failure on non-200", async () => {
    caps.caps = new Set(["events.read", "events.ack"]);
    const failResponse = new Response("fail", { status: 500 });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(failResponse);

    const { app, el } = mountEvents();
    setInput(el, "tenant.system");
    await nextTick();
    clickButton(el, "ACK");
    await flushAsyncUi();
    expect(fetchSpy).toHaveBeenCalled();
    expect(el.textContent).toContain("HTTP 500");
    app.unmount();
  });
});
