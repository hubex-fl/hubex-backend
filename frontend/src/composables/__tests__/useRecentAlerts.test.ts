import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { severityStatus, relativeTime } from "../useRecentAlerts";

describe("severityStatus", () => {
  it("maps critical → bad", () => {
    expect(severityStatus("critical")).toBe("bad");
  });

  it("maps warning → warn", () => {
    expect(severityStatus("warning")).toBe("warn");
  });

  it("maps info and any other value → info", () => {
    expect(severityStatus("info")).toBe("info");
    expect(severityStatus("unknown")).toBe("info");
  });
});

describe("relativeTime", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2024-06-01T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows 'gerade eben' for timestamps within the same minute", () => {
    const ts = new Date("2024-06-01T12:00:00Z").toISOString();
    expect(relativeTime(ts)).toBe("gerade eben");
  });

  it("shows minutes ago", () => {
    const ts = new Date("2024-06-01T11:55:00Z").toISOString();
    expect(relativeTime(ts)).toBe("vor 5m");
  });

  it("shows hours ago", () => {
    const ts = new Date("2024-06-01T10:00:00Z").toISOString();
    expect(relativeTime(ts)).toBe("vor 2h");
  });

  it("shows days ago", () => {
    const ts = new Date("2024-05-30T12:00:00Z").toISOString();
    expect(relativeTime(ts)).toBe("vor 2d");
  });
});
