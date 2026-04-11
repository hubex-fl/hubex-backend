import { defineStore } from "pinia";
import { ref } from "vue";
import { apiFetch, fetchMe, hasToken } from "../lib/api";

const STORAGE_KEY = "hubex_user_prefs";

export const usePreferencesStore = defineStore("preferences", () => {
  const preferences = ref<Record<string, unknown>>({});
  const loaded = ref(false);

  /** Load preferences from API (falls back to localStorage). */
  async function load(): Promise<void> {
    // Try localStorage first for instant availability
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) preferences.value = JSON.parse(stored);
    } catch { /* ignore */ }

    if (!hasToken()) return;

    try {
      // Sprint 8 R4 Perf-01: use the shared fetchMe() so this call collapses
      // with the one from refreshCapabilities() during app bootstrap.
      const data = await fetchMe<{ preferences: Record<string, unknown> }>();
      preferences.value = data.preferences ?? {};
      localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences.value));
    } catch {
      // Keep localStorage fallback
    }
    loaded.value = true;
  }

  /** Update a single preference key. Optimistic + API persist. */
  async function update(key: string, value: unknown): Promise<void> {
    // Optimistic update
    preferences.value = { ...preferences.value, [key]: value };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences.value));

    if (!hasToken()) return;

    try {
      const result = await apiFetch<Record<string, unknown>>("/api/v1/users/me/preferences", {
        method: "PATCH",
        body: JSON.stringify({ preferences: { [key]: value } }),
      });
      preferences.value = result;
      localStorage.setItem(STORAGE_KEY, JSON.stringify(result));
    } catch {
      // Keep optimistic update
    }
  }

  /** Get a preference value with type assertion. */
  function get<T>(key: string, defaultValue: T): T {
    const val = preferences.value[key];
    return val !== undefined ? (val as T) : defaultValue;
  }

  return { preferences, loaded, load, update, get };
});
