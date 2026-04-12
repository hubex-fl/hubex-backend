<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../lib/api";
import UInfoTooltip from "../components/ui/UInfoTooltip.vue";

const { t } = useI18n();

// ── Types ────────────────────────────────────────────────────────────────

interface McpStatus {
  enabled: boolean;
  active_connections: number;
  tools_count: number;
  protocol_version: string;
}

interface McpTool {
  name: string;
  description: string;
  inputSchema: Record<string, any>;
}

interface LogEntry {
  ts: string;
  tool: string;
  status: string;
  duration_ms: number;
  user_id?: number;
  error?: string;
}

interface ApiKeyOut {
  id: number;
  name: string;
  key_prefix: string;
  caps: string[];
  expires_at: string | null;
  last_used_at: string | null;
  revoked: boolean;
  created_at: string;
}

interface ApiKeyCreatedOut extends ApiKeyOut {
  key: string;
}

// ── State ────────────────────────────────────────────────────────────────

const loading = ref(true);
const status = ref<McpStatus | null>(null);
const tools = ref<McpTool[]>([]);
const logEntries = ref<LogEntry[]>([]);
const expandedTool = ref<string | null>(null);
const apiKeys = ref<ApiKeyOut[]>([]);

// Test tool modal
const testModalOpen = ref(false);
const testTool = ref<McpTool | null>(null);
const testParams = ref<string>("{}");
const testResult = ref<string | null>(null);
const testRunning = ref(false);

// Key generation
const generatingKey = ref(false);
const newKey = ref<string | null>(null);
const copiedKey = ref(false);
const copiedUrl = ref(false);
const copiedConfig = ref(false);

// Active tab
const activeTab = ref<"overview" | "tools" | "integration" | "log">("overview");

// ── Computed ─────────────────────────────────────────────────────────────

const connectionUrl = computed(() => {
  const host = window.location.origin;
  return `${host}/api/v1/mcp/sse`;
});

const claudeDesktopConfig = computed(() => {
  return JSON.stringify({
    mcpServers: {
      hubex: {
        url: connectionUrl.value,
        headers: { Authorization: "Bearer YOUR_API_KEY" },
      },
    },
  }, null, 2);
});

const pythonExample = computed(() => {
  return `import httpx
import json

MCP_URL = "${connectionUrl.value}"
API_KEY = "hbx_your_api_key_here"

# Connect to MCP SSE stream
with httpx.stream(
    "GET", MCP_URL,
    headers={"Authorization": f"Bearer {API_KEY}"},
    timeout=None,
) as response:
    for line in response.iter_lines():
        if line.startswith("event: endpoint"):
            continue
        if line.startswith("data:"):
            data = json.loads(line[5:])
            print("Received:", data)`;
});

const mcpApiKeys = computed(() =>
  apiKeys.value.filter(
    (k) => !k.revoked && k.caps.includes("mcp.read") && k.caps.includes("mcp.execute")
  )
);

// ── Actions ──────────────────────────────────────────────────────────────

async function fetchStatus() {
  try {
    status.value = await apiFetch<McpStatus>("/api/v1/mcp/status");
  } catch {
    status.value = null;
  }
}

async function fetchTools() {
  try {
    const res = await apiFetch<{ tools: McpTool[] }>("/api/v1/mcp/tools/list", {
      method: "POST",
    });
    tools.value = res.tools;
  } catch {
    tools.value = [];
  }
}

async function fetchLog() {
  try {
    const res = await apiFetch<{ entries: LogEntry[] }>("/api/v1/mcp/log?limit=50");
    logEntries.value = res.entries;
  } catch {
    logEntries.value = [];
  }
}

async function fetchApiKeys() {
  try {
    apiKeys.value = await apiFetch<ApiKeyOut[]>("/api/v1/api-keys");
  } catch {
    apiKeys.value = [];
  }
}

async function generateMcpKey() {
  generatingKey.value = true;
  try {
    const res = await apiFetch<ApiKeyCreatedOut>("/api/v1/api-keys", {
      method: "POST",
      body: JSON.stringify({
        name: `MCP Access Key (${new Date().toLocaleDateString()})`,
        caps: ["mcp.read", "mcp.execute"],
      }),
    });
    newKey.value = res.key;
    await fetchApiKeys();
  } catch {
    // error handled silently
  } finally {
    generatingKey.value = false;
  }
}

