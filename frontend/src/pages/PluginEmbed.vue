<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";

import { usePluginsStore, type InstalledPlugin } from "../stores/plugins";

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const store = usePluginsStore();

const pluginKey = computed(() => String(route.params.key || ""));
const plugin = ref<InstalledPlugin | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);

const iframeUrl = computed<string | null>(() => {
  if (!plugin.value) return null;
  const manifest = plugin.value.manifest as Record<string, unknown>;
  const embed = manifest.embed as { iframe_url?: string } | undefined;
  const raw = embed?.iframe_url;
  if (!raw) return null;
  // Rewrite hardcoded "localhost" to the hostname the user is actually
  // browsing from, so the iframe works when HubEx is accessed via IP
  // or a custom hostname (not just when running on the user's own machine).
  try {
    const u = new URL(raw);
    if (u.hostname === "localhost" || u.hostname === "127.0.0.1") {
      u.hostname = window.location.hostname;
    }
    return u.toString();
  } catch {
    return raw;
  }
});

const isRunning = computed(() => plugin.value?.runtime_status === "running");

onMounted(async () => {
  if (store.installed.length === 0) {
    await store.load();
  }
  plugin.value = store.installed.find((p) => p.key === pluginKey.value) || null;
  if (!plugin.value) {
    error.value = t("plugins.embed.not_found", { key: pluginKey.value });
  }
  loading.value = false;
});

async function handleStart(): Promise<void> {
  if (!plugin.value) return;
  try {
    const updated = await store.start(plugin.value.key);
    plugin.value = updated;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Start failed";
  }
}

function goBack(): void {
  router.push("/plugins");
}
</script>

<template>
  <div class="h-screen w-screen flex flex-col bg-[var(--bg-base)]">
    <!-- Top bar -->
    <header
      class="shrink-0 flex items-center justify-between px-4 py-2 border-b border-[var(--border)] bg-[var(--bg-surface)]"
    >
      <div class="flex items-center gap-3 min-w-0">
        <button
          class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)]"
          :title="t('common.back')"
          @click="goBack"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div class="min-w-0">
          <h1 class="text-sm font-semibold text-[var(--text-primary)] truncate">
            {{ plugin?.name || pluginKey }}
          </h1>
          <p
            v-if="plugin?.container_name"
            class="text-[10px] text-[var(--text-muted)] font-mono truncate"
          >
            {{ plugin.container_name }}
          </p>
        </div>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <span
          v-if="plugin?.runtime_status"
          class="flex items-center gap-1 text-[10px] text-[var(--text-muted)]"
        >
          <span
            :class="[
              'h-1.5 w-1.5 rounded-full',
              isRunning ? 'bg-[var(--status-ok)]' : 'bg-[var(--text-muted)]',
            ]"
          />
          {{ plugin.runtime_status }}
        </span>
        <a
          v-if="iframeUrl"
          :href="iframeUrl"
          target="_blank"
          rel="noopener"
          class="text-[10px] text-[var(--text-muted)] hover:text-[var(--primary)]"
        >
          {{ t("plugins.embed.open_new_tab") }} ↗
        </a>
      </div>
    </header>

    <!-- Body -->
    <div class="flex-1 min-h-0">
      <div
        v-if="loading"
        class="h-full flex items-center justify-center text-xs text-[var(--text-muted)]"
      >
        {{ t("common.loading") }}
      </div>
      <div
        v-else-if="error"
        class="h-full flex items-center justify-center"
      >
        <div class="max-w-md text-center space-y-3">
          <p class="text-xs text-red-400">{{ error }}</p>
          <button
            class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black"
            @click="goBack"
          >
            {{ t("plugins.embed.back_to_list") }}
          </button>
        </div>
      </div>
      <div
        v-else-if="!isRunning"
        class="h-full flex items-center justify-center"
      >
        <div class="max-w-md text-center space-y-3">
          <p class="text-xs text-[var(--text-muted)]">
            {{ t("plugins.embed.not_running") }}
          </p>
          <div class="flex justify-center gap-2">
            <button
              class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black"
              @click="handleStart"
            >
              {{ t("plugins.start") }}
            </button>
            <button
              class="px-3 py-1.5 rounded-lg text-xs font-medium border border-[var(--border)] text-[var(--text-muted)]"
              @click="goBack"
            >
              {{ t("plugins.embed.back_to_list") }}
            </button>
          </div>
        </div>
      </div>
      <div
        v-else-if="!iframeUrl"
        class="h-full flex items-center justify-center text-xs text-[var(--text-muted)]"
      >
        {{ t("plugins.embed.no_iframe") }}
      </div>
      <iframe
        v-else
        :src="iframeUrl"
        class="w-full h-full border-0"
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-downloads"
        :title="plugin?.name || pluginKey"
      />
    </div>
  </div>
</template>
