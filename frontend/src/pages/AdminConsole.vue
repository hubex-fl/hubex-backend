<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";
import UCard from "../components/ui/UCard.vue";
import UBadge from "../components/ui/UBadge.vue";
import UEmpty from "../components/ui/UEmpty.vue";

const toast = useToastStore();

// ── Modules ──────────────────────────────────────────────────────────────────
type Module = {
  key: string;
  label: string;
  description: string;
  enabled: boolean;
  version: string;
  capabilities: string[];
};

const modules = ref<Module[]>([]);
const modulesLoading = ref(true);
const modulesError = ref<string | null>(null);
const togglingModule = ref<string | null>(null);

async function loadModules() {
  modulesLoading.value = true;
  modulesError.value = null;
  try {
    modules.value = await apiFetch<Module[]>("/api/v1/modules");
  } catch {
    modulesError.value = "Failed to load modules";
  } finally {
    modulesLoading.value = false;
  }
}

async function toggleModule(mod: Module) {
  togglingModule.value = mod.key;
  try {
    const action = mod.enabled ? "disable" : "enable";
    await apiFetch(`/api/v1/modules/${mod.key}/${action}`, { method: "POST" });
    mod.enabled = !mod.enabled;
    toast.addToast(`Module ${mod.key} ${mod.enabled ? "enabled" : "disabled"}`, "success");
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : "Toggle failed", "error");
  } finally {
    togglingModule.value = null;
  }
}

// ── System Status ────────────────────────────────────────────────────────────
type HealthData = {
  status: string;
  database: string;
  redis: string;
  version: string;
};

const health = ref<HealthData | null>(null);
const healthLoading = ref(true);

async function loadHealth() {
  healthLoading.value = true;
  try {
    health.value = await apiFetch<HealthData>("/health");
  } catch {
    health.value = null;
  } finally {
    healthLoading.value = false;
  }
}

// ── Plan/Capabilities Summary ────────────────────────────────────────────────
const enabledCount = computed(() => modules.value.filter(m => m.enabled).length);
const totalCaps = computed(() => {
  const all = new Set<string>();
  modules.value.filter(m => m.enabled).forEach(m => (m.capabilities || []).forEach(c => all.add(c)));
  return all.size;
});

onMounted(() => {
  loadModules();
  loadHealth();
});
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-xl font-semibold text-[var(--text-primary)]">Admin Console</h1>
      <p class="text-xs text-[var(--text-muted)] mt-0.5">Module lifecycle, system status, and platform configuration</p>
    </div>

    <!-- Status Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
      <UCard padding="md">
        <div class="text-center">
          <p class="text-2xl font-bold text-[var(--primary)]">{{ enabledCount }}/{{ modules.length }}</p>
          <p class="text-[10px] text-[var(--text-muted)] mt-1">Modules Enabled</p>
        </div>
      </UCard>
      <UCard padding="md">
        <div class="text-center">
          <p class="text-2xl font-bold text-[var(--accent)]">{{ totalCaps }}</p>
          <p class="text-[10px] text-[var(--text-muted)] mt-1">Active Capabilities</p>
        </div>
      </UCard>
      <UCard padding="md">
        <div class="text-center">
          <p class="text-2xl font-bold" :class="health?.status === 'ok' ? 'text-[var(--status-ok)]' : 'text-[var(--status-bad)]'">
            {{ healthLoading ? '...' : health?.status === 'ok' ? 'Healthy' : 'Degraded' }}
          </p>
          <p class="text-[10px] text-[var(--text-muted)] mt-1">System Status</p>
        </div>
      </UCard>
    </div>

    <!-- Module List -->
    <UCard>
      <template #header>
        <h3 class="text-sm font-semibold text-[var(--text-primary)]">Module Registry</h3>
        <span class="text-xs text-[var(--text-muted)]">Enable or disable platform modules</span>
      </template>

      <div v-if="modulesLoading" class="text-xs text-[var(--text-muted)] py-4">Loading modules...</div>
      <div v-else-if="modulesError" class="text-xs text-red-400 py-4">{{ modulesError }}</div>

      <UEmpty v-else-if="!modules.length"
        title="No modules registered"
        description="Modules provide additional capabilities to the platform."
        icon="M6.429 9.75L2.25 12l4.179 2.25m0-4.5l5.571 3 5.571-3m-11.142 0L2.25 7.5 12 2.25l9.75 5.25-4.179 2.25m0 0L21.75 12l-4.179 2.25m0 0L12 16.5l-5.571-2.25m11.142 0L21.75 16.5 12 21.75 2.25 16.5l4.179-2.25"
      />

      <div v-else class="divide-y divide-[var(--border)]">
        <div v-for="mod in modules" :key="mod.key" class="flex items-center gap-4 py-3">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="text-xs font-medium text-[var(--text-primary)]">{{ mod.label || mod.key }}</span>
              <UBadge :status="mod.enabled ? 'ok' : 'neutral'" size="sm">{{ mod.enabled ? 'enabled' : 'disabled' }}</UBadge>
              <span class="text-[10px] text-[var(--text-muted)] font-mono">v{{ mod.version }}</span>
            </div>
            <p v-if="mod.description" class="text-[10px] text-[var(--text-muted)] mt-0.5 truncate">{{ mod.description }}</p>
            <div v-if="mod.capabilities?.length" class="flex flex-wrap gap-1 mt-1">
              <span
                v-for="cap in mod.capabilities.slice(0, 5)"
                :key="cap"
                class="text-[9px] px-1 py-0.5 rounded bg-[var(--bg-raised)] border border-[var(--border)] font-mono text-[var(--text-muted)]"
              >{{ cap }}</span>
              <span v-if="mod.capabilities.length > 5" class="text-[9px] text-[var(--text-muted)]">+{{ mod.capabilities.length - 5 }} more</span>
            </div>
          </div>
          <button
            :disabled="togglingModule === mod.key"
            :class="[
              'relative w-10 h-5 rounded-full transition-colors',
              mod.enabled ? 'bg-[var(--status-ok)]' : 'bg-[var(--bg-overlay)]',
            ]"
            @click="toggleModule(mod)"
          >
            <span
              :class="[
                'absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform',
                mod.enabled ? 'translate-x-5' : 'translate-x-0.5',
              ]"
            />
          </button>
        </div>
      </div>
    </UCard>

    <!-- System Info -->
    <UCard v-if="health">
      <template #header>
        <h3 class="text-sm font-semibold text-[var(--text-primary)]">System Info</h3>
      </template>
      <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
        <div>
          <span class="text-[var(--text-muted)]">Database</span>
          <p class="font-medium" :class="health.database === 'ok' ? 'text-[var(--status-ok)]' : 'text-[var(--status-bad)]'">{{ health.database }}</p>
        </div>
        <div>
          <span class="text-[var(--text-muted)]">Redis</span>
          <p class="font-medium" :class="health.redis === 'ok' ? 'text-[var(--status-ok)]' : health.redis === 'not configured' ? 'text-[var(--text-muted)]' : 'text-[var(--status-bad)]'">{{ health.redis }}</p>
        </div>
        <div>
          <span class="text-[var(--text-muted)]">Version</span>
          <p class="font-medium text-[var(--text-primary)]">{{ health.version || 'dev' }}</p>
        </div>
      </div>
    </UCard>
  </div>
</template>
