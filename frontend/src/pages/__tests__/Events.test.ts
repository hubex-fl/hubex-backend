import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { createApp, nextTick } from "vue";
import Events from "../Events.vue";
import { useCapabilities } from "../../lib/capabilities";

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
}

function clickStart(el: HTMLElement) {
  const buttons = Array.from(el.querySelectorAll("button"));
  const start = buttons.find((btn) => btn.textContent?.includes("Start"));
  start?.click();
}

describe("Events view", () => {
  const caps = useCapabilities();

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
      return new Promise<Response>(() => undefined);
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
    let vis = "visible";
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      get: () => vis,
    });
    setInput(el, "tenant.system");
    await nextTick();
    clickStart(el);
    vi.advanceTimersByTime(3000);
    await nextTick();
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    vis = "hidden";
    document.dispatchEvent(new Event("visibilitychange"));
    vi.advanceTimersByTime(4000);
    await Promise.resolve();
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    vis = "visible";
    document.dispatchEvent(new Event("visibilitychange"));
    vi.advanceTimersByTime(10);
    await Promise.resolve();
    expect(fetchSpy).toHaveBeenCalledTimes(2);

    app.unmount();
    vi.useRealTimers();
  });

  it("hides viewer without events.read capability", () => {
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
