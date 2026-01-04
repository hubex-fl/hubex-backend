import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createApp, nextTick } from "vue";
import Audit from "../Audit.vue";
import * as capMod from "../../lib/capabilities";

function mountAudit() {
  const el = document.createElement("div");
  document.body.appendChild(el);
  const app = createApp(Audit);
  app.mount(el);
  return { app, el };
}

function clickButton(el: HTMLElement, label: string) {
  const buttons = Array.from(el.querySelectorAll("button"));
  const btn = buttons.find((b) => b.textContent?.includes(label));
  btn?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  return btn as HTMLButtonElement | undefined;
}

describe("Audit view", () => {
  const caps = capMod.useCapabilities();

  beforeEach(() => {
    caps.status = "ready";
    caps.caps = new Set(["audit.read"]);
    caps.error = null;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("does not fetch without audit.read capability", () => {
    vi.spyOn(capMod, "hasCap").mockReturnValue(false);
    caps.caps = new Set();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      return Promise.reject(new Error("should not call fetch"));
    });

    const { app, el } = mountAudit();
    expect(el.textContent).toContain("Missing capability: audit.read");
    expect(fetchSpy).not.toHaveBeenCalled();
    app.unmount();
  });

  it("does not fetch when capabilities are unavailable", () => {
    caps.status = "unavailable";
    caps.caps = new Set(["audit.read"]);
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      return Promise.reject(new Error("should not call fetch"));
    });

    const { app, el } = mountAudit();
    expect(el.textContent).toContain("Capabilities unavailable");
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

    const { app, el } = mountAudit();
    clickButton(el, "Retry");
    expect(fetchSpy).toHaveBeenCalled();
    expect(capturedSignal?.aborted).toBe(false);
    app.unmount();
    expect(capturedSignal?.aborted).toBe(true);
  });

  it("manual retry triggers one fetch", async () => {
    const response = new Response(JSON.stringify([]), { status: 200 });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(response);

    const { app, el } = mountAudit();
    clickButton(el, "Retry");
    await nextTick();
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    app.unmount();
  });
});
