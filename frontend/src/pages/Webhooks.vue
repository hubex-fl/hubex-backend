<script setup lang="ts">
import { ref, onMounted } from "vue";
import { apiFetch } from "../lib/api";
import { parseApiError, mapErrorToUserText } from "../lib/errors";
import UCard from "../components/ui/UCard.vue";
import UButton from "../components/ui/UButton.vue";
import UInput from "../components/ui/UInput.vue";
import UBadge from "../components/ui/UBadge.vue";
import UModal from "../components/ui/UModal.vue";
import UEmpty from "../components/ui/UEmpty.vue";
import UToggle from "../components/ui/UToggle.vue";
import { useToastStore } from "../stores/toast";
const toast = useToastStore();

type Webhook = {
  id: number;
  url: string;
  secret: string;
  event_filter: string[];
  active: boolean;
  created_at: string;
};

const webhooks = ref<Webhook[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// Create modal
const showCreate = ref(false);
const createUrl = ref("");
const createSecret = ref("");
const createEvents = ref("");
const createSaving = ref(false);
const createError = ref<string | null>(null);

async function loadWebhooks() {
  loading.value = true;
  error.value = null;
  try {
    webhooks.value = await apiFetch<Webhook[]>("/api/v1/webhooks");
  } catch (e) {
    error.value = mapErrorToUserText(parseApiError(e), "Failed to load webhooks");
  } finally {
    loading.value = false;
  }
}

async function createWebhook() {
  createSaving.value = true;
  createError.value = null;
  try {
    const eventFilter = createEvents.value.trim()
      ? createEvents.value.split(",").map(s => s.trim()).filter(Boolean)
      : [];
    await apiFetch("/api/v1/webhooks", {
      method: "POST",
      body: JSON.stringify({
        url: createUrl.value.trim(),
        secret: createSecret.value.trim() || "hubex-webhook",
        event_filter: eventFilter,
      }),
    });
    showCreate.value = false;
    createUrl.value = "";
    createSecret.value = "";
    createEvents.value = "";
    await loadWebhooks();
  } catch (e) {
    createError.value = mapErrorToUserText(parseApiError(e), "Failed to create webhook");
  } finally {
    createSaving.value = false;
  }
}

async function deleteWebhook(id: number) {
  if (!confirm("Delete this webhook subscription?")) return;
  try {
    await apiFetch(`/api/v1/webhooks/${id}`, { method: "DELETE" });
    webhooks.value = webhooks.value.filter(w => w.id !== id);
    toast.addToast("Webhook deleted", "success");
  } catch { toast.addToast("Failed to delete webhook", "error"); }
}

async function testWebhook(webhook: Webhook) {
  try {
    const r = await fetch(webhook.url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ test: true, source: "hubex", timestamp: new Date().toISOString() }),
      signal: AbortSignal.timeout(5000),
    });
    toast.addToast(r.ok ? `Test successful (${r.status})` : `Test failed (${r.status})`, r.ok ? "success" : "error");
  } catch (e: unknown) {
    toast.addToast(`Test failed: ${e instanceof Error ? e.message : 'Connection error'}`, "error");
  }
}

// Delivery history
type Delivery = {
  id: number;
  webhook_id: number;
  event_id: number;
  status_code: number | null;
  response_time_ms: number | null;
  attempt: number;
  success: boolean;
  created_at: string;
};

const deliveryWebhookId = ref<number | null>(null);
const deliveries = ref<Delivery[]>([]);
const deliveriesLoading = ref(false);

async function showDeliveries(webhookId: number) {
  deliveryWebhookId.value = webhookId;
  deliveriesLoading.value = true;
  try {
    deliveries.value = await apiFetch<Delivery[]>(`/api/v1/webhooks/${webhookId}/deliveries?limit=30`);
  } catch {
    deliveries.value = [];
  } finally {
    deliveriesLoading.value = false;
  }
}