async function revokeKey(keyId: number) {
  try {
    await apiFetch(`/api/v1/api-keys/${keyId}`, { method: "DELETE" });
    await fetchApiKeys();
  } catch {
    // error handled silently
  }
}

function toggleTool(name: string) {
  expandedTool.value = expandedTool.value === name ? null : name;
}

function openTestModal(tool: McpTool) {
  testTool.value = tool;
  // Build default params from schema
  const props = tool.inputSchema?.properties || {};
  const defaults: Record<string, any> = {};
  for (const [key, schema] of Object.entries(props) as [string, any][]) {
    if (schema.default !== undefined) defaults[key] = schema.default;
    else if (schema.type === "string") defaults[key] = "";
    else if (schema.type === "integer") defaults[key] = 0;
    else if (schema.type === "boolean") defaults[key] = false;
  }
  testParams.value = JSON.stringify(defaults, null, 2);
  testResult.value = null;
  testModalOpen.value = true;
}

async function runTest() {
  if (!testTool.value) return;
  testRunning.value = true;
  testResult.value = null;
  try {
    const args = JSON.parse(testParams.value);
    const res = await apiFetch<{ content: { type: string; text: string }[] }>(
      "/api/v1/mcp/tools/call",
      {
        method: "POST",
        body: JSON.stringify({ name: testTool.value.name, arguments: args }),
      }
    );
    testResult.value = res.content?.[0]?.text ?? JSON.stringify(res);
  } catch (e: any) {
    testResult.value = `Error: ${e.message}`;
  } finally {
    testRunning.value = false;
  }
}

async function copyToClipboard(text: string, flag: "url" | "key" | "config") {
  await navigator.clipboard.writeText(text);
  if (flag === "url") { copiedUrl.value = true; setTimeout(() => (copiedUrl.value = false), 2000); }
  if (flag === "key") { copiedKey.value = true; setTimeout(() => (copiedKey.value = false), 2000); }
  if (flag === "config") { copiedConfig.value = true; setTimeout(() => (copiedConfig.value = false), 2000); }
}

function formatTs(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString();
}

// ── Demo Presenter ──────────────────────────────────────────────────────

const demoRunning = ref(false);
const demoSequence = ref<"teaser" | "short" | "full">("teaser");

async function runDemoPresenter() {
  demoRunning.value = true;
  try {
    await apiFetch("/api/v1/system/run-demo?sequence=" + demoSequence.value + "&speed=1.0", {
      method: "POST",
    });
  } catch {
    // handled silently
  } finally {
    // The demo runs in the background; mark button as available again after a short delay
    setTimeout(() => { demoRunning.value = false; }, 3000);
  }
}

