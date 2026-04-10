<script setup lang="ts">
import { ref, computed, onMounted, reactive } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";

import UModal from "../components/ui/UModal.vue";
import UBadge from "../components/ui/UBadge.vue";
import UEmpty from "../components/ui/UEmpty.vue";

import { useToastStore } from "../stores/toast";
import { useFeaturesStore } from "../stores/features";
import {
  usePluginsStore,
  type CatalogEntry,
  type CredentialSchemaField,
  type InstalledPlugin,
} from "../stores/plugins";

const { t } = useI18n();
const toast = useToastStore();
const router = useRouter();
const store = usePluginsStore();
const features = useFeaturesStore();

// ── state ──────────────────────────────────────────────────────────────────

const configureOpen = ref(false);
const configureEntry = ref<CatalogEntry | null>(null);
const configurePlugin = ref<InstalledPlugin | null>(null);
const configureValues = reactive<Record<string, string>>({});
const configureSaving = ref(false);

const confirmUninstallKey = ref<string | null>(null);

// ── derived ────────────────────────────────────────────────────────────────

const orchestratorEnabled = computed(() => features.isEnabled("orchestrator"));

const marketplaceEntries = computed(() => {
  return store.catalog.slice().sort((a, b) => {
    // Service plugins first (highlight orchestrator), then connectors
    if (a.kind !== b.kind) return a.kind === "service" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
});

const installedList = computed(() =>
  store.installed.slice().sort((a, b) => a.name.localeCompare(b.name))
);

// ── lifecycle ──────────────────────────────────────────────────────────────

onMounted(async () => {
  await features.load();
  await store.load();
});

// ── actions ────────────────────────────────────────────────────────────────

async function handleInstall(entry: CatalogEntry): Promise<void> {
  if (entry.kind === "service" && !orchestratorEnabled.value) {
    toast.addToast(t("plugins.orchestrator_hint_short"), "error");
    return;
  }
  if (store.isInstalled(entry.key)) return;
  try {
    const plugin = await store.installFromCatalog(entry.key);
    toast.addToast(
      t("plugins.installed_toast", { name: entry.name }),
      "success"
    );
    // Connectors land with no credentials — open the configure modal immediately.
    if (entry.kind === "connector") {
      openConfigure(entry, plugin);
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Install failed";
    toast.addToast(msg, "error");
  }
}

async function handleStart(plugin: InstalledPlugin): Promise<void> {
  try {
    await store.start(plugin.key);
    toast.addToast(t("plugins.started_toast", { name: plugin.name }), "success");
  } catch (err) {
    toast.addToast(err instanceof Error ? err.message : "Start failed", "error");
  }
}

async function handleStop(plugin: InstalledPlugin): Promise<void> {
  try {
    await store.stop(plugin.key);
    toast.addToast(t("plugins.stopped_toast", { name: plugin.name }), "success");
  } catch (err) {
    toast.addToast(err instanceof Error ? err.message : "Stop failed", "error");
  }
}

function handleOpenEmbed(plugin: InstalledPlugin): void {
  router.push(`/plugins/${encodeURIComponent(plugin.key)}/embed`);
}

function askUninstall(key: string): void {
  confirmUninstallKey.value = key;
}

async function confirmUninstall(): Promise<void> {
  const key = confirmUninstallKey.value;
  if (!key) return;
  try {
    await store.uninstall(key);
    toast.addToast(t("plugins.uninstalled_toast"), "success");
  } catch (err) {
    toast.addToast(err instanceof Error ? err.message : "Uninstall failed", "error");
  } finally {
    confirmUninstallKey.value = null;
  }
}

// ── configure modal (connector credentials) ───────────────────────────────

function openConfigure(entry: CatalogEntry | null, plugin: InstalledPlugin): void {
  // Entry is optional (for plugins already installed, we derive the schema
  // from plugin.manifest instead of the catalog).
  configureEntry.value = entry;
  configurePlugin.value = plugin;
  for (const k of Object.keys(configureValues)) delete configureValues[k];
  const schema = credentialSchemaForPlugin(plugin);
  for (const f of schema) {
    configureValues[f.key] = (f.default as string | undefined) ?? "";
  }
  configureOpen.value = true;
}

function openConfigureFromInstalled(plugin: InstalledPlugin): void {
  const entry =
    store.catalog.find((e) => e.key === plugin.key) ?? null;
  openConfigure(entry, plugin);
}

function credentialSchemaForPlugin(plugin: InstalledPlugin): CredentialSchemaField[] {
  const manifest = plugin.manifest as Record<string, unknown>;
  const schema = manifest.credential_schema;
  return Array.isArray(schema) ? (schema as CredentialSchemaField[]) : [];
}

async function saveCredentials(): Promise<void> {
  if (!configurePlugin.value) return;
  const plugin = configurePlugin.value;
  configureSaving.value = true;
  try {
    // Strip empty values so users can skip optional fields
    const creds: Record<string, string> = {};
    for (const [k, v] of Object.entries(configureValues)) {
      if (v && v.trim() !== "") creds[k] = v;
    }
    if (Object.keys(creds).length === 0) {
      toast.addToast(t("plugins.no_fields_to_save"), "error");
      return;
    }
    await store.setCredentials(plugin.key, creds);
    toast.addToast(t("plugins.credentials_saved"), "success");
    configureOpen.value = false;
  } catch (err) {
    toast.addToast(err instanceof Error ? err.message : "Save failed", "error");
  } finally {
    configureSaving.value = false;
  }
}

// ── helpers ────────────────────────────────────────────────────────────────

function statusDotClass(status: string | null): string {
  switch (status) {
    case "running":
      return "bg-[var(--status-ok)]";
    case "stopped":
      return "bg-[var(--text-muted)]";
    case "unhealthy":
    case "error":
      return "bg-[var(--status-warn)]";
    case "installing":
      return "bg-[var(--primary)] animate-pulse";
    default:
      return "bg-[var(--text-muted)]/40";
  }
}

function iframeUrlFor(plugin: InstalledPlugin): string | null {
  const manifest = plugin.manifest as Record<string, unknown>;
  const embed = manifest.embed as { iframe_url?: string } | undefined;
  return embed?.iframe_url ?? null;
}
</script>

<template>
  <div class="space-y-8">
    <!-- Header -->
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-xl font-semibold text-[var(--text-primary)]">
          {{ t("plugins.title") }}
        </h1>
        <p class="text-xs text-[var(--text-muted)] mt-0.5 max-w-2xl">
          {{ t("plugins.subtitle") }}
        </p>
      </div>
      <router-link
        to="/settings/features"
        class="text-xs text-[var(--primary)] hover:underline shrink-0"
      >
        {{ t("plugins.manage_features") }}
      </router-link>
    </div>

    <div v-if="store.loading" class="text-xs text-[var(--text-muted)]">
      {{ t("common.loading") }}
    </div>

    <div
      v-else-if="store.error"
      class="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-400"
    >
      <p>{{ store.error }}</p>
      <button
        class="mt-2 px-2.5 py-1 rounded text-xs font-medium border border-red-500/30 hover:bg-red-500/10"
        @click="store.load(true)"
      >
        {{ t("common.retry") }}
      </button>
    </div>

    <div v-else class="grid gap-8 lg:grid-cols-2">
      <!-- ─── Marketplace column ───────────────────────────────────────── -->
      <section class="space-y-3">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold text-[var(--text-primary)]">
            {{ t("plugins.marketplace") }}
          </h2>
          <span class="text-[10px] text-[var(--text-muted)]">
            {{ marketplaceEntries.length }} {{ t("plugins.available") }}
          </span>
        </div>

        <div
          v-if="!orchestratorEnabled && marketplaceEntries.some((e) => e.kind === 'service')"
          class="rounded-lg border border-[var(--border)] bg-[var(--bg-raised)] px-3 py-2 text-[10px] text-[var(--text-muted)]"
        >
          {{ t("plugins.orchestrator_hint") }}
        </div>

        <div class="space-y-3">
          <article
            v-for="entry in marketplaceEntries"
            :key="entry.key"
            :class="[
              'border border-[var(--border)] rounded-xl bg-[var(--bg-surface)] px-4 py-3 transition-opacity',
              entry.kind === 'service' && !orchestratorEnabled ? 'opacity-50' : '',
            ]"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                  <span class="text-sm font-medium text-[var(--text-primary)]">
                    {{ entry.name }}
                  </span>
                  <UBadge :status="entry.kind === 'service' ? 'warn' : 'info'" size="sm">
                    {{ t(`plugins.kind.${entry.kind}`) }}
                  </UBadge>
                  <span
                    v-if="store.isInstalled(entry.key)"
                    class="text-[10px] text-[var(--status-ok)]"
                  >
                    ● {{ t("plugins.installed_badge") }}
                  </span>
                </div>
                <p class="text-[10px] text-[var(--text-muted)] leading-relaxed">
                  {{ entry.description }}
                </p>
                <div v-if="entry.tags.length" class="mt-1.5 flex flex-wrap gap-1">
                  <span
                    v-for="tag in entry.tags"
                    :key="tag"
                    class="px-1.5 py-0.5 rounded bg-[var(--bg-raised)] text-[9px] text-[var(--text-muted)] font-mono"
                  >
                    {{ tag }}
                  </span>
                </div>
              </div>
              <div class="shrink-0">
                <button
                  v-if="!store.isInstalled(entry.key)"
                  :disabled="
                    store.isBusy(entry.key) ||
                    (entry.kind === 'service' && !orchestratorEnabled)
                  "
                  class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black hover:bg-[var(--primary-hover)] disabled:opacity-40 disabled:cursor-not-allowed"
                  :title="
                    entry.kind === 'service' && !orchestratorEnabled
                      ? t('plugins.orchestrator_hint_short')
                      : ''
                  "
                  @click="handleInstall(entry)"
                >
                  {{ store.isBusy(entry.key) ? t("plugins.installing") : t("plugins.install") }}
                </button>
                <a
                  v-else-if="entry.docs_url"
                  :href="entry.docs_url"
                  target="_blank"
                  rel="noopener"
                  class="text-[10px] text-[var(--text-muted)] hover:text-[var(--primary)]"
                >
                  {{ t("plugins.docs") }} ↗
                </a>
              </div>
            </div>
          </article>
        </div>
      </section>

      <!-- ─── Installed column ─────────────────────────────────────────── -->
      <section class="space-y-3">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold text-[var(--text-primary)]">
            {{ t("plugins.installed") }}
          </h2>
          <span class="text-[10px] text-[var(--text-muted)]">
            {{ installedList.length }}
          </span>
        </div>

        <UEmpty
          v-if="!installedList.length"
          :title="t('plugins.empty_title')"
          :description="t('plugins.empty_description')"
          icon="M14.25 6.087c0-.355.186-.676.401-.959.221-.29.349-.634.349-1.003 0-1.036-1.007-1.875-2.25-1.875s-2.25.84-2.25 1.875c0 .369.128.713.349 1.003.215.283.401.604.401.959v0a.64.64 0 01-.657.643 48.39 48.39 0 01-4.163-.3c.186 1.613.293 3.25.315 4.907a.656.656 0 01-.658.663v0c-.355 0-.676-.186-.959-.401a1.647 1.647 0 00-1.003-.349c-1.036 0-1.875 1.007-1.875 2.25s.84 2.25 1.875 2.25c.369 0 .713-.128 1.003-.349.283-.215.604-.401.959-.401v0c.31 0 .555.26.532.57a48.039 48.039 0 01-.642 5.056c1.518.19 3.058.309 4.616.354a.64.64 0 00.657-.643v0c0-.355-.186-.676-.401-.959a1.647 1.647 0 01-.349-1.003c0-1.035 1.008-1.875 2.25-1.875 1.243 0 2.25.84 2.25 1.875 0 .369-.128.713-.349 1.003-.215.283-.4.604-.4.959v0c0 .333.277.599.61.58a48.1 48.1 0 005.427-.63 48.05 48.05 0 00.582-4.717.532.532 0 00-.533-.57v0c-.355 0-.676.186-.959.401-.29.221-.634.349-1.003.349-1.035 0-1.875-1.007-1.875-2.25s.84-2.25 1.875-2.25c.37 0 .713.128 1.003.349.283.215.604.401.96.401v0a.656.656 0 00.658-.663 48.422 48.422 0 00-.37-5.36c-1.886.342-3.81.574-5.766.689a.578.578 0 01-.61-.58v0z"
        />

        <div v-else class="space-y-3">
          <article
            v-for="plugin in installedList"
            :key="plugin.key"
            class="border border-[var(--border)] rounded-xl bg-[var(--bg-surface)] px-4 py-3"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-0.5">
                  <span class="text-sm font-medium text-[var(--text-primary)]">
                    {{ plugin.name }}
                  </span>
                  <UBadge :status="plugin.kind === 'service' ? 'warn' : 'info'" size="sm">
                    {{ t(`plugins.kind.${plugin.kind}`) }}
                  </UBadge>
                  <!-- Service status dot -->
                  <span
                    v-if="plugin.kind === 'service'"
                    class="flex items-center gap-1 text-[10px] text-[var(--text-muted)]"
                  >
                    <span :class="['h-1.5 w-1.5 rounded-full', statusDotClass(plugin.runtime_status)]" />
                    {{ plugin.runtime_status || "unknown" }}
                  </span>
                </div>
                <p
                  v-if="plugin.description"
                  class="text-[10px] text-[var(--text-muted)] leading-relaxed"
                >
                  {{ plugin.description }}
                </p>
                <div
                  v-if="plugin.kind === 'service' && plugin.container_name"
                  class="mt-1 text-[10px] text-[var(--text-muted)] font-mono"
                >
                  {{ plugin.container_name }}
                </div>
              </div>
              <div class="flex items-center gap-1.5 shrink-0">
                <!-- Service actions -->
                <template v-if="plugin.kind === 'service'">
                  <button
                    v-if="iframeUrlFor(plugin) && plugin.runtime_status === 'running'"
                    class="px-2 py-1 rounded-lg text-[10px] font-medium text-[var(--primary)] hover:bg-[var(--primary)]/10"
                    @click="handleOpenEmbed(plugin)"
                  >
                    {{ t("plugins.open") }}
                  </button>
                  <button
                    v-if="plugin.runtime_status === 'running'"
                    :disabled="store.isBusy(plugin.key)"
                    class="px-2 py-1 rounded-lg text-[10px] font-medium text-[var(--text-muted)] hover:text-[var(--text-primary)] disabled:opacity-40"
                    @click="handleStop(plugin)"
                  >
                    {{ t("plugins.stop") }}
                  </button>
                  <button
                    v-else
                    :disabled="store.isBusy(plugin.key)"
                    class="px-2 py-1 rounded-lg text-[10px] font-medium text-[var(--status-ok)] hover:bg-[var(--status-ok)]/10 disabled:opacity-40"
                    @click="handleStart(plugin)"
                  >
                    {{ t("plugins.start") }}
                  </button>
                </template>
                <!-- Connector actions -->
                <template v-else>
                  <button
                    class="px-2 py-1 rounded-lg text-[10px] font-medium text-[var(--primary)] hover:bg-[var(--primary)]/10"
                    @click="openConfigureFromInstalled(plugin)"
                  >
                    {{ t("plugins.configure") }}
                  </button>
                </template>
                <!-- Common: uninstall -->
                <button
                  :disabled="store.isBusy(plugin.key)"
                  class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-red-400 hover:bg-red-500/10 disabled:opacity-40"
                  :title="t('plugins.uninstall')"
                  @click="askUninstall(plugin.key)"
                >
                  <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79"
                    />
                  </svg>
                </button>
              </div>
            </div>
          </article>
        </div>
      </section>
    </div>

    <!-- ── Configure modal (connector credentials) ───────────────────── -->
    <UModal
      :open="configureOpen"
      :title="configurePlugin ? t('plugins.configure_title', { name: configurePlugin.name }) : ''"
      @close="configureOpen = false"
    >
      <div v-if="configurePlugin" class="space-y-3">
        <p class="text-[10px] text-[var(--text-muted)]">
          {{ t("plugins.credentials_hint") }}
        </p>
        <div
          v-for="field in credentialSchemaForPlugin(configurePlugin)"
          :key="field.key"
          class="space-y-1"
        >
          <label class="text-[10px] font-medium text-[var(--text-muted)] flex items-center gap-1">
            {{ field.label }}
            <span v-if="field.required" class="text-red-400">*</span>
          </label>
          <select
            v-if="field.type === 'select'"
            v-model="configureValues[field.key]"
            class="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs"
          >
            <option
              v-for="opt in field.options || []"
              :key="opt"
              :value="opt"
            >
              {{ opt }}
            </option>
          </select>
          <input
            v-else
            v-model="configureValues[field.key]"
            :type="field.secret ? 'password' : 'text'"
            :placeholder="field.placeholder || ''"
            class="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs"
            :class="field.secret ? 'font-mono' : ''"
          />
          <p v-if="field.help" class="text-[9px] text-[var(--text-muted)]">
            {{ field.help }}
          </p>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <button
            class="px-3 py-2 rounded-lg text-xs text-[var(--text-muted)]"
            @click="configureOpen = false"
          >
            {{ t("common.cancel") }}
          </button>
          <button
            :disabled="configureSaving"
            class="px-3 py-2 rounded-lg text-xs font-medium bg-[var(--primary)] text-black disabled:opacity-50"
            @click="saveCredentials"
          >
            {{ configureSaving ? t("plugins.saving") : t("plugins.save_credentials") }}
          </button>
        </div>
      </template>
    </UModal>

    <!-- ── Uninstall confirmation modal ─────────────────────────────── -->
    <UModal
      :open="confirmUninstallKey !== null"
      :title="t('plugins.confirm_uninstall_title')"
      @close="confirmUninstallKey = null"
    >
      <p class="text-xs text-[var(--text-muted)]">
        {{ t("plugins.confirm_uninstall_body", { key: confirmUninstallKey }) }}
      </p>
      <template #footer>
        <div class="flex justify-end gap-2">
          <button
            class="px-3 py-2 rounded-lg text-xs text-[var(--text-muted)]"
            @click="confirmUninstallKey = null"
          >
            {{ t("common.cancel") }}
          </button>
          <button
            class="px-3 py-2 rounded-lg text-xs font-medium bg-red-500 text-white hover:bg-red-600"
            @click="confirmUninstall"
          >
            {{ t("plugins.uninstall") }}
          </button>
        </div>
      </template>
    </UModal>
  </div>
</template>
