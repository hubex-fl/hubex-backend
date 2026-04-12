<script setup lang="ts">
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import { useEntities, type Entity, type EntityBinding, type EntityHealth } from "../composables/useEntities";
import { apiFetch } from "../lib/api";
import { useCapabilities, hasCap } from "../lib/capabilities";
import { parseApiError, mapErrorToUserText } from "../lib/errors";
import UCard from "../components/ui/UCard.vue";
import UButton from "../components/ui/UButton.vue";
import UBadge from "../components/ui/UBadge.vue";
import UInput from "../components/ui/UInput.vue";
import UModal from "../components/ui/UModal.vue";
import UEmpty from "../components/ui/UEmpty.vue";
import USkeleton from "../components/ui/USkeleton.vue";
import UToggle from "../components/ui/UToggle.vue";
import UEntitySelect from "../components/ui/UEntitySelect.vue";
import UInfoTooltip from "../components/ui/UInfoTooltip.vue";

const { t, tm, rt } = useI18n();
const caps = useCapabilities();
const { entities, loading, error, reload } = useEntities();

// ── Entity type options (combobox) — Sprint 10 C4: i18n labels ─────────────
const ENTITY_TYPE_KEYS = ["building", "floor", "room", "zone", "property", "site", "machine", "area", "group", "custom"] as const;
const entityTypeOptions = computed(() =>
  ENTITY_TYPE_KEYS.map(key => ({
    value: key,
    label: t(`pages.entities.types.${key}`),
  }))
);
const createTypeDropdownOpen = ref(false);
const editTypeDropdownOpen = ref(false);
const createTypeQuery = ref("");
const editTypeQuery = ref("");

// ── Search & filter ──────────────────────────────────────────────────────────
const search = ref("");
const typeFilter = ref("all"); // "all" | "group" | "custom"

const filteredEntities = computed(() => {
  let list = entities.value;

  // Sort: groups first, then alphabetically
  list = [...list].sort((a, b) => {
    if (a.type === "group" && b.type !== "group") return -1;
    if (a.type !== "group" && b.type === "group") return 1;
    return a.entity_id.localeCompare(b.entity_id);
  });

  if (typeFilter.value === "group") {
    list = list.filter((e) => e.type === "group");
  } else if (typeFilter.value === "custom") {
    list = list.filter((e) => e.type !== "group");
  }

  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    list = list.filter(
      (e) =>
        e.entity_id.toLowerCase().includes(q) ||
        (e.name ?? "").toLowerCase().includes(q),
    );
  }

  return list;
});

// ── Expand state ─────────────────────────────────────────────────────────────
const expanded = ref(new Set<string>());
const bindingsMap = ref(new Map<string, EntityBinding[]>());
const healthMap = ref(new Map<string, EntityHealth>());
const expandLoading = ref(new Set<string>());

async function toggleExpanded(entityId: string) {
  if (expanded.value.has(entityId)) {
    expanded.value = new Set([...expanded.value].filter((id) => id !== entityId));
    return;
  }
  expanded.value = new Set([...expanded.value, entityId]);
  if (!bindingsMap.value.has(entityId)) {
    expandLoading.value = new Set([...expandLoading.value, entityId]);
    try {
      const [bindings, health] = await Promise.all([
        apiFetch<EntityBinding[]>(`/api/v1/entities/${entityId}/devices`),
        apiFetch<EntityHealth>(`/api/v1/entities/${entityId}/health`),
      ]);
      const bMap = new Map(bindingsMap.value);
      bMap.set(entityId, bindings);
      bindingsMap.value = bMap;
      const hMap = new Map(healthMap.value);
      hMap.set(entityId, health);
      healthMap.value = hMap;
    } catch {
      // ignore
    } finally {
      expandLoading.value = new Set([...expandLoading.value].filter((id) => id !== entityId));
    }
  }
}

