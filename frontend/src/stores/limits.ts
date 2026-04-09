import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { apiFetch } from "../lib/api";

export interface LimitEntry {
  current: number;
  max: number;
  exceeded: boolean;
}

export interface LimitsData {
  edition: string;
  upgrade_url: string;
  limits: {
    users: LimitEntry;
    devices: LimitEntry;
    api_keys: LimitEntry;
    dashboards: LimitEntry;
    automations: LimitEntry;
    custom_endpoints: LimitEntry;
  };
}

export type LimitResource = keyof LimitsData["limits"];

export const useLimitsStore = defineStore("limits", () => {
  const data = ref<LimitsData | null>(null);
  const loading = ref(false);
  const loaded = ref(false);
  const dismissed = ref(false);

  const edition = computed(() => data.value?.edition ?? "community");
  const upgradeUrl = computed(() => data.value?.upgrade_url ?? "https://hubex.io/pricing");
  const isCommunity = computed(() => edition.value === "community");

  const limits = computed(() => data.value?.limits ?? null);

  /** Resources that are currently over their soft limit. */
  const exceededResources = computed<LimitResource[]>(() => {
    if (!data.value) return [];
    return (Object.keys(data.value.limits) as LimitResource[]).filter(
      (key) => data.value!.limits[key].exceeded,
    );
  });

  const hasExceeded = computed(() => exceededResources.value.length > 0);

  /** The first exceeded resource for the top banner display. */
  const primaryExceeded = computed<{ resource: LimitResource; entry: LimitEntry } | null>(() => {
    if (!data.value || exceededResources.value.length === 0) return null;
    const key = exceededResources.value[0];
    return { resource: key, entry: data.value.limits[key] };
  });

  async function load() {
    if (loading.value) return;
    loading.value = true;
    try {
      data.value = await apiFetch<LimitsData>("/api/v1/system/limits");
      loaded.value = true;
    } catch {
      // Silently fail — edition info is non-critical
    } finally {
      loading.value = false;
    }
  }

  function dismiss() {
    dismissed.value = true;
  }

  function getLimit(resource: LimitResource): LimitEntry | null {
    return data.value?.limits[resource] ?? null;
  }

  return {
    data,
    loading,
    loaded,
    dismissed,
    edition,
    upgradeUrl,
    isCommunity,
    limits,
    exceededResources,
    hasExceeded,
    primaryExceeded,
    load,
    dismiss,
    getLimit,
  };
});
