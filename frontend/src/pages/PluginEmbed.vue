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

interface EmbedManifest {
  iframe_url?: string;
  /**
   * Sprint 3.3 — relative path served by the hubex frontend nginx which
   * reverse-proxies to the plugin container and strips X-Frame-Options.
   * When present, this is the canonical iframe src.
   */
  proxy_path?: string;
  /** Explicit opt-out for plugins that cannot be iframed at all. */
  allow_iframe?: boolean;
  /** Canonical URL to open in a new tab when iframing isn't possible. */
  open_url?: string;
}

function embedOf(p: InstalledPlugin | null): EmbedManifest | null {
  if (!p) return null;
  const manifest = p.manifest as Record<string, unknown>;
  return (manifest.embed as EmbedManifest) ?? null;
}

/**
 * Rewrite 'localhost' / '127.0.0.1' in an absolute URL to whatever hostname
 * the user is currently browsing from, so the URL works over LAN/remote
 * access not just on the docker host itself. Other hostnames pass through.
 */
function resolveHostname(raw: string): string {
  try {
    const u = new URL(raw);
    if (u.hostname === "localhost" || u.hostname === "127.0.0.1") {
      u.hostname = window.location.hostname;
    }
    return u.toString();
  } catch {
    return raw;
  }
}

/**
 * Resolve the best iframe source for this plugin:
 *   1. If manifest has proxy_path → use that (same-origin, X-Frame headers stripped)
 *   2. Otherwise, if allow_iframe is explicitly false → null (no iframe)
 *   3. Otherwise, use iframe_url with hostname rewrite
 */
const iframeSrc = computed<string | null>(() => {
  const embed = embedOf(plugin.value);
  if (!embed) return null;
  if (embed.proxy_path) {
    // Relative to current origin — browser resolves to http(s)://<current host>/plugins-embed/...
    return embed.proxy_path;
  }
  if (embed.allow_iframe === false) return null;
  if (!embed.iframe_url) return null;
  return resolveHostname(embed.iframe_url);
});

/** Canonical external URL for the "Open in new tab" button. */
const externalUrl = computed<string | null>(() => {
  const embed = embedOf(plugin.value);
  if (!embed) return null;
  const raw = embed.open_url || embed.iframe_url;
  return raw ? resolveHostname(raw) : null;
});

/**
 * True when we should not even try to render an iframe and should show
 * the "Open in new tab" placeholder instead. That's either because the
 * manifest explicitly forbids iframing, or because there's no usable src
 * but there IS an external URL to open.
 */
const iframeBlocked = computed(() => {
  const embed = embedOf(plugin.value);
  if (!embed) return false;
  return embed.allow_iframe === false;
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

function openInNewTab(): void {
  if (externalUrl.value) {
    window.open(externalUrl.value, "_blank", "noopener");
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
        <button
          v-if="externalUrl"
          class="text-[11px] text-[var(--text-muted)] hover:text-[var(--primary)] flex items-center gap-1"
          @click="openInNewTab"
        >
          {{ t("plugins.embed.open_new_tab") }}
          <svg class="h-3 w-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M14 3h7v7m0-7L10 14m-5-5v10a2 2 0 002 2h10" />
          </svg>
        </button>
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

      <!-- Iframe explicitly disabled (allow_iframe=false) → friendly fallback -->
      <div
        v-else-if="iframeBlocked"
        class="h-full flex items-center justify-center px-6"
      >
        <div class="max-w-lg text-center space-y-4">
          <div class="mx-auto h-14 w-14 rounded-full bg-[var(--primary)]/15 flex items-center justify-center">
            <svg class="h-7 w-7 text-[var(--primary)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
            </svg>
          </div>
          <h2 class="text-base font-semibold text-[var(--text-primary)]">
            {{ t("plugins.embed.not_embeddable_title", { name: plugin?.name || pluginKey }) }}
          </h2>
          <p class="text-xs text-[var(--text-muted)] leading-relaxed">
            {{ t("plugins.embed.not_embeddable_body") }}
          </p>
          <div class="flex justify-center gap-2 pt-2">
            <button
              class="px-4 py-2 rounded-lg text-xs font-medium bg-[var(--primary)] text-black hover:bg-[var(--primary-hover)] flex items-center gap-2"
              @click="openInNewTab"
            >
              {{ t("plugins.embed.open_in_new_tab_button") }}
              <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M14 3h7v7m0-7L10 14m-5-5v10a2 2 0 002 2h10" />
              </svg>
            </button>
            <button
              class="px-4 py-2 rounded-lg text-xs font-medium border border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              @click="goBack"
            >
              {{ t("plugins.embed.back_to_list") }}
            </button>
          </div>
        </div>
      </div>

      <!-- No iframe src at all (malformed manifest) -->
      <div
        v-else-if="!iframeSrc"
        class="h-full flex items-center justify-center text-xs text-[var(--text-muted)]"
      >
        {{ t("plugins.embed.no_iframe") }}
      </div>

      <!-- Happy path: iframe -->
      <iframe
        v-else
        :src="iframeSrc"
        class="w-full h-full border-0"
        :title="plugin?.name || pluginKey"
      />
    </div>
  </div>
</template>