onMounted(async () => {
  loading.value = true;
  await Promise.all([fetchStatus(), fetchTools(), fetchLog(), fetchApiKeys()]);
  loading.value = false;
});
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-6 space-y-6">

    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold text-[var(--text-primary)]">{{ t('mcp.title') }}</h1>
        <p class="text-sm text-[var(--text-muted)] mt-1">{{ t('mcp.subtitle') }}</p>
      </div>
      <div class="flex items-center gap-2">
        <span
          v-if="status"
          class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
          :class="status.enabled
            ? 'bg-emerald-500/10 text-emerald-400'
            : 'bg-red-500/10 text-red-400'"
        >
          <span class="w-1.5 h-1.5 rounded-full" :class="status.enabled ? 'bg-emerald-400' : 'bg-red-400'" />
          {{ status.enabled ? t('mcp.statusActive') : t('mcp.statusInactive') }}
        </span>
      </div>
    </div>

    <!-- Tab bar -->
    <div class="flex gap-1 border-b border-[var(--border)]">
      <button
        v-for="tab in (['overview', 'tools', 'integration', 'log'] as const)"
        :key="tab"
        class="px-4 py-2 text-sm font-medium border-b-2 transition-colors"
        :class="activeTab === tab
          ? 'border-[var(--primary)] text-[var(--primary)]'
          : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)]'"
        @click="activeTab = tab"
      >
        {{ t(`mcp.tab_${tab}`) }}
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-12 text-[var(--text-muted)]">
      {{ t('common.loading') }}
    </div>

    <!-- ── OVERVIEW TAB ────────────────────────────────────────────────── -->
    <div v-else-if="activeTab === 'overview'" class="space-y-6">

      <!-- Stats cards -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
          <div class="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">{{ t('mcp.connections') }}</div>
          <div class="text-2xl font-semibold text-[var(--text-primary)]">{{ status?.active_connections ?? 0 }}</div>
        </div>
        <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
          <div class="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">{{ t('mcp.availableTools') }}</div>
          <div class="text-2xl font-semibold text-[var(--text-primary)]">{{ status?.tools_count ?? 0 }}</div>
        </div>
        <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
          <div class="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">{{ t('mcp.protocolVersion') }}</div>
          <div class="text-2xl font-semibold text-[var(--text-primary)]">{{ status?.protocol_version ?? '—' }}</div>
        </div>
      </div>

      <!-- Connection URL -->
      <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-5 space-y-3">
        <h2 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('mcp.connectionUrl') }}</h2>
        <div class="flex items-center gap-2">
          <code class="flex-1 px-3 py-2 rounded-lg bg-[var(--bg-raised)] text-sm font-mono text-[var(--text-primary)] border border-[var(--border)] overflow-auto">
            {{ connectionUrl }}
          </code>
          <button
            class="px-3 py-2 rounded-lg text-xs font-medium bg-[var(--primary)]/10 text-[var(--primary)] hover:bg-[var(--primary)]/20 transition-colors whitespace-nowrap"
            @click="copyToClipboard(connectionUrl, 'url')"
          >
            {{ copiedUrl ? t('common.copied') : t('common.copy') }}
          </button>
        </div>
      </div>

      <!-- Demo Presenter -->
      <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-5 space-y-3">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('mcp.demo.title') }}</h2>
            <p class="text-xs text-[var(--text-muted)] mt-0.5">{{ t('mcp.demo.subtitle') }}</p>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <select
            v-model="demoSequence"
            class="px-3 py-1.5 rounded-lg text-xs bg-[var(--bg-raised)] border border-[var(--border)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
          >
            <option value="teaser">{{ t('mcp.demo.presetTeaser') }}</option>
            <option value="short">{{ t('mcp.demo.presetShort') }}</option>
            <option value="full">{{ t('mcp.demo.presetFull') }}</option>
          </select>
          <button
            class="px-4 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black hover:bg-[var(--primary-hover)] transition-colors disabled:opacity-50"
            :disabled="demoRunning"
            @click="runDemoPresenter"
          >
            {{ demoRunning ? t('common.running') : t('mcp.demo.runDemo') }}
          </button>
        </div>
      </div>

      <!-- API Keys for MCP -->
      <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-5 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold text-[var(--text-primary)]">
            {{ t('mcp.apiKeys') }}
            <UInfoTooltip :text="t('mcp.apiKeysHelp')" tourId="mcp-overview" />
          </h2>
          <button
            class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black hover:bg-[var(--primary-hover)] transition-colors disabled:opacity-50"
            :disabled="generatingKey"
            @click="generateMcpKey"
          >
            {{ generatingKey ? t('common.loading') : t('mcp.generateKey') }}
          </button>
        </div>

        <!-- Newly generated key (shown once) -->
        <div v-if="newKey" class="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 space-y-2">
          <p class="text-xs text-amber-300">{{ t('mcp.keyWarning') }}</p>
          <div class="flex items-center gap-2">
            <code class="flex-1 px-2 py-1.5 rounded bg-[var(--bg-raised)] text-xs font-mono text-[var(--text-primary)] border border-[var(--border)] break-all">
              {{ newKey }}
            </code>
            <button
              class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)]/10 text-[var(--primary)] hover:bg-[var(--primary)]/20 transition-colors whitespace-nowrap"
              @click="copyToClipboard(newKey!, 'key')"
            >
              {{ copiedKey ? t('common.copied') : t('common.copy') }}
            </button>
          </div>
        </div>

        <!-- Existing MCP keys -->
        <div v-if="mcpApiKeys.length" class="space-y-2">
          <div
            v-for="key in mcpApiKeys"
            :key="key.id"
            class="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-raised)] border border-[var(--border)]"
          >
            <div>
              <div class="text-sm text-[var(--text-primary)] font-medium">{{ key.name }}</div>
              <div class="text-xs text-[var(--text-muted)]">
                {{ key.key_prefix }}... &middot; {{ t('mcp.created') }} {{ formatTs(key.created_at) }}
                <span v-if="key.last_used_at"> &middot; {{ t('mcp.lastUsed') }} {{ formatTs(key.last_used_at) }}</span>
              </div>
            </div>
            <button
              class="px-2 py-1 rounded text-xs text-red-400 hover:bg-red-500/10 transition-colors"
              @click="revokeKey(key.id)"
            >
              {{ t('mcp.revoke') }}
            </button>
          </div>
        </div>
        <p v-else class="text-xs text-[var(--text-muted)]">{{ t('mcp.noKeys') }}</p>
      </div>
    </div>

    <!-- ── TOOLS TAB ───────────────────────────────────────────────────── -->
    <div v-else-if="activeTab === 'tools'" class="space-y-3">
      <p class="text-sm text-[var(--text-muted)]">{{ t('mcp.toolsDescription') }}</p>

      <div v-if="!tools.length" class="text-center py-8 text-[var(--text-muted)] text-sm">
        {{ t('common.noData') }}
      </div>

      <div v-for="tool in tools" :key="tool.name" class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] overflow-hidden">
        <button
          class="w-full flex items-center justify-between p-4 text-left hover:bg-[var(--bg-raised)]/50 transition-colors"
          @click="toggleTool(tool.name)"
        >
          <div class="flex-1 min-w-0">
            <div class="text-sm font-mono font-medium text-[var(--primary)]">{{ tool.name }}</div>
            <div class="text-xs text-[var(--text-muted)] mt-0.5 truncate">{{ tool.description }}</div>
          </div>
          <div class="flex items-center gap-2 ml-3">
            <button
              class="px-2.5 py-1 rounded-lg text-xs font-medium bg-[var(--accent)]/10 text-[var(--accent)] hover:bg-[var(--accent)]/20 transition-colors"
              @click.stop="openTestModal(tool)"
            >
              {{ t('mcp.testTool') }}
            </button>
            <svg
              class="h-4 w-4 text-[var(--text-muted)] transition-transform"
              :class="{ 'rotate-180': expandedTool === tool.name }"
              fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
            </svg>
          </div>
        </button>

        <div v-if="expandedTool === tool.name" class="border-t border-[var(--border)] p-4">
          <h4 class="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2">{{ t('mcp.parameterSchema') }}</h4>
          <pre class="text-xs font-mono text-[var(--text-secondary)] bg-[var(--bg-raised)] rounded-lg p-3 overflow-auto max-h-64">{{ JSON.stringify(tool.inputSchema, null, 2) }}</pre>
        </div>
      </div>
    </div>

    <!-- ── INTEGRATION TAB ─────────────────────────────────────────────── -->
    <div v-else-if="activeTab === 'integration'" class="space-y-6">

      <!-- Claude Desktop config -->
      <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-5 space-y-3">
        <h2 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('mcp.claudeDesktopTitle') }}</h2>
        <p class="text-xs text-[var(--text-muted)]">{{ t('mcp.claudeDesktopHelp') }}</p>
        <div class="relative">
          <pre class="text-xs font-mono text-[var(--text-secondary)] bg-[var(--bg-raised)] rounded-lg p-4 overflow-auto border border-[var(--border)]">{{ claudeDesktopConfig }}</pre>
          <button
            class="absolute top-2 right-2 px-2 py-1 rounded text-xs font-medium bg-[var(--primary)]/10 text-[var(--primary)] hover:bg-[var(--primary)]/20 transition-colors"
            @click="copyToClipboard(claudeDesktopConfig, 'config')"
          >
            {{ copiedConfig ? t('common.copied') : t('common.copy') }}
          </button>
        </div>
      </div>

      <!-- Python example -->
      <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-5 space-y-3">
        <h2 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('mcp.pythonClientTitle') }}</h2>
        <p class="text-xs text-[var(--text-muted)]">{{ t('mcp.pythonClientHelp') }}</p>
        <pre class="text-xs font-mono text-[var(--text-secondary)] bg-[var(--bg-raised)] rounded-lg p-4 overflow-auto border border-[var(--border)]">{{ pythonExample }}</pre>
      </div>

      <!-- Protocol reference -->
      <div class="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-5 space-y-3">
        <h2 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('mcp.protocolFlowTitle') }}</h2>
        <ol class="list-decimal list-inside text-sm text-[var(--text-secondary)] space-y-2">
          <li>{{ t('mcp.protocolStep1') }}</li>
          <li>{{ t('mcp.protocolStep2') }}</li>
          <li>{{ t('mcp.protocolStep3') }}</li>
          <li>{{ t('mcp.protocolStep4') }}</li>
        </ol>
      </div>
    </div>

    <!-- ── LOG TAB ─────────────────────────────────────────────────────── -->
    <div v-else-if="activeTab === 'log'" class="space-y-3">
      <div class="flex items-center justify-between">
        <p class="text-sm text-[var(--text-muted)]">{{ t('mcp.logDescription') }}</p>
        <button
          class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--bg-raised)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
          @click="fetchLog"
        >
          {{ t('common.refresh') }}
        </button>
      </div>

      <div v-if="!logEntries.length" class="text-center py-8 text-[var(--text-muted)] text-sm">
        {{ t('mcp.noLogEntries') }}
      </div>

      <div v-else class="rounded-xl border border-[var(--border)] overflow-hidden">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-[var(--bg-surface)] border-b border-[var(--border)]">
              <th class="text-left px-4 py-2 text-xs font-medium text-[var(--text-muted)] uppercase">{{ t('mcp.logTimestamp') }}</th>
              <th class="text-left px-4 py-2 text-xs font-medium text-[var(--text-muted)] uppercase">{{ t('mcp.logTool') }}</th>
              <th class="text-left px-4 py-2 text-xs font-medium text-[var(--text-muted)] uppercase">{{ t('mcp.logStatus') }}</th>
              <th class="text-right px-4 py-2 text-xs font-medium text-[var(--text-muted)] uppercase">{{ t('mcp.logDuration') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(entry, i) in logEntries"
              :key="i"
              class="border-b border-[var(--border)] last:border-0 hover:bg-[var(--bg-raised)]/50"
            >
              <td class="px-4 py-2.5 text-xs text-[var(--text-muted)] font-mono">{{ formatTs(entry.ts) }}</td>
              <td class="px-4 py-2.5 text-xs text-[var(--primary)] font-mono">{{ entry.tool }}</td>
              <td class="px-4 py-2.5">
                <span
                  class="inline-flex px-2 py-0.5 rounded-full text-xs font-medium"
                  :class="{
                    'bg-emerald-500/10 text-emerald-400': entry.status === 'ok',
                    'bg-amber-500/10 text-amber-400': entry.status === 'error',
                    'bg-red-500/10 text-red-400': entry.status === 'exception',
                  }"
                >
                  {{ entry.status }}
                </span>
              </td>
              <td class="px-4 py-2.5 text-xs text-[var(--text-muted)] text-right font-mono">{{ entry.duration_ms }}ms</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── TEST TOOL MODAL ─────────────────────────────────────────────── -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="testModalOpen" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="testModalOpen = false" />
          <div class="relative w-full max-w-xl bg-[var(--bg-surface)] border border-[var(--border)] rounded-2xl shadow-2xl p-6 space-y-4 mx-4">
            <div class="flex items-center justify-between">
              <h3 class="text-sm font-semibold text-[var(--text-primary)]">
                {{ t('mcp.testToolTitle') }}: <span class="font-mono text-[var(--primary)]">{{ testTool?.name }}</span>
              </h3>
              <button class="text-[var(--text-muted)] hover:text-[var(--text-primary)]" @click="testModalOpen = false">
                <svg class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div>
              <label class="block text-xs text-[var(--text-muted)] mb-1">{{ t('mcp.parameters') }}</label>
              <textarea
                v-model="testParams"
                rows="6"
                class="w-full px-3 py-2 rounded-lg bg-[var(--bg-raised)] border border-[var(--border)] text-sm font-mono text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)] resize-none"
              />
            </div>

            <button
              class="w-full px-4 py-2 rounded-lg text-sm font-medium bg-[var(--primary)] text-black hover:bg-[var(--primary-hover)] transition-colors disabled:opacity-50"
              :disabled="testRunning"
              @click="runTest"
            >
              {{ testRunning ? t('common.loading') : t('mcp.runTest') }}
            </button>

            <div v-if="testResult !== null">
              <label class="block text-xs text-[var(--text-muted)] mb-1">{{ t('mcp.result') }}</label>
              <pre class="text-xs font-mono text-[var(--text-secondary)] bg-[var(--bg-raised)] rounded-lg p-3 overflow-auto max-h-48 border border-[var(--border)]">{{ testResult }}</pre>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
