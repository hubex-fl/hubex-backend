<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../lib/api";
import { fmtRelativeIso } from "../lib/relativeTime";
import { useToastStore } from "../stores/toast";

const toast = useToastStore();
const { t, locale } = useI18n();

type ApiKeyOut = {
  id: number;
  name: string;
  key_prefix: string;
  caps: string[];
  expires_at: string | null;
  last_used_at: string | null;
  revoked: boolean;
  created_at: string;
};

const keys = ref<ApiKeyOut[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// Capability scopes for checkboxes
const capScopes = [
  { value: "devices.read", label: "Read Devices" },
  { value: "devices.write", label: "Write Devices" },
  { value: "vars.read", label: "Read Variables" },
  { value: "vars.write", label: "Write Variables" },
  { value: "telemetry.read", label: "Read Telemetry" },
  { value: "telemetry.emit", label: "Send Telemetry" },
  { value: "alerts.read", label: "Read Alerts" },
  { value: "alerts.write", label: "Write Alerts" },
  { value: "automations.read", label: "Read Automations" },
  { value: "dashboards.read", label: "Read Dashboards" },
  { value: "events.read", label: "Read Events" },
  { value: "webhooks.read", label: "Read Webhooks" },
];

// Create form
const showCreate = ref(false);
const newName = ref("");
const selectedCaps = ref<string[]>([]);
const newExpiry = ref<number | null>(null);
const creating = ref(false);
const createdKey = ref<string | null>(null);
const copied = ref(false);

async function loadKeys() {
  loading.value = true;
  error.value = null;
  try {
    keys.value = await apiFetch<ApiKeyOut[]>("/api/v1/api-keys");
  } catch {
    error.value = "Failed to load API keys";
  } finally {
    loading.value = false;
  }
}

async function handleCreate() {
  if (!newName.value.trim()) return;
  creating.value = true;
  try {
    const result = await apiFetch<ApiKeyOut & { key: string }>("/api/v1/api-keys", {
      method: "POST",
      body: JSON.stringify({
        name: newName.value.trim(),
        caps: selectedCaps.value,
        expires_in_days: newExpiry.value || null,
      }),
    });
    createdKey.value = result.key;
    toast.addToast("API key created", "success");
    await loadKeys();
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Failed to create API key";
    toast.addToast(msg, "error");
  } finally {
    creating.value = false;
  }
}

async function handleRevoke(id: number) {
  if (!confirm("Revoke this API key? This cannot be undone.")) return;
  try {
    await apiFetch(`/api/v1/api-keys/${id}`, { method: "DELETE" });
    toast.addToast("API key revoked", "success");
    await loadKeys();
  } catch {
    toast.addToast("Failed to revoke API key", "error");
  }
}

function copyKey() {
  if (createdKey.value) {
    navigator.clipboard.writeText(createdKey.value);
    copied.value = true;
    setTimeout(() => (copied.value = false), 2000);
  }
}

function closeCreate() {
  showCreate.value = false;
  createdKey.value = null;
  newName.value = "";
  selectedCaps.value = [];
  newExpiry.value = null;
}

function relativeTime(dt: string | null): string {
  if (!dt) return t('apiKeyManager.never');
  return fmtRelativeIso(dt);
}

// Sprint 8 R4 B3 fix: was using .toLocaleDateString() without locale arg, which
// defaulted to the browser locale (may differ from the app's i18n locale).
function formatExpiryDate(dt: string): string {
  return new Date(dt).toLocaleDateString(locale.value);
}

onMounted(loadKeys);
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <div>
        <h3 class="text-sm font-semibold text-[var(--text-primary)]">API Keys</h3>
        <p class="text-xs text-[var(--text-muted)]">Service-to-service authentication with scoped capabilities</p>
      </div>
      <button
        class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black hover:bg-[var(--primary-hover)] transition-colors"
        @click="showCreate = true"
      >
        + Create Key
      </button>
    </div>

    <!-- Error -->
    <div v-if="error" class="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-xs text-red-400">
      {{ error }}
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-xs text-[var(--text-muted)]">Loading...</div>

    <!-- Keys list -->
    <div v-else-if="keys.length" class="space-y-2">
      <div
        v-for="key in keys"
        :key="key.id"
        :class="[
          'flex items-center gap-3 px-4 py-3 rounded-lg border transition-colors',
          key.revoked
            ? 'border-red-500/20 bg-red-500/5 opacity-60'
            : 'border-[var(--border)] bg-[var(--bg-raised)]',
        ]"
      >
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="text-xs font-medium text-[var(--text-primary)]">{{ key.name }}</span>
            <span v-if="key.revoked" class="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400">revoked</span>
          </div>
          <div class="flex items-center gap-3 mt-1 text-[10px] text-[var(--text-muted)]">
            <span class="font-mono">{{ key.key_prefix }}...</span>
            <span :title="key.caps.join(', ')">{{ key.caps.length }} capabilities</span>
            <span :class="key.last_used_at ? 'text-[var(--status-ok)]' : ''">
              {{ key.last_used_at ? t('apiKeyManager.lastUsed', { when: relativeTime(key.last_used_at) }) : t('apiKeyManager.neverUsed') }}
            </span>
            <span v-if="key.expires_at">{{ t('apiKeyManager.expiresOn', { date: formatExpiryDate(key.expires_at) }) }}</span>
          </div>
        </div>
        <button
          v-if="!key.revoked"
          class="px-2.5 py-1 rounded-lg text-xs font-medium text-[var(--text-muted)] hover:text-red-400 hover:bg-red-500/10 transition-colors"
          @click="handleRevoke(key.id)"
        >
          Revoke
        </button>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="text-center py-6">
      <p class="text-xs text-[var(--text-muted)]">No API keys yet</p>
      <p class="text-[10px] text-[var(--text-muted)] mt-1">Create a key for service-to-service integrations</p>
    </div>

    <!-- Create modal -->
    <Teleport to="body">
      <div v-if="showCreate" class="fixed inset-0 z-50 flex items-center justify-center p-4" @click.self="closeCreate">
        <div class="absolute inset-0 bg-black/80 backdrop-blur-sm" @click="closeCreate" />
        <div class="relative w-full max-w-md bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl shadow-2xl p-5 space-y-4">
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">
            {{ createdKey ? 'API Key Created' : 'Create API Key' }}
          </h3>

          <!-- Created key display -->
          <template v-if="createdKey">
            <div class="rounded-lg border border-[var(--primary)]/30 bg-[var(--primary)]/5 p-3">
              <p class="text-[10px] text-[var(--text-muted)] mb-1">Copy this key now — it won't be shown again</p>
              <div class="flex items-center gap-2">
                <code class="flex-1 text-xs font-mono text-[var(--text-primary)] break-all">{{ createdKey }}</code>
                <button
                  class="px-2.5 py-1 rounded text-xs font-medium bg-[var(--primary)] text-black"
                  @click="copyKey"
                >
                  {{ copied ? 'Copied!' : 'Copy' }}
                </button>
              </div>
            </div>
            <div class="rounded-lg bg-[var(--bg-raised)] px-3 py-2 text-[10px] text-[var(--text-muted)] font-mono">
              curl -H "Authorization: Bearer {{ createdKey?.slice(0, 16) }}..." {{ window?.location?.origin || 'https://your-hubex' }}/api/v1/devices
            </div>
            <button
              class="w-full px-3 py-2 rounded-lg text-xs font-medium border border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              @click="closeCreate"
            >
              Done
            </button>
          </template>

          <!-- Create form -->
          <template v-else>
            <div>
              <label class="text-[10px] font-medium text-[var(--text-muted)]">Name *</label>
              <input
                v-model="newName"
                class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)]"
                placeholder="e.g. n8n Integration"
              />
            </div>
            <div>
              <label class="text-[10px] font-medium text-[var(--text-muted)]">Capabilities</label>
              <div class="mt-1.5 grid grid-cols-2 gap-1.5">
                <label v-for="scope in capScopes" :key="scope.value" class="flex items-center gap-1.5 px-2 py-1.5 rounded border border-[var(--border)] hover:border-[var(--primary)]/40 cursor-pointer text-[10px]">
                  <input type="checkbox" :value="scope.value" v-model="selectedCaps" class="rounded" />
                  <span class="text-[var(--text-primary)]">{{ scope.label }}</span>
                </label>
              </div>
              <p class="text-[10px] text-[var(--text-muted)] mt-1">Select what this key can access</p>
            </div>
            <div>
              <label class="text-[10px] font-medium text-[var(--text-muted)]">Expiry (days, optional)</label>
              <input
                v-model.number="newExpiry"
                type="number"
                min="1"
                class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)]"
                placeholder="Leave empty for no expiry"
              />
            </div>
            <div class="flex gap-2 justify-end">
              <button
                class="px-3 py-2 rounded-lg text-xs font-medium text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                @click="closeCreate"
              >
                Cancel
              </button>
              <button
                :disabled="creating || !newName.trim()"
                class="px-3 py-2 rounded-lg text-xs font-medium bg-[var(--primary)] text-black hover:bg-[var(--primary-hover)] disabled:opacity-50"
                @click="handleCreate"
              >
                {{ creating ? 'Creating...' : 'Create Key' }}
              </button>
            </div>
          </template>
        </div>
      </div>
    </Teleport>
  </div>
</template>
