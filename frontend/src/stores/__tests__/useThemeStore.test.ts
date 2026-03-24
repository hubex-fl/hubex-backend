import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

// jsdom doesn't implement matchMedia — provide a stub
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

import { useThemeStore } from "../theme";

describe("useThemeStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    document.documentElement.classList.remove("dark");
  });

  afterEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    document.documentElement.classList.remove("dark");
  });

  it("setTheme() updates theme to light", () => {
    const store = useThemeStore();
    store.setTheme("light");
    expect(store.theme).toBe("light");
  });

  it("setTheme() updates theme to dark", () => {
    const store = useThemeStore();
    store.setTheme("dark");
    expect(store.theme).toBe("dark");
  });

  it("setTheme() applies data-theme to documentElement", () => {
    const store = useThemeStore();
    store.setTheme("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("toggleTheme() changes theme", () => {
    const store = useThemeStore();
    const before = store.theme;
    store.toggleTheme();
    expect(store.theme).not.toBe(before);
  });

  it("setTheme('dark') adds dark class", () => {
    const store = useThemeStore();
    store.setTheme("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("setTheme('light') removes dark class", () => {
    const store = useThemeStore();
    store.setTheme("dark");
    store.setTheme("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("setTheme() persists to localStorage", () => {
    const store = useThemeStore();
    store.setTheme("light");
    expect(localStorage.getItem("hubex-theme")).toBe("light");
  });
});
