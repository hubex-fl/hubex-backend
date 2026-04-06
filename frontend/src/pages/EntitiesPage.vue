<script setup lang="ts">
import { ref, computed } from "vue";
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

const caps = useCapabilities();
const { entities, loading, error, reload } = useEntities();

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
  if (!hs) return "unknown";
  return hs;
}

function typeBadgeStatus(type: string): "info" | "neutral" {
  return type === "group" ? "info" : "neutral";
}

// ── Create Entity ─────────────────────────────────────────────────────────────
const createOpen = ref(false);
const createEntityId = ref("");
const createEntityType = ref("sensor");
const createEntityName = ref("");
const createError = ref<string | null>(null);
const createLoading = ref(false);

function openCreate() {
  createEntityId.value = "";
  createEntityType.value = "sensor";
  createEntityName.value = "";
  createError.value = null;
  createOpen.value = true;
}

async function submitCreate() {
  if (!createEntityId.value.trim()) {
    createError.value = "Entity ID is required";
    return;
  }
  if (!createEntityType.value.trim()) {
    createError.value = "Type is required";
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
      }),
    });
    createOpen.value = false;
    await reload();
  } catch (err: unknown) {
    const info = parseApiError(err);
    createError.value = mapErrorToUserText(info, "Failed to create entity");
  } finally {
    createLoading.value = false;
  }
}

// ── Edit Entity ───────────────────────────────────────────────────────────────
const editOpen = ref(false);
const editEntityId = ref("");
const editEntityType = ref("");
const editEntityName = ref("");
const editError = ref<string | null>(null);
const editLoading = ref(false);