onMounted(loadWebhooks);
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-xl font-semibold text-[var(--text-primary)]">Webhooks</h1>
        <p class="text-xs text-[var(--text-muted)] mt-0.5">HTTP callbacks for system events — integrate with n8n, Zapier, or custom endpoints</p>
      </div>
      <div class="flex gap-2">
        <UButton size="sm" variant="secondary" @click="loadWebhooks">Refresh</UButton>
        <UButton size="sm" @click="showCreate = true">+ New Webhook</UButton>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="h-16 rounded-xl bg-[var(--bg-surface)] animate-pulse" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="rounded-lg border border-[var(--status-bad)]/30 bg-[var(--status-bad)]/10 px-4 py-3 text-sm text-[var(--status-bad)]">
      {{ error }}
    </div>

    <!-- Empty -->
    <UEmpty v-else-if="!webhooks.length"
      title="No webhooks configured"
      description="Webhooks notify external services when events occur in HUBEX. Create one to integrate with n8n, Zapier, or your own API."
      icon="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3"
    >
      <UButton size="sm" @click="showCreate = true">Create Webhook</UButton>
    </UEmpty>

    <!-- Webhook list -->
    <div v-else class="space-y-3">
      <UCard v-for="wh in webhooks" :key="wh.id" padding="md">
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 mb-1">
              <UBadge :status="wh.active ? 'ok' : 'neutral'" size="sm">{{ wh.active ? 'active' : 'paused' }}</UBadge>
              <span class="text-xs font-mono text-[var(--text-primary)] truncate">{{ wh.url }}</span>
            </div>
            <div class="flex items-center gap-3 text-[10px] text-[var(--text-muted)]">
              <span v-if="wh.event_filter?.length">Events: {{ wh.event_filter.join(', ') }}</span>
              <span v-else>All events</span>
              <span>Created {{ new Date(wh.created_at).toLocaleDateString() }}</span>
            </div>
          </div>
          <div class="flex items-center gap-1.5 shrink-0">
            <UButton size="sm" variant="ghost" @click="showDeliveries(wh.id)" title="Delivery history">History</UButton>
            <UButton size="sm" variant="ghost" @click="testWebhook(wh)" title="Send test event">Test</UButton>
            <UButton size="sm" variant="ghost" class="text-[var(--text-muted)] hover:text-[var(--status-bad)]" @click="deleteWebhook(wh.id)" title="Delete webhook">
              <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" /></svg>
            </UButton>
          </div>
        </div>
      </UCard>
    </div>

    <!-- Delivery History Modal -->
    <UModal :open="deliveryWebhookId !== null" title="Delivery History" size="lg" @close="deliveryWebhookId = null">
      <div v-if="deliveriesLoading" class="text-xs text-[var(--text-muted)] py-4 text-center">Loading...</div>
      <div v-else-if="!deliveries.length" class="text-xs text-[var(--text-muted)] py-4 text-center">No deliveries recorded yet</div>
      <div v-else class="space-y-1.5 max-h-[50vh] overflow-y-auto">
        <div
          v-for="d in deliveries"
          :key="d.id"
          :class="[
            'flex items-center gap-3 px-3 py-2 rounded-lg text-xs',
            d.success ? 'bg-[var(--status-ok)]/5' : 'bg-[var(--status-bad)]/5',
          ]"
        >
          <span :class="d.success ? 'text-[var(--status-ok)]' : 'text-[var(--status-bad)]'" class="font-mono font-bold w-8">{{ d.status_code ?? '---' }}</span>
          <span class="text-[var(--text-muted)] w-16">{{ d.response_time_ms ? `${Math.round(d.response_time_ms)}ms` : '---' }}</span>
          <span class="text-[var(--text-muted)]">attempt {{ d.attempt }}</span>
          <span class="flex-1" />
          <span class="text-[var(--text-muted)]">{{ new Date(d.created_at).toLocaleString() }}</span>
        </div>
      </div>
    </UModal>

    <!-- Create Modal -->
    <UModal :open="showCreate" title="New Webhook" @close="showCreate = false">
      <div class="space-y-3 p-2">
        <UInput v-model="createUrl" label="Endpoint URL" placeholder="https://your-server.com/webhook" />
        <UInput v-model="createSecret" label="Secret (for HMAC signature)" placeholder="my-webhook-secret" />
        <UInput v-model="createEvents" label="Event Filter (comma-separated, empty = all)" placeholder="device.offline, variable.changed, alert.fired" />
        <div v-if="createError" class="text-xs text-[var(--status-bad)]">{{ createError }}</div>
      </div>
      <template #footer>
        <UButton variant="ghost" @click="showCreate = false">Cancel</UButton>
        <UButton :loading="createSaving" @click="createWebhook">Create</UButton>
      </template>
    </UModal>
  </div>
</template>
