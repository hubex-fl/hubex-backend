import { describe, it, expect } from "vitest";
import { formatUptime } from "../useMetrics";

describe("formatUptime", () => {
  it("shows only minutes for short uptimes", () => {
    expect(formatUptime(0)).toBe("0m");
    expect(formatUptime(59)).toBe("0m");
    expect(formatUptime(120)).toBe("2m");
  });

  it("shows hours and minutes when >= 1 hour", () => {
    expect(formatUptime(3600)).toBe("1h 0m");
    expect(formatUptime(3660)).toBe("1h 1m");
    expect(formatUptime(7380)).toBe("2h 3m");
  });

  it("shows days, hours, minutes when >= 1 day", () => {
    expect(formatUptime(86400)).toBe("1d 0h 0m");
    expect(formatUptime(90061)).toBe("1d 1h 1m");
    expect(formatUptime(172800 + 7200 + 780)).toBe("2d 2h 13m");
  });
});
