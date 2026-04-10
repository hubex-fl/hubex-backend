/**
 * Plugins store — catalog browsing + installed plugin lifecycle.
 *
 * Sprint 3 surface area:
 *  - GET  /api/v1/plugins/catalog                     → marketplace cards
 *  - GET  /api/v1/plugins                             → installed list
 *  - POST /api/v1/plugins/install-from-catalog/{key}  → install (connector or service)
 *  - DELETE /api/v1/plugins/{key}                     → uninstall
 *  - PUT  /api/v1/plugins/{key}/credentials           → set connector creds
 *  - POST /api/v1/plugins/{key}/start                 → service lifecycle
 *  - POST /api/v1/plugins/{key}/stop
 *  - GET  /api/v1/plugins/{key}/status                → drift-correct + configured-check
 *
 * The service-kind marketplace cards require the ``orchestrator`` feature
 * flag to be enabled. The store does NOT hide them when disabled; the view
 * renders them greyed out so users know the feature exists.
 */
import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { apiFetch, hasToken } from "../lib/api";

export type PluginKind = "service" | "connector";

export interface CredentialSchemaField {
  key: string;
  label: string;
  type: "string" | "select";
  secret?: boolean;
  required?: boolean;
  options?: string[];
  default?: string;
  placeholder?: string;
  help?: string;
}

export interface CatalogEntry {
  key: string;
  name: string;
  description: string;
  kind: PluginKind;
  category: string;
  manifest: {
    kind: PluginKind;
    category?: string;
    credential_schema?: CredentialSchemaField[];
    docker?: Record<string, unknown>;
    embed?: { iframe_url?: string; sidebar_label?: string };
    [k: string]: unknown;
  };
  icon_url: string | null;
  docs_url: string | null;
  adopt_container_name: string | null;
  tags: string[];
}

export interface InstalledPlugin {
  id: number;
  key: string;
  name: string;
  version: string;
  description: string | null;
  author: string | null;
  manifest: Record<string, unknown>;
  required_caps: string[];
  sandbox_mode: string;
  enabled: boolean;
  execution_count: number;
  error_count: number;
  last_executed_at: string | null;
  installed_at: string;
  config: Record<string, unknown> | null;
  kind: PluginKind;
  runtime_status: string | null;
  container_name: string | null;
}

export interface ConnectorStatus {
  kind: "connector";
  key: string;
  configured: boolean;
  set_fields: string[];
}

export interface ServiceStatus {
  kind: "service";
  key: string;
  runtime_status: string;
  container_name: string;
  container: Record<string, unknown> | null;
}

export type PluginStatus = ConnectorStatus | ServiceStatus;

export const usePluginsStore = defineStore("plugins", () => {
  const catalog = ref<CatalogEntry[]>([]);
  const installed = ref<InstalledPlugin[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const busyKeys = ref<Set<string>>(new Set());

  const installedMap = computed(() => {
    const m: Record<string, InstalledPlugin> = {};
    for (const p of installed.value) m[p.key] = p;
    return m;
  });

  const catalogByKind = computed(() => ({
    service: catalog.value.filter((e) => e.kind === "service"),
    connector: catalog.value.filter((e) => e.kind === "connector"),
  }));

  const installedByKind = computed(() => ({
    service: installed.value.filter((p) => p.kind === "service"),
    connector: installed.value.filter((p) => p.kind === "connector"),
  }));

  function isInstalled(key: string): boolean {
    return installedMap.value[key] != null;
  }

  function isBusy(key: string): boolean {
    return busyKeys.value.has(key);
  }

  async function load(force = false): Promise<void> {
    if (loading.value) return;
    if (!hasToken()) return;
    if (catalog.value.length > 0 && installed.value.length >= 0 && !force) {
      // still refresh installed (catalog is static)
    }
    loading.value = true;
    error.value = null;
    try {
      const [cat, inst] = await Promise.all([
        apiFetch<CatalogEntry[]>("/api/v1/plugins/catalog"),
        apiFetch<InstalledPlugin[]>("/api/v1/plugins"),
      ]);
      catalog.value = cat;
      installed.value = inst;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to load plugins";
    } finally {
      loading.value = false;
    }
  }

  async function installFromCatalog(key: string): Promise<InstalledPlugin> {
    busyKeys.value.add(key);
    try {
      const plugin = await apiFetch<InstalledPlugin>(
        `/api/v1/plugins/install-from-catalog/${encodeURIComponent(key)}`,
        { method: "POST" }
      );
      installed.value.push(plugin);
      return plugin;
    } finally {
      busyKeys.value.delete(key);
    }
  }

  async function uninstall(key: string): Promise<void> {
    busyKeys.value.add(key);
    try {
      await apiFetch(`/api/v1/plugins/${encodeURIComponent(key)}`, {
        method: "DELETE",
      });
      installed.value = installed.value.filter((p) => p.key !== key);
    } finally {
      busyKeys.value.delete(key);
    }
  }

  async function start(key: string): Promise<InstalledPlugin> {
    busyKeys.value.add(key);
    try {
      const updated = await apiFetch<InstalledPlugin>(
        `/api/v1/plugins/${encodeURIComponent(key)}/start`,
        { method: "POST" }
      );
      replaceInstalled(updated);
      return updated;
    } finally {
      busyKeys.value.delete(key);
    }
  }

  async function stop(key: string): Promise<InstalledPlugin> {
    busyKeys.value.add(key);
    try {
      const updated = await apiFetch<InstalledPlugin>(
        `/api/v1/plugins/${encodeURIComponent(key)}/stop`,
        { method: "POST" }
      );
      replaceInstalled(updated);
      return updated;
    } finally {
      busyKeys.value.delete(key);
    }
  }

  async function setCredentials(
    key: string,
    credentials: Record<string, string>
  ): Promise<{ ok: boolean; updated_fields: string[] }> {
    busyKeys.value.add(key);
    try {
      return await apiFetch<{ ok: boolean; updated_fields: string[] }>(
        `/api/v1/plugins/${encodeURIComponent(key)}/credentials`,
        {
          method: "PUT",
          body: JSON.stringify({ credentials }),
        }
      );
    } finally {
      busyKeys.value.delete(key);
    }
  }

  async function fetchStatus(key: string): Promise<PluginStatus> {
    const s = await apiFetch<PluginStatus>(
      `/api/v1/plugins/${encodeURIComponent(key)}/status`
    );
    // For service plugins the backend corrects runtime_status drift — mirror it here.
    if (s.kind === "service") {
      const existing = installedMap.value[key];
      if (existing && existing.runtime_status !== s.runtime_status) {
        existing.runtime_status = s.runtime_status;
      }
    }
    return s;
  }

  function replaceInstalled(updated: InstalledPlugin): void {
    const idx = installed.value.findIndex((p) => p.key === updated.key);
    if (idx >= 0) installed.value[idx] = updated;
    else installed.value.push(updated);
  }

  function reset(): void {
    catalog.value = [];
    installed.value = [];
    loading.value = false;
    error.value = null;
    busyKeys.value.clear();
  }

  return {
    catalog,
    installed,
    loading,
    error,
    installedMap,
    catalogByKind,
    installedByKind,
    isInstalled,
    isBusy,
    load,
    installFromCatalog,
    uninstall,
    start,
    stop,
    setCredentials,
    fetchStatus,
    reset,
  };
});
