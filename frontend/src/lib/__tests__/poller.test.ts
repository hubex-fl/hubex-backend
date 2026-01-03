import { describe, expect, it, vi } from "vitest";
import { createPoller } from "../poller";

function setVisibility(state: "visible" | "hidden") {
  Object.defineProperty(document, "visibilityState", {
    value: state,
    configurable: true,
  });
  document.dispatchEvent(new Event("visibilitychange"));
}

describe("createPoller", () => {
  it("pauses when hidden and resumes on visible", async () => {
    vi.useFakeTimers();
    let calls = 0;
    const poller = createPoller(async () => {
      calls += 1;
    }, 100, { pauseWhenHidden: true });

    setVisibility("hidden");
    poller.start();
    vi.advanceTimersByTime(300);
    expect(calls).toBe(0);

    setVisibility("visible");
    vi.advanceTimersByTime(10);
    expect(calls).toBeGreaterThan(0);

    poller.stop();
    vi.useRealTimers();
  });
});
