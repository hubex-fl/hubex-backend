import { describe, it, expect } from "vitest";
import { eventBadgeStatus, payloadPreview } from "../useEventStream";

describe("eventBadgeStatus", () => {
  it("device.* → info (cyan)", () => {
    expect(eventBadgeStatus("device.online")).toBe("info");
    expect(eventBadgeStatus("device.offline")).toBe("info");
  });

  it("alert.* → bad (red)", () => {
    expect(eventBadgeStatus("alert.fired")).toBe("bad");
    expect(eventBadgeStatus("alert.resolved")).toBe("bad");
  });

  it("task.* → ok (lime/green)", () => {
    expect(eventBadgeStatus("task.completed")).toBe("ok");
    expect(eventBadgeStatus("task.failed")).toBe("ok");
  });

  it("telemetry.* → warn (amber)", () => {
    expect(eventBadgeStatus("telemetry.reading")).toBe("warn");
  });

  it("org.* and unknown → neutral", () => {
    expect(eventBadgeStatus("org.created")).toBe("neutral");
    expect(eventBadgeStatus("other.event")).toBe("neutral");
  });
});

describe("payloadPreview", () => {
  it("returns JSON for short payloads", () => {
    expect(payloadPreview({ key: "value" })).toBe('{"key":"value"}');
  });

  it("truncates payloads longer than 60 characters", () => {
    const payload = { data: "x".repeat(100) };
    const result = payloadPreview(payload);
    expect(result.endsWith("…")).toBe(true);
    expect(result.length).toBe(61); // 60 chars + "…"
  });

  it("returns the full string for exactly 60-char payloads", () => {
    // Build a payload that serializes to exactly 60 chars
    const str60 = "x".repeat(55);
    const payload = { a: str60 }; // '{"a":"' + 55x + '"}' = 6 + 55 + 2 = 63 chars → truncated
    const result = payloadPreview(payload);
    expect(result.endsWith("…")).toBe(true);
  });

  it("does not truncate payloads at or under 60 characters", () => {
    const payload = { id: 1 };
    const json = JSON.stringify(payload); // '{"id":1}' = 8 chars
    expect(payloadPreview(payload)).toBe(json);
    expect(payloadPreview(payload).endsWith("…")).toBe(false);
  });
});
