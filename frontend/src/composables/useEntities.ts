import { ref, onMounted, onUnmounted } from "vue";
import { apiFetch } from "../lib/api";
import { createPoller } from "../lib/poller";
import { parseApiError, mapErrorToUserText } from "../lib/errors";

export type Entity = {
  entity_id: string;
  type: string;
  name: string | null;
  tags: unknown[] | Record<string, unknown> | null;
  health_last_seen_at: string | null;
  health_status: string | null;
  created_at: string;
  parent_id: string | null;
  location_name: string | null;
  location_lat: number | null;
  location_lng: number | null;
};

export type EntityBinding = {
  device_id: number;
  enabled: boolean;
  priority: number;
};

export type EntityHealth = {
  entity_id: string;
  device_count: number;
  online: number;
  stale: number;
  offline: number;
  worst_health: string;
};

export function useEntities(intervalMs = 15_000) {
  const entities = ref<Entity[]>([]);
  const loading = ref(true);
  const error = ref<string | null>(null);

  async function fetchEntities(): Promise<void> {
    try {
      entities.value = await apiFetch<Entity[]>("/api/v1/entities");
      error.value = null;
    } catch (err: unknown) {
      const info = parseApiError(err);
      error.value = mapErrorToUserText(info, "Failed to load entities");
    } finally {
      loading.value = false;
    }
  }

  const poller = createPoller(fetchEntities, intervalMs);

  onMounted(() => poller.start());
  onUnmounted(() => poller.stop());

  return { entities, loading, error, reload: fetchEntities };
}
