import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createApp, nextTick } from "vue";
import { useCapabilities } from "../../lib/capabilities";
import SystemStage from "../SystemStage.vue";
import Events from "../Events.vue";
import Effects from "../Effects.vue";
import Observability from "../Observability.vue";
import TraceHub from "../TraceHub.vue";

function mountComponent(component: any) {
  const el = document.createElement("div");
  document.body.appendChild(el);
  const app = createApp(component);
  app.mount(el);
  return { app, el };
}

describe("capabilities unavailable (deny-by-default)", () => {
  const caps = useCapabilities();

  beforeEach(() => {
    caps.status = "unavailable";
    caps.caps = new Set();
    caps.error = "Capabilities unavailable";
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("does not fetch on pages when caps are unavailable", async () => {
    vi.useFakeTimers();
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() => Promise.reject(new Error("should not call fetch")));

    const pages = [SystemStage, Events, Effects, Observability, TraceHub];
    for (const page of pages) {
      const { app } = mountComponent(page);
      await nextTick();
      await vi.runOnlyPendingTimersAsync();
      expect(fetchSpy).not.toHaveBeenCalled();
      app.unmount();
    }

    vi.useRealTimers();
  });
});
