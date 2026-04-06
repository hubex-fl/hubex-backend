<script setup lang="ts">
import { ref, onMounted } from "vue";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";
import UModal from "../components/ui/UModal.vue";
import UBadge from "../components/ui/UBadge.vue";
import UEmpty from "../components/ui/UEmpty.vue";

const toast = useToastStore();

type PluginItem = {
  id: number; key: string; name: string; version: string;
  description: string | null; author: string | null;
  manifest: Record<string, unknown>; required_caps: string[];
  sandbox_mode: string; enabled: boolean;
  execution_count: number; error_count: number;
  last_executed_at: string | null; installed_at: string;
  config: Record<string, unknown> | null;
};

const plugins = ref<PluginItem[]>([]);
const loading = ref(true);

const installOpen = ref(false);
const formKey = ref("");
const formName = ref("");
const formVersion = ref("0.1.0");
const formDesc = ref("");
const formAuthor = ref("");
const installing = ref(false);

const error = ref<string | null>(null);

async function loadPlugins() {
  loading.value = true;
  error.value = null;
  try { plugins.value = await apiFetch<PluginItem[]>("/api/v1/plugins"); }
  catch { error.value = "Failed to load plugins"; plugins.value = []; }
  finally { loading.value = false; }
}

async function handleInstall() {
  installing.value = true;
  try {
    await apiFetch("/api/v1/plugins", {
      method: "POST",
      body: JSON.stringify({
        key: formKey.value.trim(), name: formName.value.trim(),
        version: formVersion.value, description: formDesc.value || null,
        author: formAuthor.value || null,
      }),
    });
    toast.addToast("Plugin installed", "success");
    installOpen.value = false;
    formKey.value = ""; formName.value = ""; formDesc.value = ""; formAuthor.value = "";
    await loadPlugins();
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : "Install failed", "error");
  } finally { installing.value = false; }
}

async function togglePlugin(p: PluginItem) {
  try {
    await apiFetch(`/api/v1/plugins/${p.key}`, {
      method: "PATCH",
      body: JSON.stringify({ config: p.config || {}, enabled: !p.enabled }),
    });
    p.enabled = !p.enabled;
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : "Toggle failed", "error");
  }
}

async function executePlugin(p: PluginItem) {
  try {
    const res = await apiFetch<{ status: string; execution_count: number }>(`/api/v1/plugins/${p.key}/execute`, { method: "POST" });
    p.execution_count = res.execution_count;
    toast.addToast(`Plugin executed (${res.status})`, "success");
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : "Execute failed", "error");
  }
}

async function uninstallPlugin(key: string) {
  if (!confirm(`Uninstall plugin "${key}"?`)) return;
  try {
    await apiFetch(`/api/v1/plugins/${key}`, { method: "DELETE" });
    toast.addToast("Plugin uninstalled", "success");
    await loadPlugins();
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : "Uninstall failed", "error");
  }
}

