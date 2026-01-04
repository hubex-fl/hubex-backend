import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createApp, nextTick } from "vue";
import * as capMod from "../../lib/capabilities";
import Correlation from "../Correlation.vue";

vi.mock("vue-router", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

function mountCorrelation() {
  const el = document.createElement("div");
  document.body.appendChild(el);
  const app = createApp(Correlation);
  app.mount(el);
  return { app, el };
}

function setInputByPlaceholder(el: HTMLElement, placeholder: string, value: string) {
  const input = Array.from(el.querySelectorAll("input")).find(
    (node) => (node as HTMLInputElement).placeholder === placeholder
  ) as HTMLInputElement | undefined;
  if (!input) return;
  input.value = value;
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
}

function clickButton(el: HTMLElement, label: string) {
  const buttons = Array.from(el.querySelectorAll("button"));
  const btn = buttons.find((b) => b.textContent?.trim() === label);
  btn?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  return btn as HTMLButtonElement | undefined;
}

describe("Correlation view", () => {
  const caps = capMod.useCapabilities();

  beforeEach(() => {
    caps.status = "ready";
    caps.caps = new Set(["tasks.read", "effects.read", "devices.read"]);
    caps.error = null;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("does not fetch when capabilities are unavailable", () => {
    caps.status = "unavailable";
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      return Promise.reject(new Error("should not call fetch"));
    });

    const { app, el } = mountCorrelation();
    expect(el.textContent).toContain("Capabilities unavailable");
    expect(fetchSpy).not.toHaveBeenCalled();
    app.unmount();
  });

  it("does not fetch without effects.read", async () => {
    caps.caps = new Set(["tasks.read"]);
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      return Promise.reject(new Error("should not call fetch"));
    });

    const { app, el } = mountCorrelation();
    setInputByPlaceholder(el, "effect_id", "abc");
    await nextTick();
    clickButton(el, "Lookup");
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(el.textContent).toContain("Missing capability: effects.read");
    app.unmount();
  });

  it("aborts inflight request on unmount", async () => {
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

    const { app, el } = mountCorrelation();
    setInputByPlaceholder(el, "device id", "1");
    setInputByPlaceholder(el, "context_key", "ctx");
    await nextTick();
    clickButton(el, "Search");
    expect(fetchSpy).toHaveBeenCalled();
    expect(capturedSignal?.aborted).toBe(false);
    app.unmount();
    expect(capturedSignal?.aborted).toBe(true);
  });

  it("manual retry triggers a single fetch", async () => {
    const failResponse = new Response("fail", { status: 500 });
    const okResponse = new Response("[]", { status: 200 });
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(failResponse)
      .mockResolvedValueOnce(okResponse);

    const { app, el } = mountCorrelation();
    setInputByPlaceholder(el, "device id", "1");
    setInputByPlaceholder(el, "context_key", "ctx");
    await nextTick();
    clickButton(el, "Search");
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();
    clickButton(el, "Retry");
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();
    expect(fetchSpy).toHaveBeenCalledTimes(2);
    app.unmount();
  });
});
