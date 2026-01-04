import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createApp, nextTick } from "vue";
import TraceHub from "../TraceHub.vue";
import * as capMod from "../../lib/capabilities";

function mountTraceHub() {
  const el = document.createElement("div");
  document.body.appendChild(el);
  const app = createApp(TraceHub);
  app.mount(el);
  return { app, el };
}

describe("TraceHub view", () => {
  const caps = capMod.useCapabilities();

  beforeEach(() => {
    caps.status = "ready";
    caps.caps = new Set(["events.read", "effects.read"]);
    caps.error = null;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("does not fetch when capabilities are unavailable", () => {
    caps.status = "unavailable";
    caps.caps = new Set();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      return Promise.reject(new Error("should not call fetch"));
    });

    const { app, el } = mountTraceHub();
    expect(el.textContent).toContain("Capabilities unavailable");
    expect(fetchSpy).not.toHaveBeenCalled();
    app.unmount();
  });

  it("does not fetch events without events.read capability", () => {
    caps.status = "ready";
    caps.caps = new Set(["effects.read"]);
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      return Promise.reject(new Error("should not call fetch"));
    });

    const { app, el } = mountTraceHub();
    expect(el.textContent).toContain("Missing capability: events.read");
    expect(fetchSpy).not.toHaveBeenCalled();
    app.unmount();
  });

  it("does not fetch effects without effects.read capability", async () => {
    caps.status = "ready";
    caps.caps = new Set(["events.read"]);
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      return Promise.reject(new Error("should not call fetch"));
    });

    const { app, el } = mountTraceHub();
    const buttons = Array.from(el.querySelectorAll("button"));
    const effectsBtn = buttons.find((btn) => btn.textContent?.includes("Effects"));
    effectsBtn?.click();
    await nextTick();
    expect(el.textContent).toContain("Missing capability: effects.read");
    expect(fetchSpy).not.toHaveBeenCalled();
    app.unmount();
  });
});
