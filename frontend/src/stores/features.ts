/**
 * Features store — runtime feature-flag map for the frontend.
 *
 * Mirrors the backend FEATURES registry. Loaded once per session from
 * `GET /api/v1/config/features`, used by:
 *   - sidebar filter (DefaultLayout.vue)
 *   - router guard (main.ts → beforeEach)
 *   - Settings → Features section + /setup wizard
 *
 * When a flag is toggled via `setEnabled`, the store refreshes itself so
 * the UI updates immediately.
 */
import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { apiFetch, hasToken } from "../lib/api";

export interface FeatureFlag {
  key: string;
  name: string;
  description: string;
  category: string;
  default: boolean;
  requires: string[];
  enabled: boolean;
  updated_at: string | null;
  updated_by: string | null;
}

interface FeatureFlagsListResponse {
  features: FeatureFlag[];
  categories: string[];
  total: number;
  enabled_count: number;
}

export const useFeaturesStore = defineStore("features", () => {
  const flags = ref<Record<string, FeatureFlag>>({});
  const categories = ref<string[]>([]);
  const total = ref(0);
  const enabledCount = ref(0);
  const loaded = ref(false);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function load(force = false): Promise<void> {
    if (loading.value) return;
    if (loaded.value && !force) return;
    if (!hasToken()) return; // no session → skip
    loading.value = true;
    error.value = null;
    try {
      const res = await apiFetch<FeatureFlagsListResponse>(
        "/api/v1/config/features"
      );
      const map: Record<string, FeatureFlag> = {};
      for (const f of res.features) map[f.key] = f;
      flags.value = map;
      categories.value = res.categories;
      total.value = res.total;
      enabledCount.value = res.enabled_count;
      loaded.value = true;
    } catch (e: any) {
      error.value = e?.message || "Failed to load features";
    } finally {
      loading.value = false;
    }
  }

  function isEnabled(key: string): boolean {
    const f = flags.value[key];
    if (f == null) return true; // unknown key = not gated
    return f.enabled;
  }

  async function setEnabled(key: string, enabled: boolean): Promise<FeatureFlag> {
    const updated = await apiFetch<FeatureFlag>(
      `/api/v1/config/features/${encodeURIComponent(key)}`,
      {
        method: "PUT",
        body: JSON.stringify({ enabled }),
      }
    );
    flags.value[key] = updated;
    enabledCount.value = Object.values(flags.value).filter((f) => f.enabled).length;
    return updated;
  }

  const byCategory = computed(() => {
    const groups: Record<string, FeatureFlag[]> = {};
    for (const f of Object.values(flags.value)) {
      if (!groups[f.category]) groups[f.category] = [];
      groups[f.category].push(f);
    }
    for (const cat of Object.keys(groups)) {
      groups[cat].sort((a, b) => a.name.localeCompare(b.name));
    }
    return groups;
  });

  return {
    flags,
    categories,
    total,
    enabledCount,
    loaded,
    loading,
    error,
    byCategory,
    load,
    isEnabled,
    setEnabled,
  };
});