onMounted(loadPlugins);
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-xl font-semibold text-[var(--text-primary)]">Plugins</h1>
        <p class="text-xs text-[var(--text-muted)] mt-0.5">
          Extend HUBEX with custom integrations, automation hooks, and data processing.
          <router-link to="/admin" class="text-[var(--primary)] hover:underline ml-1">Admin Console</router-link>
        </p>
      </div>
      <button class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black hover:bg-[var(--primary-hover)]" @click="installOpen = true">
        + Install Plugin
      </button>
    </div>

    <div v-if="loading" class="text-xs text-[var(--text-muted)]">Loading...</div>

    <div v-else-if="error" class="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-400">
      <p>{{ error }}</p>
      <button class="mt-2 px-2.5 py-1 rounded text-xs font-medium border border-red-500/30 hover:bg-red-500/10" @click="loadPlugins">Retry</button>
    </div>

    <UEmpty v-else-if="!plugins.length"
      title="No plugins installed"
      description="Plugins add custom logic, integrations, and automation hooks to your HUBEX installation."
      icon="M14.25 6.087c0-.355.186-.676.401-.959.221-.29.349-.634.349-1.003 0-1.036-1.007-1.875-2.25-1.875s-2.25.84-2.25 1.875c0 .369.128.713.349 1.003.215.283.401.604.401.959v0a.64.64 0 01-.657.643 48.39 48.39 0 01-4.163-.3c.186 1.613.293 3.25.315 4.907a.656.656 0 01-.658.663v0c-.355 0-.676-.186-.959-.401a1.647 1.647 0 00-1.003-.349c-1.036 0-1.875 1.007-1.875 2.25s.84 2.25 1.875 2.25c.369 0 .713-.128 1.003-.349.283-.215.604-.401.959-.401v0c.31 0 .555.26.532.57a48.039 48.039 0 01-.642 5.056c1.518.19 3.058.309 4.616.354a.64.64 0 00.657-.643v0c0-.355-.186-.676-.401-.959a1.647 1.647 0 01-.349-1.003c0-1.035 1.008-1.875 2.25-1.875 1.243 0 2.25.84 2.25 1.875 0 .369-.128.713-.349 1.003-.215.283-.4.604-.4.959v0c0 .333.277.599.61.58a48.1 48.1 0 005.427-.63 48.05 48.05 0 00.582-4.717.532.532 0 00-.533-.57v0c-.355 0-.676.186-.959.401-.29.221-.634.349-1.003.349-1.035 0-1.875-1.007-1.875-2.25s.84-2.25 1.875-2.25c.37 0 .713.128 1.003.349.283.215.604.401.96.401v0a.656.656 0 00.658-.663 48.422 48.422 0 00-.37-5.36c-1.886.342-3.81.574-5.766.689a.578.578 0 01-.61-.58v0z"
    >
      <button class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black" @click="installOpen = true">Install Plugin</button>
    </UEmpty>

    <div v-else class="space-y-3">
      <div v-for="p in plugins" :key="p.key" class="border border-[var(--border)] rounded-xl bg-[var(--bg-surface)] px-5 py-4">
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-sm font-medium text-[var(--text-primary)]">{{ p.name }}</span>
              <span class="text-[10px] font-mono text-[var(--text-muted)]">{{ p.key }}</span>
              <UBadge :status="p.enabled ? 'ok' : 'neutral'" size="sm">{{ p.enabled ? 'active' : 'disabled' }}</UBadge>
              <span class="text-[10px] text-[var(--text-muted)]">v{{ p.version }}</span>
            </div>
            <p v-if="p.description" class="text-[10px] text-[var(--text-muted)]">{{ p.description }}</p>
            <div class="flex items-center gap-3 mt-2 text-[10px] text-[var(--text-muted)]">
              <span v-if="p.author">by {{ p.author }}</span>
              <span>{{ p.execution_count }} executions</span>
              <span v-if="p.error_count" class="text-red-400">{{ p.error_count }} errors</span>
              <span class="font-mono">sandbox: {{ p.sandbox_mode }}</span>
            </div>
            <div v-if="p.required_caps.length" class="flex flex-wrap gap-1 mt-1.5">
              <span v-for="cap in p.required_caps.slice(0, 5)" :key="cap" class="text-[9px] px-1 py-0.5 rounded bg-[var(--bg-raised)] border border-[var(--border)] font-mono text-[var(--text-muted)]">{{ cap }}</span>
            </div>
          </div>
          <div class="flex items-center gap-1.5 shrink-0">
            <button v-if="p.enabled" class="px-2 py-1 rounded-lg text-xs font-medium text-[var(--primary)] hover:bg-[var(--primary)]/10" @click="executePlugin(p)">Run</button>
            <button :class="['relative w-9 h-5 rounded-full transition-colors', p.enabled ? 'bg-[var(--status-ok)]' : 'bg-[var(--bg-overlay)]']" @click="togglePlugin(p)">
              <span :class="['absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform', p.enabled ? 'translate-x-4' : 'translate-x-0.5']" />
            </button>
            <button class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-red-400 hover:bg-red-500/10" @click="uninstallPlugin(p.key)">
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79" /></svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Install Modal -->
    <UModal :open="installOpen" title="Install Plugin" @close="installOpen = false">
      <div class="space-y-3">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-[10px] font-medium text-[var(--text-muted)]">Plugin Key *</label>
            <input v-model="formKey" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs font-mono" placeholder="my-plugin" />
          </div>
          <div>
            <label class="text-[10px] font-medium text-[var(--text-muted)]">Name *</label>
            <input v-model="formName" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs" placeholder="My Plugin" />
          </div>
        </div>
        <div>
          <label class="text-[10px] font-medium text-[var(--text-muted)]">Description</label>
          <input v-model="formDesc" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-[10px] font-medium text-[var(--text-muted)]">Version</label>
            <input v-model="formVersion" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs font-mono" />
          </div>
          <div>
            <label class="text-[10px] font-medium text-[var(--text-muted)]">Author</label>
            <input v-model="formAuthor" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs" />
          </div>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <button class="px-3 py-2 rounded-lg text-xs text-[var(--text-muted)]" @click="installOpen = false">Cancel</button>
          <button :disabled="installing || !formKey.trim() || !formName.trim()" class="px-3 py-2 rounded-lg text-xs font-medium bg-[var(--primary)] text-black disabled:opacity-50" @click="handleInstall">
            {{ installing ? 'Installing...' : 'Install' }}
          </button>
        </div>
      </template>
    </UModal>
  </div>
</template>
