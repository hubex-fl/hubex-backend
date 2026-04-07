import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { getToken, setToken, clearToken, apiFetch } from "../lib/api";
import { refreshCapabilities } from "../lib/capabilities";

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(getToken());
  const orgId = ref<number | null>(null);

  const isAuthenticated = computed(() => Boolean(token.value));

  function _decodePayload(t: string): Record<string, unknown> {
    try {
      const parts = t.split(".");
      if (parts.length < 2) return {};
      const json = atob(parts[1].replace(/-/g, "+").replace(/_/g, "/"));
      return JSON.parse(json);
    } catch {
      return {};
    }
  }

  function _syncFromToken(t: string | null) {
    token.value = t;
    if (t) {
      const payload = _decodePayload(t);
      orgId.value = typeof payload.org_id === "number" ? payload.org_id : null;
    } else {
      orgId.value = null;
    }
  }

  const mfaPending = ref(false);
  const mfaToken = ref<string | null>(null);
  const mfaMethods = ref<string[]>([]);

  async function login(email: string, password: string): Promise<"ok" | "mfa_required"> {
    const res = await apiFetch<{ access_token?: string; mfa_required?: boolean; mfa_token?: string; methods?: string[] }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });

    if (res.mfa_required && res.mfa_token) {
      mfaPending.value = true;
      mfaToken.value = res.mfa_token;
      mfaMethods.value = res.methods || ["totp"];
      return "mfa_required";
    }

    if (res.access_token) {
      setToken(res.access_token);
      _syncFromToken(res.access_token);
      await refreshCapabilities();
    }
    return "ok";
  }

  async function verifyMfa(code: string): Promise<void> {
    if (!mfaToken.value) throw new Error("No MFA challenge pending");
    const res = await apiFetch<{ access_token: string }>("/api/v1/auth/mfa/verify", {
      method: "POST",
      body: JSON.stringify({ mfa_token: mfaToken.value, code }),
    });
    setToken(res.access_token);
    _syncFromToken(res.access_token);
    mfaPending.value = false;
    mfaToken.value = null;
    mfaMethods.value = [];
    await refreshCapabilities();
  }

  function logout(): void {
    clearToken();
    _syncFromToken(null);
  }

  async function switchOrg(id: number): Promise<void> {
    const res = await apiFetch<{ access_token: string }>("/api/v1/auth/switch-org", {
      method: "POST",
      body: JSON.stringify({ org_id: id }),
    });
    setToken(res.access_token);
    _syncFromToken(res.access_token);
    await refreshCapabilities();
  }

  // Initialise from localStorage on store creation
  _syncFromToken(getToken());

  return { token, orgId, isAuthenticated, mfaPending, mfaToken, mfaMethods, login, verifyMfa, logout, switchOrg };
});
