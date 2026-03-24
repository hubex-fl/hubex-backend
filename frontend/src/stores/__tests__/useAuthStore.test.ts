import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

// Mock the lib dependencies before importing the store
vi.mock("../../lib/api", () => ({
  apiFetch: vi.fn().mockResolvedValue({ access_token: "tok-xyz" }),
  getToken: vi.fn().mockReturnValue(null),
  setToken: vi.fn(),
  clearToken: vi.fn(),
  hasToken: vi.fn().mockReturnValue(false),
}));

vi.mock("../../lib/capabilities", () => ({
  refreshCapabilities: vi.fn().mockResolvedValue(undefined),
  useCapabilities: vi.fn().mockReturnValue({ status: "idle", caps: new Set(), error: null }),
  hasCap: vi.fn().mockReturnValue(false),
}));

import { useAuthStore } from "../auth";

describe("useAuthStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("starts unauthenticated when no stored token", () => {
    const store = useAuthStore();
    expect(store.isAuthenticated).toBe(false);
    expect(store.token).toBeNull();
  });

  it("login() calls apiFetch and sets token", async () => {
    const store = useAuthStore();
    await store.login("user@test.com", "pass");
    expect(store.token).toBe("tok-xyz");
    expect(store.isAuthenticated).toBe(true);
  });

  it("logout() clears auth state", async () => {
    const store = useAuthStore();
    await store.login("user@test.com", "pass");
    store.logout();
    expect(store.token).toBeNull();
    expect(store.isAuthenticated).toBe(false);
  });
});
