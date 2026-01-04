import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createApp, nextTick } from "vue";
import Executions from "../Executions.vue";
import * as capMod from "../../lib/capabilities";

function mountPage() {
  const el = document.createElement("div");
  document.body.appendChild(el);
  const app = createApp(Executions);
  app.mount(el);
  return { app, el };
}

function setInput(el: HTMLElement, label: string, value: string) {
  const inputs = Array.from(el.querySelectorAll("input"));
  const input = inputs.find((i) => i.previousElementSibling?.textContent?.includes(label)) as HTMLInputElement | undefined;
  if (!input) return;
  input.value = value;
  input.dispatchEvent(new Event("input", { bubbles: true }));
}

function clickButton(el: HTMLElement, label: string) {
  const buttons = Array.from(el.querySelectorAll("button"));
  const btn = buttons.find((b) => b.textContent?.includes(label));
  btn?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  return btn as HTMLButtonElement | undefined;
}

describe("Executions view", () => {
  const caps = capMod.useCapabilities();

  beforeEach(() => {
    caps.status = "ready";
    caps.caps = new Set(["tasks.read"]);
    caps.error = null;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("does not fetch without tasks.read capability", () => {
    vi.spyOn(capMod, "hasCap").mockReturnValue(false);
    caps.caps = new Set();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      return Promise.reject(new Error("should not call fetch"));
    });

    const { app, el } = mountPage();
    expect(el.textContent).toContain("Missing capability: tasks.read");
    expect(fetchSpy).not.toHaveBeenCalled();
    app.unmount();
  });

  it("does not fetch when capabilities are unavailable", () => {
    caps.status = "unavailable";
    caps.caps = new Set(["tasks.read"]);
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      return Promise.reject(new Error("should not call fetch"));
    });

    const { app, el } = mountPage();
    expect(el.textContent).toContain("Capabilities unavailable");
    expect(fetchSpy).not.toHaveBeenCalled();
    app.unmount();
  });

  it("aborts request on unmount", async () => {
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

    const { app, el } = mountPage();
    setInput(el, "Device ID", "123");
    clickButton(el, "Load");
    await nextTick();
    expect(fetchSpy).toHaveBeenCalled();
    expect(capturedSignal?.aborted).toBe(false);
    app.unmount();
    expect(capturedSignal?.aborted).toBe(true);
  });

  it("manual refresh triggers one fetch", async () => {
    const response = new Response(JSON.stringify([]), { status: 200 });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(response);

    const { app, el } = mountPage();
    setInput(el, "Device ID", "123");
    clickButton(el, "Load");
    await nextTick();
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    app.unmount();
  });
});