async function refreshEntityData(entityId: string) {
  expandLoading.value = new Set([...expandLoading.value, entityId]);
  try {
    const [bindings, health] = await Promise.all([
      apiFetch<EntityBinding[]>(`/api/v1/entities/${entityId}/devices`),
      apiFetch<EntityHealth>(`/api/v1/entities/${entityId}/health`),
    ]);
    const bMap = new Map(bindingsMap.value);
    bMap.set(entityId, bindings);
    bindingsMap.value = bMap;
    const hMap = new Map(healthMap.value);
    hMap.set(entityId, health);
    healthMap.value = hMap;
  } catch {
    // ignore
  } finally {
    expandLoading.value = new Set([...expandLoading.value].filter((id) => id !== entityId));
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function healthToBadge(hs: string | null): "ok" | "warn" | "bad" | "neutral" {
  if (!hs) return "neutral";
  if (hs === "ok") return "ok";
  if (hs === "stale") return "warn";
  return "bad";
}

function healthLabel(hs: string | null): string {
  if (!hs) return t('pages.entities.unknownStatus');
  return hs;
}

function typeBadgeStatus(type: string): "info" | "neutral" {
  return type === "group" ? "info" : "neutral";
}

// ── Create Entity ─────────────────────────────────────────────────────────────
const createOpen = ref(false);
const createEntityId = ref("");
const createEntityType = ref("room");
const createEntityName = ref("");
const createParentId = ref("");
const createLocationName = ref("");
const createLocationLat = ref("");
const createLocationLng = ref("");
const createError = ref<string | null>(null);
const createLoading = ref(false);

function openCreate() {
  createEntityId.value = "";
  createEntityType.value = "room";
  createEntityName.value = "";
  createParentId.value = "";
  createLocationName.value = "";
  createLocationLat.value = "";
  createLocationLng.value = "";
  createError.value = null;
  createOpen.value = true;
}

async function submitCreate() {
  if (!createEntityId.value.trim()) {
    createError.value = t('pages.entities.entityIdRequired');
    return;
  }
  if (!createEntityType.value.trim()) {
    createError.value = t('pages.entities.typeRequired');
    return;
  }
  createLoading.value = true;
  createError.value = null;
  try {
    await apiFetch("/api/v1/entities", {
      method: "POST",
      body: JSON.stringify({
        entity_id: createEntityId.value.trim(),
        type: createEntityType.value.trim(),
        name: createEntityName.value.trim() || null,
        parent_id: createParentId.value.trim() || null,
        location_name: createLocationName.value.trim() || null,
        location_lat: createLocationLat.value ? parseFloat(createLocationLat.value) : null,
        location_lng: createLocationLng.value ? parseFloat(createLocationLng.value) : null,
      }),
    });
    createOpen.value = false;
    await reload();
  } catch (err: unknown) {
    const info = parseApiError(err);
    createError.value = mapErrorToUserText(info, t('pages.entities.createFailed'));
  } finally {
    createLoading.value = false;
  }
}

// ── Edit Entity ───────────────────────────────────────────────────────────────
const editOpen = ref(false);
const editEntityId = ref("");
const editEntityType = ref("");
const editEntityName = ref("");
const editParentId = ref("");
const editLocationName = ref("");
const editLocationLat = ref("");
const editLocationLng = ref("");
const editError = ref<string | null>(null);
const editLoading = ref(false);

function openEdit(entity: Entity) {
  editEntityId.value = entity.entity_id;
  editEntityType.value = entity.type;
  editEntityName.value = entity.name ?? "";
  editParentId.value = entity.parent_id ?? "";
  editLocationName.value = entity.location_name ?? "";
  editLocationLat.value = entity.location_lat != null ? String(entity.location_lat) : "";
  editLocationLng.value = entity.location_lng != null ? String(entity.location_lng) : "";
  editError.value = null;
  editOpen.value = true;
}

async function submitEdit() {
  editLoading.value = true;
  editError.value = null;
  try {
    await apiFetch(`/api/v1/entities/${editEntityId.value}`, {
      method: "PUT",
      body: JSON.stringify({
        type: editEntityType.value.trim() || null,
        name: editEntityName.value.trim() || null,
        parent_id: editParentId.value.trim() || null,
        location_name: editLocationName.value.trim() || null,
        location_lat: editLocationLat.value ? parseFloat(editLocationLat.value) : null,
        location_lng: editLocationLng.value ? parseFloat(editLocationLng.value) : null,
      }),
    });
    editOpen.value = false;
    await reload();
  } catch (err: unknown) {
    const info = parseApiError(err);
    editError.value = mapErrorToUserText(info, t('pages.entities.updateFailed'));
  } finally {
    editLoading.value = false;
  }
}

// ── Delete Entity ─────────────────────────────────────────────────────────────
const deleteOpen = ref(false);
const deleteEntityId = ref("");
const deleteLoading = ref(false);
const deleteError = ref<string | null>(null);

function openDelete(entity: Entity) {
  deleteEntityId.value = entity.entity_id;
  deleteError.value = null;
  deleteOpen.value = true;
}

async function submitDelete() {
  deleteLoading.value = true;
  deleteError.value = null;
  try {
    await apiFetch(`/api/v1/entities/${deleteEntityId.value}`, { method: "DELETE" });
    expanded.value = new Set([...expanded.value].filter((id) => id !== deleteEntityId.value));
    const bMap = new Map(bindingsMap.value);
    bMap.delete(deleteEntityId.value);
    bindingsMap.value = bMap;
    const hMap = new Map(healthMap.value);
    hMap.delete(deleteEntityId.value);
    healthMap.value = hMap;
    deleteOpen.value = false;
    await reload();
  } catch (err: unknown) {
    const info = parseApiError(err);
    deleteError.value = mapErrorToUserText(info, t('pages.entities.deleteFailed'));
  } finally {
    deleteLoading.value = false;
  }
}

// ── Bind Device ───────────────────────────────────────────────────────────────
const bindOpen = ref(false);
const bindTargetEntityId = ref("");
const bindDeviceId = ref("");
const bindPriority = ref("0");
const bindEnabled = ref(true);
const bindError = ref<string | null>(null);
const bindLoading = ref(false);

function openBind(entityId: string) {
  bindTargetEntityId.value = entityId;
  bindDeviceId.value = "";
  bindPriority.value = "0";
  bindEnabled.value = true;
  bindError.value = null;
  bindOpen.value = true;
}

async function submitBind() {
  if (!bindDeviceId.value) {
    bindError.value = t('pages.entities.selectDeviceError');
    return;
  }
  bindLoading.value = true;
  bindError.value = null;
  try {
    // UEntitySelect returns device_uid (string). Look up numeric device ID.
    const devices = await apiFetch<Array<{ id: number; device_uid: string }>>("/api/v1/devices");
    const device = devices.find((d) => d.device_uid === bindDeviceId.value);
    if (!device) {
      bindError.value = t('pages.entities.deviceNotFound');
      bindLoading.value = false;
      return;
    }
    await apiFetch(`/api/v1/entities/${bindTargetEntityId.value}/devices`, {
      method: "POST",
      body: JSON.stringify({
        device_ids: [device.id],
        priority: parseInt(bindPriority.value) || 0,
        enabled: bindEnabled.value,
      }),
    });
    bindOpen.value = false;
    await refreshEntityData(bindTargetEntityId.value);
  } catch (err: unknown) {
    const info = parseApiError(err);
    bindError.value = mapErrorToUserText(info, t('pages.entities.bindFailed'));
  } finally {
    bindLoading.value = false;
  }
}

// ── Unbind Device ─────────────────────────────────────────────────────────────
async function unbindDevice(entityId: string, deviceId: number) {
  try {
    await apiFetch(`/api/v1/entities/${entityId}/devices/${deviceId}`, { method: "DELETE" });
    await refreshEntityData(entityId);
  } catch {
    // ignore
  }
}

// ── Toggle binding enabled ────────────────────────────────────────────────────
async function toggleBinding(entityId: string, deviceId: number, enabled: boolean) {
  try {
    await apiFetch(`/api/v1/entities/${entityId}/devices/${deviceId}`, {
      method: "PUT",
      body: JSON.stringify({ enabled }),
    });
    await refreshEntityData(entityId);
  } catch {
    // ignore
  }
}
</script>

<template>
  <div class="space-y-5">
    <!-- ── Page Header ──────────────────────────────────────────────────────── -->
    <div class="flex items-start justify-between gap-4">
      <div>
        <div class="flex items-center">
          <h1 class="text-xl font-semibold text-[var(--text-primary)]">{{ t('pages.entities.title') }}</h1>
          <UInfoTooltip
            :title="t('infoTooltips.entities.title')"
            :items="tm('infoTooltips.entities.items').map((i: any) => rt(i))"
            tourId="entities-overview"
          />
        </div>
        <p class="text-sm text-[var(--text-muted)] mt-0.5">{{ t('pages.entities.subtitle') }}</p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <UBadge status="neutral" :label="t('pages.entities.entitiesCount', { n: entities.length })" />
        <UButton
          v-if="caps.status === 'ready' && hasCap('entities.write')"
          size="sm"
          variant="primary"
          @click="openCreate"
        >
          {{ t('pages.entities.newEntity') }}
        </UButton>
      </div>
    </div>

    <!-- ── Caps not ready ───────────────────────────────────────────────────── -->
    <template v-if="caps.status !== 'ready'">
      <UCard>
        <UEmpty
          :title="t('pages.entities.notAuthenticated')"
          :description="t('pages.entities.notAuthenticatedHint')"
        />
      </UCard>
    </template>

    <template v-else>
      <!-- ── Toolbar ─────────────────────────────────────────────────────────── -->
      <UCard padding="sm">
        <div class="flex flex-wrap items-center gap-3">
          <div class="flex-1 min-w-[180px]">
            <UInput
              v-model="search"
              variant="search"
              :placeholder="t('pages.entities.searchPlaceholder')"
            />
          </div>
          <select
            v-model="typeFilter"
            data-testid="entities-type-filter"
            class="input text-sm"
          >
            <option value="all">{{ t('pages.entities.filterAll') }}</option>
            <option value="group">{{ t('pages.entities.filterGroup') }}</option>
            <option value="custom">{{ t('pages.entities.filterCustom') }}</option>
          </select>
          <span class="text-xs text-[var(--text-muted)] whitespace-nowrap">
            {{ t('pages.entities.countSummary', { shown: filteredEntities.length, total: entities.length }) }}
          </span>
        </div>
      </UCard>

      <!-- ── Error banner ────────────────────────────────────────────────────── -->
      <div
        v-if="error"
        class="rounded-lg border border-[var(--status-bad)]/30 bg-[var(--status-bad-bg)] px-4 py-3 text-sm text-[var(--status-bad)]"
      >
        {{ error }}
      </div>

      <!-- ── Entity list ─────────────────────────────────────────────────────── -->
      <UCard padding="none">
        <!-- Loading skeletons -->
        <div v-if="loading" class="divide-y divide-[var(--border)]">
          <div v-for="i in 3" :key="i" class="flex items-center gap-3 px-4 py-3">
            <USkeleton class="h-4 w-4 rounded" />
            <USkeleton class="h-4 w-40" />
            <USkeleton class="h-4 w-24 ml-4" />
            <USkeleton class="h-4 w-16 ml-2" />
          </div>
        </div>

        <!-- Empty states -->
        <template v-else-if="filteredEntities.length === 0">
          <UEmpty
            v-if="entities.length === 0"
            :title="t('pages.entities.emptyTitle')"
            :description="t('pages.entities.emptyDescription')"
            icon="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z"
          >
            <UButton
              v-if="hasCap('entities.write')"
              size="sm"
              variant="primary"
              @click="openCreate"
            >
              {{ t('pages.entities.newEntity') }}
            </UButton>
          </UEmpty>
          <UEmpty
            v-else
            :title="t('pages.entities.emptyFilterTitle')"
            :description="t('pages.entities.emptyFilterDescription')"
            icon="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 15.803a7.5 7.5 0 0010.607 10.607z"
          />
        </template>

        <!-- Entity rows -->
        <div v-else class="divide-y divide-[var(--border)]">
          <div v-for="entity in filteredEntities" :key="entity.entity_id">
            <!-- Row header -->
            <div
              class="flex items-center gap-3 px-4 py-3 hover:bg-[var(--bg-raised)] transition-colors cursor-pointer"
              @click="toggleExpanded(entity.entity_id)"
            >
              <!-- Chevron -->
              <svg
                class="h-3.5 w-3.5 shrink-0 text-[var(--text-muted)] transition-transform duration-150"
                :class="expanded.has(entity.entity_id) ? 'rotate-90' : ''"
                fill="none"
                stroke="currentColor"
                stroke-width="2.5"
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
              </svg>

              <!-- Identity -->
              <div class="flex-1 min-w-0 flex items-center gap-2 flex-wrap">
                <span class="font-mono font-medium text-sm text-[var(--text-primary)]">
                  {{ entity.entity_id }}
                </span>
                <span
                  v-if="entity.name"
                  class="text-xs text-[var(--text-muted)] truncate"
                >
                  {{ entity.name }}
                </span>
                <!-- Parent indicator -->
                <span
                  v-if="entity.parent_id"
                  class="text-[10px] text-[var(--text-muted)] flex items-center gap-0.5"
                  :title="t('pages.entities.childOf') + ' ' + entity.parent_id"
                >
                  <svg class="h-2.5 w-2.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" /></svg>
                  {{ entity.parent_id }}
                </span>
                <!-- Location indicator -->
                <span
                  v-if="entity.location_name"
                  class="text-[10px] text-[var(--text-muted)] flex items-center gap-0.5"
                  :title="String(entity.location_name)"
                >
                  <svg class="h-2.5 w-2.5 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" /></svg>
                  <span class="truncate max-w-[120px]">{{ entity.location_name }}</span>
                </span>
              </div>

              <!-- Badges -->
              <div class="flex items-center gap-2 shrink-0" @click.stop>
                <UBadge
                  :status="typeBadgeStatus(entity.type)"
                  :label="entity.type"
                />
                <UBadge
                  :status="healthToBadge(entity.health_status)"
                  :label="healthLabel(entity.health_status)"
                />
              </div>

              <!-- Actions -->
              <div
                v-if="hasCap('entities.write')"
                class="flex items-center gap-1 shrink-0"
                @click.stop
              >
                <UButton
                  size="sm"
                  variant="ghost"
                  @click="openEdit(entity)"
                >
                  {{ t('pages.entities.editAction') }}
                </UButton>
                <UButton
                  size="sm"
                  variant="ghost"
                  class="text-[var(--status-bad)] hover:text-[var(--status-bad)]"
                  @click="openDelete(entity)"
                >
                  {{ t('pages.entities.deleteAction') }}
                </UButton>
              </div>
            </div>

            <!-- Expanded section -->
            <div
              v-show="expanded.has(entity.entity_id)"
              class="border-t border-[var(--border)] bg-[var(--bg-raised)]"
            >
              <!-- Loading state -->
              <div v-if="expandLoading.has(entity.entity_id)" class="p-4 space-y-2">
                <USkeleton class="h-4 w-48" />
                <USkeleton class="h-4 w-64" />
              </div>

              <!-- Content -->
              <div v-else class="p-4 space-y-3">
                <!-- Health summary -->
                <div
                  v-if="healthMap.get(entity.entity_id)"
                  class="flex items-center gap-4 text-xs"
                >
                  <span class="text-[var(--text-muted)] font-medium">{{ t('pages.entities.healthLabel') }}</span>
                  <span class="text-[var(--text-muted)]">
                    {{ t('pages.entities.healthDevices', { n: healthMap.get(entity.entity_id)!.device_count }) }}
                  </span>
                  <span class="text-[var(--status-ok)]">
                    {{ t('pages.entities.healthOnline', { n: healthMap.get(entity.entity_id)!.online }) }}
                  </span>
                  <span class="text-[var(--status-warn)]">
                    {{ t('pages.entities.healthStale', { n: healthMap.get(entity.entity_id)!.stale }) }}
                  </span>
                  <span class="text-[var(--status-bad)]">
                    {{ t('pages.entities.healthOffline', { n: healthMap.get(entity.entity_id)!.offline }) }}
                  </span>
                  <UBadge
                    :status="healthToBadge(healthMap.get(entity.entity_id)!.worst_health)"
                    :label="healthMap.get(entity.entity_id)!.worst_health || t('pages.entities.unknownStatus')"
                  />
                </div>

                <!-- Bindings list -->
                <div
                  v-if="(bindingsMap.get(entity.entity_id) ?? []).length === 0"
                  class="text-xs text-[var(--text-muted)]"
                >
                  {{ t('pages.entities.noDevicesBound') }}
                </div>
                <table v-else class="w-full text-xs">
                  <thead>
                    <tr class="text-left text-[var(--text-muted)]">
                      <th class="pb-1.5 pr-4 font-medium">{{ t('pages.entities.colDeviceId') }}</th>
                      <th class="pb-1.5 pr-4 font-medium" :title="t('pages.entities.enableBindingTooltip')">{{ t('pages.entities.colEnabled') }}</th>
                      <th class="pb-1.5 pr-4 font-medium" :title="t('pages.entities.priorityTooltip')">{{ t('pages.entities.colPriority') }}</th>
                      <th class="pb-1.5 font-medium"></th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-[var(--border)]">
                    <tr
                      v-for="b in bindingsMap.get(entity.entity_id)"
                      :key="b.device_id"
                    >
                      <td class="py-1.5 pr-4 font-mono text-[var(--text-primary)]">
                        {{ b.device_id }}
                      </td>
                      <td class="py-1.5 pr-4">
                        <UToggle
                          :model-value="b.enabled"
                          size="sm"
                          :disabled="!hasCap('entities.write')"
                          @update:model-value="(v) => toggleBinding(entity.entity_id, b.device_id, v)"
                        />
                      </td>
                      <td class="py-1.5 pr-4 text-[var(--text-secondary)]">
                        {{ b.priority }}
                      </td>
                      <td class="py-1.5">
                        <UButton
                          v-if="hasCap('entities.write')"
                          size="sm"
                          variant="ghost"
                          class="text-[var(--status-bad)]"
                          @click="unbindDevice(entity.entity_id, b.device_id)"
                        >
                          {{ t('pages.entities.unbindAction') }}
                        </UButton>
                      </td>
                    </tr>
                  </tbody>
                </table>

                <!-- Bind Device button -->
                <UButton
                  v-if="hasCap('entities.write')"
                  size="sm"
                  variant="secondary"
                  @click="openBind(entity.entity_id)"
                >
                  {{ t('pages.entities.bindDeviceAction') }}
                </UButton>
              </div>
            </div>
          </div>
        </div>
      </UCard>
    </template>

    <!-- ── Create Entity Modal ────────────────────────────────────────────────── -->
    <UModal :open="createOpen" :title="t('pages.entities.modalNewTitle')" @close="createOpen = false">
      <div class="space-y-4">
        <UInput
          v-model="createEntityId"
          :label="t('pages.entities.entityIdLabel')"
          :placeholder="t('pages.entities.entityIdPlaceholder')"
        />
        <!-- ── Section 1: Basic Info ── -->
        <div class="rounded-lg border border-[var(--border)] bg-[var(--bg-raised)]/30 p-3 space-y-3">
          <p class="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wide">{{ t('pages.entities.sectionBasic') }}</p>

          <!-- Type as proper select (not combobox) -->
          <div>
            <label class="block text-xs font-medium text-[var(--text-muted)] mb-1">{{ t('pages.entities.typeLabel') }}</label>
            <select
              v-model="createEntityType"
              class="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--primary)]/50"
            >
              <option v-for="opt in entityTypeOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
            <p class="text-[9px] text-[var(--text-muted)] mt-1">{{ t('pages.entities.typeHint') }}</p>
          </div>

          <UInput
            v-model="createEntityName"
            :label="t('pages.entities.nameLabelOptional')"
            :placeholder="t('pages.entities.namePlaceholder')"
          />
        </div>

        <!-- ── Section 2: Hierarchy ── -->
        <div class="rounded-lg border border-[var(--border)] bg-[var(--bg-raised)]/30 p-3 space-y-2">
          <p class="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wide">{{ t('pages.entities.sectionHierarchy') }}</p>
          <p class="text-[9px] text-[var(--text-muted)] leading-relaxed">{{ t('pages.entities.hierarchyExplainer') }}</p>
          <UEntitySelect
            v-model="createParentId"
            entity-type="entity"
            :label="t('pages.entities.parentEntity')"
            :placeholder="t('pages.entities.parentEntityPlaceholder')"
            optional
          />
        </div>

        <!-- ── Section 3: Location ── -->
        <div class="rounded-lg border border-[var(--border)] bg-[var(--bg-raised)]/30 p-3 space-y-3">
          <p class="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wide">{{ t('pages.entities.sectionLocation') }}</p>
          <UInput
            v-model="createLocationName"
            :label="t('pages.entities.locationName')"
            :placeholder="t('pages.entities.locationNamePlaceholder')"
          />
          <div class="grid grid-cols-2 gap-3">
            <UInput
              v-model="createLocationLat"
              :label="t('pages.entities.locationLat')"
              type="number"
              placeholder="52.520"
            />
            <UInput
              v-model="createLocationLng"
              :label="t('pages.entities.locationLng')"
              type="number"
              placeholder="13.405"
            />
          </div>
          <p class="text-[9px] text-[var(--text-muted)]">{{ t('pages.entities.locationGpsHint') }}</p>
        </div>

        <div
          v-if="createError"
          class="rounded-lg border border-[var(--status-bad)]/30 bg-[var(--status-bad-bg)] px-3 py-2 text-xs text-[var(--status-bad)]"
        >
          {{ createError }}
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton variant="secondary" size="sm" @click="createOpen = false">{{ t('common.cancel') }}</UButton>
          <UButton
            variant="primary"
            size="sm"
            :loading="createLoading"
            @click="submitCreate"
          >
            {{ t('common.create') }}
          </UButton>
        </div>
      </template>
    </UModal>

    <!-- ── Edit Entity Modal ──────────────────────────────────────────────────── -->
    <UModal :open="editOpen" :title="t('pages.entities.modalEditTitle')" @close="editOpen = false">
      <div class="space-y-4">
        <div class="text-xs text-[var(--text-muted)]">
          {{ t('pages.entities.modalEditingLabel') }} <span class="font-mono font-medium text-[var(--text-primary)]">{{ editEntityId }}</span>
        </div>
        <!-- Type combobox -->
        <div class="relative flex flex-col gap-1">
          <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ t('pages.entities.typeLabel') }}</label>
          <input
            :value="editTypeDropdownOpen ? editTypeQuery : editEntityType"
            :placeholder="t('pages.entities.typePlaceholder')"
            class="input w-full pr-8"
            autocomplete="off"
            @input="editTypeQuery = ($event.target as HTMLInputElement).value; editEntityType = editTypeQuery"
            @focus="editTypeDropdownOpen = true; editTypeQuery = editEntityType"
            @blur="setTimeout(() => editTypeDropdownOpen = false, 150)"
          />
          <svg class="absolute right-2 top-[calc(50%+8px)] -translate-y-1/2 h-3.5 w-3.5 text-[var(--text-muted)] pointer-events-none" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
          </svg>
          <div v-if="editTypeDropdownOpen" class="absolute left-0 right-0 top-full mt-1 z-50 max-h-40 overflow-y-auto rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] shadow-xl">
            <button
              v-for="opt in entityTypeOptions.filter(o => !editTypeQuery || o.value.includes(editTypeQuery.toLowerCase()))"
              :key="opt.value"
              type="button"
              class="w-full text-left px-3 py-2 text-xs hover:bg-[var(--bg-raised)] transition-colors"
              :class="opt.value === editEntityType ? 'text-[var(--primary)]' : 'text-[var(--text-primary)]'"
              @mousedown.prevent="editEntityType = opt.value; editTypeDropdownOpen = false; editTypeQuery = ''"
            >
              {{ t('pages.entities.types.' + opt.value) }}
              <span class="text-[10px] text-[var(--text-muted)] ml-1">({{ opt.value }})</span>
            </button>
          </div>
          <p class="text-[10px] text-[var(--text-muted)] mt-0.5">{{ t('pages.entities.typeHint') }}</p>
        </div>
        <UInput
          v-model="editEntityName"
          :label="t('pages.entities.nameLabel')"
          :placeholder="t('pages.entities.namePlaceholder')"
        />
        <!-- Parent Entity (optional) -->
        <UEntitySelect
          v-model="editParentId"
          entity-type="entity"
          :label="t('pages.entities.parentEntity')"
          :placeholder="t('pages.entities.parentEntityPlaceholder')"
          optional
        />
        <!-- Location fields -->
        <UInput
          v-model="editLocationName"
          :label="t('pages.entities.locationName')"
          :placeholder="t('pages.entities.locationNamePlaceholder')"
        />
        <div class="grid grid-cols-2 gap-3">
          <UInput
            v-model="editLocationLat"
            :label="t('pages.entities.locationLat')"
            type="number"
            placeholder="52.520"
          />
          <UInput
            v-model="editLocationLng"
            :label="t('pages.entities.locationLng')"
            type="number"
            placeholder="13.405"
          />
        </div>
        <div
          v-if="editError"
          class="rounded-lg border border-[var(--status-bad)]/30 bg-[var(--status-bad-bg)] px-3 py-2 text-xs text-[var(--status-bad)]"
        >
          {{ editError }}
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton variant="secondary" size="sm" @click="editOpen = false">{{ t('common.cancel') }}</UButton>
          <UButton
            variant="primary"
            size="sm"
            :loading="editLoading"
            @click="submitEdit"
          >
            {{ t('common.save') }}
          </UButton>
        </div>
      </template>
    </UModal>

    <!-- ── Delete Entity Modal ────────────────────────────────────────────────── -->
    <UModal :open="deleteOpen" :title="t('pages.entities.modalDeleteTitle')" size="sm" @close="deleteOpen = false">
      <div class="space-y-3">
        <p class="text-sm text-[var(--text-secondary)]">
          {{ t('pages.entities.deleteConfirmPrefix') }}
          <span class="font-mono font-medium text-[var(--text-primary)]">{{ deleteEntityId }}</span>{{ t('pages.entities.deleteConfirmSuffix') }}
        </p>
        <div
          v-if="deleteError"
          class="rounded-lg border border-[var(--status-bad)]/30 bg-[var(--status-bad-bg)] px-3 py-2 text-xs text-[var(--status-bad)]"
        >
          {{ deleteError }}
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton variant="secondary" size="sm" @click="deleteOpen = false">{{ t('common.cancel') }}</UButton>
          <UButton
            variant="danger"
            size="sm"
            :loading="deleteLoading"
            @click="submitDelete"
          >
            {{ t('common.delete') }}
          </UButton>
        </div>
      </template>
    </UModal>

    <!-- ── Bind Device Modal ──────────────────────────────────────────────────── -->
    <UModal :open="bindOpen" :title="t('pages.entities.modalBindTitle')" @close="bindOpen = false">
      <div class="space-y-4">
        <div class="text-xs text-[var(--text-muted)]">
          {{ t('pages.entities.bindingToLabel') }}
          <span class="font-mono font-medium text-[var(--text-primary)]">{{ bindTargetEntityId }}</span>
        </div>
        <UEntitySelect
          v-model="bindDeviceId"
          entity-type="device"
          :label="t('pages.entities.deviceFieldLabel')"
          :placeholder="t('pages.entities.deviceFieldPlaceholder')"
        />
        <div>
          <UInput
            v-model="bindPriority"
            :label="t('pages.entities.colPriority')"
            type="number"
            placeholder="0"
          />
          <p class="text-[10px] text-[var(--text-muted)] mt-1">{{ t('pages.entities.priorityTooltip') }}</p>
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ t('pages.entities.enabledLabel') }}</span>
          <UToggle v-model="bindEnabled" :label="t('pages.entities.enableBindingLabel')" />
          <p class="text-[10px] text-[var(--text-muted)]">{{ t('pages.entities.enableBindingTooltip') }}</p>
        </div>
        <div
          v-if="bindError"
          class="rounded-lg border border-[var(--status-bad)]/30 bg-[var(--status-bad-bg)] px-3 py-2 text-xs text-[var(--status-bad)]"
        >
          {{ bindError }}
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton variant="secondary" size="sm" @click="bindOpen = false">{{ t('common.cancel') }}</UButton>
          <UButton
            variant="primary"
            size="sm"
            :loading="bindLoading"
            @click="submitBind"
          >
            {{ t('pages.entities.bindAction') }}
          </UButton>
        </div>
      </template>
    </UModal>
  </div>
</template>