function openEdit(entity: Entity) {
  editEntityId.value = entity.entity_id;
  editEntityType.value = entity.type;
  editEntityName.value = entity.name ?? "";
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
      }),
    });
    editOpen.value = false;
    await reload();
  } catch (err: unknown) {
    const info = parseApiError(err);
    editError.value = mapErrorToUserText(info, "Failed to update entity");
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
    deleteError.value = mapErrorToUserText(info, "Failed to delete entity");
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
  const deviceIdNum = parseInt(bindDeviceId.value);
  if (!bindDeviceId.value || isNaN(deviceIdNum)) {
    bindError.value = "Enter a valid Device ID";
    return;
  }
  bindLoading.value = true;
  bindError.value = null;
  try {
    await apiFetch(`/api/v1/entities/${bindTargetEntityId.value}/devices`, {
      method: "POST",
      body: JSON.stringify({
        device_ids: [deviceIdNum],
        priority: parseInt(bindPriority.value) || 0,
        enabled: bindEnabled.value,
      }),
    });
    bindOpen.value = false;
    await refreshEntityData(bindTargetEntityId.value);
  } catch (err: unknown) {
    const info = parseApiError(err);
    bindError.value = mapErrorToUserText(info, "Failed to bind device");
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
        <h1 class="text-xl font-semibold text-[var(--text-primary)]">Entities &amp; Groups</h1>
        <p class="text-sm text-[var(--text-muted)] mt-0.5">Logical groups of devices — rooms, machines, systems. Group devices to monitor health and automate together.</p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <UBadge status="neutral" :label="`${entities.length} entities`" />
        <UButton
          v-if="caps.status === 'ready' && hasCap('entities.write')"
          size="sm"
          variant="primary"
          @click="openCreate"
        >
          + New Entity
        </UButton>
      </div>
    </div>

    <!-- ── Caps not ready ───────────────────────────────────────────────────── -->
    <template v-if="caps.status !== 'ready'">
      <UCard>
        <UEmpty
          title="Not authenticated"
          description="Paste a valid token to view entities."
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
              placeholder="Search entity ID or name…"
            />
          </div>
          <select
            v-model="typeFilter"
            data-testid="entities-type-filter"
            class="input text-sm"
          >
            <option value="all">All types</option>
            <option value="group">Groups</option>
            <option value="custom">Custom</option>
          </select>
          <span class="text-xs text-[var(--text-muted)] whitespace-nowrap">
            {{ filteredEntities.length }} of {{ entities.length }} entities
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
            title="No entities yet"
            description="Entities represent logical things — rooms, machines, systems — that group your devices. Create your first entity to start organizing."
            icon="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z"
          >
            <UButton
              v-if="hasCap('entities.write')"
              size="sm"
              variant="primary"
              @click="openCreate"
            >
              + New Entity
            </UButton>
          </UEmpty>
          <UEmpty
            v-else
            title="No entities match your filter"
            description="Try adjusting your search or type filter."
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
                  Edit
                </UButton>
                <UButton
                  size="sm"
                  variant="ghost"
                  class="text-[var(--status-bad)] hover:text-[var(--status-bad)]"
                  @click="openDelete(entity)"
                >
                  Delete
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
                  <span class="text-[var(--text-muted)] font-medium">Health:</span>
                  <span class="text-[var(--text-muted)]">
                    {{ healthMap.get(entity.entity_id)!.device_count }} devices
                  </span>
                  <span class="text-[var(--status-ok)]">
                    {{ healthMap.get(entity.entity_id)!.online }} online
                  </span>
                  <span class="text-[var(--status-warn)]">
                    {{ healthMap.get(entity.entity_id)!.stale }} stale
                  </span>
                  <span class="text-[var(--status-bad)]">
                    {{ healthMap.get(entity.entity_id)!.offline }} offline
                  </span>
                  <UBadge
                    :status="healthToBadge(healthMap.get(entity.entity_id)!.worst_health)"
                    :label="healthMap.get(entity.entity_id)!.worst_health || 'unknown'"
                  />
                </div>

                <!-- Bindings list -->
                <div
                  v-if="(bindingsMap.get(entity.entity_id) ?? []).length === 0"
                  class="text-xs text-[var(--text-muted)]"
                >
                  No devices bound.
                </div>
                <table v-else class="w-full text-xs">
                  <thead>
                    <tr class="text-left text-[var(--text-muted)]">
                      <th class="pb-1.5 pr-4 font-medium">Device ID</th>
                      <th class="pb-1.5 pr-4 font-medium">Enabled</th>
                      <th class="pb-1.5 pr-4 font-medium">Priority</th>
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
                          Unbind
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
                  + Bind Device
                </UButton>
              </div>
            </div>
          </div>
        </div>
      </UCard>
    </template>

    <!-- ── Create Entity Modal ────────────────────────────────────────────────── -->
    <UModal :open="createOpen" title="New Entity" @close="createOpen = false">
      <div class="space-y-4">
        <UInput
          v-model="createEntityId"
          label="Entity ID"
          placeholder="e.g. sensor-group-1"
        />
        <UInput
          v-model="createEntityType"
          label="Type"
          placeholder="e.g. sensor, group, actuator"
        />
        <UInput
          v-model="createEntityName"
          label="Name (optional)"
          placeholder="Human-readable name"
        />
        <div
          v-if="createError"
          class="rounded-lg border border-[var(--status-bad)]/30 bg-[var(--status-bad-bg)] px-3 py-2 text-xs text-[var(--status-bad)]"
        >
          {{ createError }}
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton variant="secondary" size="sm" @click="createOpen = false">Cancel</UButton>
          <UButton
            variant="primary"
            size="sm"
            :loading="createLoading"
            @click="submitCreate"
          >
            Create
          </UButton>
        </div>
      </template>
    </UModal>

    <!-- ── Edit Entity Modal ──────────────────────────────────────────────────── -->
    <UModal :open="editOpen" title="Edit Entity" @close="editOpen = false">
      <div class="space-y-4">
        <div class="text-xs text-[var(--text-muted)]">
          Editing: <span class="font-mono font-medium text-[var(--text-primary)]">{{ editEntityId }}</span>
        </div>
        <UInput
          v-model="editEntityType"
          label="Type"
          placeholder="e.g. sensor, group, actuator"
        />
        <UInput
          v-model="editEntityName"
          label="Name"
          placeholder="Human-readable name"
        />
        <div
          v-if="editError"
          class="rounded-lg border border-[var(--status-bad)]/30 bg-[var(--status-bad-bg)] px-3 py-2 text-xs text-[var(--status-bad)]"
        >
          {{ editError }}
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton variant="secondary" size="sm" @click="editOpen = false">Cancel</UButton>
          <UButton
            variant="primary"
            size="sm"
            :loading="editLoading"
            @click="submitEdit"
          >
            Save
          </UButton>
        </div>
      </template>
    </UModal>

    <!-- ── Delete Entity Modal ────────────────────────────────────────────────── -->
    <UModal :open="deleteOpen" title="Delete Entity" size="sm" @close="deleteOpen = false">
      <div class="space-y-3">
        <p class="text-sm text-[var(--text-secondary)]">
          Delete entity
          <span class="font-mono font-medium text-[var(--text-primary)]">{{ deleteEntityId }}</span>?
          This removes all device bindings.
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
          <UButton variant="secondary" size="sm" @click="deleteOpen = false">Cancel</UButton>
          <UButton
            variant="danger"
            size="sm"
            :loading="deleteLoading"
            @click="submitDelete"
          >
            Delete
          </UButton>
        </div>
      </template>
    </UModal>

    <!-- ── Bind Device Modal ──────────────────────────────────────────────────── -->
    <UModal :open="bindOpen" title="Bind Device" @close="bindOpen = false">
      <div class="space-y-4">
        <div class="text-xs text-[var(--text-muted)]">
          Binding to entity:
          <span class="font-mono font-medium text-[var(--text-primary)]">{{ bindTargetEntityId }}</span>
        </div>
        <UEntitySelect
          v-model="bindDeviceId"
          entity-type="device"
          label="Device"
          placeholder="Select device..."
        />
        <div>
          <UInput
            v-model="bindPriority"
            label="Priority"
            type="number"
            placeholder="0"
          />
          <p class="text-[10px] text-[var(--text-muted)] mt-1">Priority when multiple bindings apply (higher = more important)</p>
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">Enabled</span>
          <UToggle v-model="bindEnabled" label="Enable binding" />
          <p class="text-[10px] text-[var(--text-muted)]">Disabled bindings are kept but ignored during evaluation</p>
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
          <UButton variant="secondary" size="sm" @click="bindOpen = false">Cancel</UButton>
          <UButton
            variant="primary"
            size="sm"
            :loading="bindLoading"
            @click="submitBind"
          >
            Bind
          </UButton>
        </div>
      </template>
    </UModal>
  </div>
</template>
