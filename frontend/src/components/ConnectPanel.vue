<script setup lang="ts">
import { ref, watch, computed } from "vue";
import { useRouter } from "vue-router";
import { useConnectPanel } from "../composables/useConnectPanel";
import { apiFetch } from "../lib/api";

const router = useRouter();
const { isOpen, context, close } = useConnectPanel();

interface RelatedItem {
  id: number | string;
  label: string;
  sub?: string;
  href?: string;
}

const loading = ref(false);
const relatedVars = ref<RelatedItem[]>([]);
const relatedAlerts = ref<RelatedItem[]>([]);
const relatedAutomations = ref<RelatedItem[]>([]);

watch(
  [isOpen, context],
  async ([open, ctx]) => {
    if (!open || !ctx) {
      relatedVars.value = [];
      relatedAlerts.value = [];
      relatedAutomations.value = [];
      return;
    }
    loading.value = true;
    try {
      if (ctx.type === "device" && ctx.deviceUid) {
        const [vars, alerts, autos] = await Promise.allSettled([
          apiFetch<any[]>(`/api/v1/variables/device/${encodeURIComponent(ctx.deviceUid)}`),
          apiFetch<any[]>("/api/v1/alerts/rules"),
          apiFetch<any[]>("/api/v1/automations"),
        ]);

        relatedVars.value =
          vars.status === "fulfilled"
            ? vars.value.slice(0, 6).map((v) => ({
                id: v.key,
                label: v.key,
                sub: v.value !== undefined && v.value !== null ? String(v.value) : "—",
                href: "/variables",
              }))
            : [];

        relatedAlerts.value =
          alerts.status === "fulfilled"
            ? alerts.value
                .filter((a: any) => a.device_uid === ctx.deviceUid)
                .slice(0, 4)
                .map((a: any) => ({
                  id: a.id,
                  label: a.name,
                  sub: a.severity ?? "info",
                  href: "/alerts",
                }))
            : [];

        relatedAutomations.value =
          autos.status === "fulfilled"
            ? autos.value
                .filter((a: any) => a.trigger_device_uid === ctx.deviceUid)
                .slice(0, 4)
                .map((a: any) => ({
                  id: a.id,
                  label: a.name,
                  sub: a.enabled ? "enabled" : "disabled",
                  href: "/automations",
                }))
            : [];
      } else if (ctx.type === "variable" && ctx.variableKey) {
        const [alerts, autos] = await Promise.allSettled([
          apiFetch<any[]>("/api/v1/alerts/rules"),
          apiFetch<any[]>("/api/v1/automations"),
        ]);
        relatedVars.value = [];
        relatedAlerts.value =
          alerts.status === "fulfilled"
            ? alerts.value
                .filter((a: any) => a.variable_key === ctx.variableKey)
                .slice(0, 4)
                .map((a: any) => ({
                  id: a.id,
                  label: a.name,
                  sub: a.severity ?? "info",
                  href: "/alerts",
                }))
            : [];
        relatedAutomations.value =
          autos.status === "fulfilled"
            ? autos.value
                .filter(
                  (a: any) =>
                    a.trigger_variable_key === ctx.variableKey ||
                    a.action_variable_key === ctx.variableKey
                )
                .slice(0, 4)
                .map((a: any) => ({
                  id: a.id,
                  label: a.name,
                  sub: a.enabled ? "enabled" : "disabled",
                  href: "/automations",
                }))
            : [];
      }
    } finally {
      loading.value = false;
    }
  },
  { immediate: false }
);

const typeIcon: Record<string, string> = {
  device:
    "M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z",
  variable:
    "M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5",
  automation:
    "M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z",
  alert:
    "M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0",
};

const totalConnections = computed(
  () =>
    relatedVars.value.length +
    relatedAlerts.value.length +
    relatedAutomations.value.length
);

function navTo(href: string) {
  close();
  router.push(href);
}

function createAlert() {
  const query: Record<string, string> = { create: "true" };
  if (context.value?.variableKey) query.variable_key = context.value.variableKey;
  if (context.value?.deviceUid) query.device_uid = String(context.value.deviceUid);
  close();
  router.push({ path: "/alerts", query });
}

function createAutomation() {
  const query: Record<string, string> = { create: "true" };
  if (context.value?.variableKey) query.variable_key = context.value.variableKey;
  if (context.value?.deviceUid) query.device_uid = String(context.value.deviceUid);
  close();
  router.push({ path: "/automations", query });
}

function viewVariables() {
  close();
  router.push("/variables");
}

function viewDevice() {
  if (context.value?.deviceId) {
    close();
    router.push(`/devices/${context.value.deviceId}`);
  }
}
</script>

<template>
  <Teleport to="body">
    <!-- Backdrop -->
    <Transition name="cp-fade">
      <div
        v-if="isOpen"
        class="cp-backdrop"
        @click="close"
      />
    </Transition>

    <!-- Slide-over panel -->
    <Transition name="cp-slide">
      <div v-if="isOpen" class="cp-panel" role="dialog" aria-modal="true">

        <!-- Header -->
        <div class="cp-header">
          <div class="flex items-center gap-2.5 min-w-0">
            <div class="cp-type-icon">
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" :d="typeIcon[context?.type ?? 'device']" />
              </svg>
            </div>
            <div class="min-w-0">
              <p class="text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-wide">{{ context?.type }}</p>
              <p class="text-sm font-semibold text-[var(--text-primary)] truncate">{{ context?.name }}</p>
            </div>
          </div>
          <button class="cp-close-btn" @click="close" aria-label="Close">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Scroll area -->
        <div class="cp-body">

          <!-- Loading skeleton -->
          <div v-if="loading" class="space-y-3">
            <div v-for="i in 4" :key="i" class="h-10 rounded-lg bg-[var(--bg-raised)] animate-pulse" />
          </div>

          <template v-else>

            <!-- Quick actions -->
            <div class="cp-section">
              <p class="cp-section-label">Quick actions</p>
              <div class="grid grid-cols-2 gap-2">
                <button
                  v-if="context?.type === 'device' || context?.type === 'variable'"
                  class="cp-action-btn"
                  @click="createAlert"
                >
                  <svg class="h-4 w-4 text-[var(--status-warn)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
                  </svg>
                  <span>Alert</span>
                </button>
                <button class="cp-action-btn" @click="createAutomation">
                  <svg class="h-4 w-4 text-[var(--primary)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                  </svg>
                  <span>Automation</span>
                </button>
                <button
                  v-if="context?.type === 'device'"
                  class="cp-action-btn"
                  @click="viewVariables"
                >
                  <svg class="h-4 w-4 text-[var(--accent)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h1.5C5.496 19.5 6 18.996 6 18.375m-3.75.125v-1.5m0 0A1.125 1.125 0 013.375 16.5h1.5m0 0h9m-9 0A1.125 1.125 0 003.375 16.5m10.5 2.625V6.375a1.125 1.125 0 00-1.125-1.125H6.375A1.125 1.125 0 005.25 6.375v10.5m7.5.375A1.125 1.125 0 0013.875 19.5h1.5c.621 0 1.125-.504 1.125-1.125V11.25" />
                  </svg>
                  <span>Variables</span>
                </button>
                <button
                  v-if="context?.type === 'variable' && context?.deviceId"
                  class="cp-action-btn"
                  @click="viewDevice"
                >
                  <svg class="h-4 w-4 text-[var(--cat-hardware)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z" />
                  </svg>
                  <span>Device</span>
                </button>
              </div>
            </div>

            <!-- Variables connected to this device -->
            <div v-if="context?.type === 'device'" class="cp-section">
              <div class="flex items-center justify-between mb-2">
                <p class="cp-section-label">Variables ({{ relatedVars.length }})</p>
                <button class="cp-link" @click="navTo('/variables')">View all →</button>
              </div>
              <div v-if="relatedVars.length === 0" class="cp-empty">No variables yet. Devices auto-discover variables from telemetry.</div>
              <div v-else class="space-y-1">
                <div
                  v-for="v in relatedVars"
                  :key="v.id"
                  class="cp-conn-item"
                >
                  <span class="font-mono text-xs text-[var(--text-primary)] truncate">{{ v.label }}</span>
                  <span class="text-[10px] text-[var(--text-muted)] shrink-0">{{ v.sub }}</span>
                </div>
              </div>
            </div>

            <!-- Alert Rules -->
            <div class="cp-section">
              <div class="flex items-center justify-between mb-2">
                <p class="cp-section-label">Alert Rules ({{ relatedAlerts.length }})</p>
                <button class="cp-link" @click="navTo('/alerts')">View all →</button>
              </div>
              <div v-if="relatedAlerts.length === 0" class="cp-empty">No alert rules linked to this {{ context?.type }}.</div>
              <div v-else class="space-y-1">
                <div v-for="a in relatedAlerts" :key="a.id" class="cp-conn-item">
                  <span class="text-xs text-[var(--text-primary)] truncate">{{ a.label }}</span>
                  <span
                    class="text-[10px] font-mono shrink-0"
                    :class="{
                      'text-[var(--status-bad)]': a.sub === 'critical',
                      'text-[var(--status-warn)]': a.sub === 'warning',
                      'text-[var(--text-muted)]': a.sub === 'info',
                    }"
                  >{{ a.sub }}</span>
                </div>
              </div>
            </div>

            <!-- Automations -->
            <div class="cp-section">
              <div class="flex items-center justify-between mb-2">
                <p class="cp-section-label">Automations ({{ relatedAutomations.length }})</p>
                <button class="cp-link" @click="navTo('/automations')">View all →</button>
              </div>
              <div v-if="relatedAutomations.length === 0" class="cp-empty">No automations linked to this {{ context?.type }}.</div>
              <div v-else class="space-y-1">
                <div v-for="a in relatedAutomations" :key="a.id" class="cp-conn-item">
                  <span class="text-xs text-[var(--text-primary)] truncate">{{ a.label }}</span>
                  <span
                    class="text-[10px] font-mono shrink-0"
                    :class="{
                      'text-[var(--accent)]': a.sub === 'enabled',
                      'text-[var(--text-muted)]': a.sub === 'disabled',
                    }"
                  >{{ a.sub }}</span>
                </div>
              </div>
            </div>

          </template>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.cp-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 400;
}

.cp-panel {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 360px;
  max-width: 90vw;
  z-index: 401;
  background: var(--bg-surface);
  border-left: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  box-shadow: -8px 0 32px rgba(0, 0, 0, 0.3);
}

.cp-fade-enter-active,
.cp-fade-leave-active { transition: opacity 0.2s ease; }
.cp-fade-enter-from,
.cp-fade-leave-to { opacity: 0; }

.cp-slide-enter-active,
.cp-slide-leave-active { transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1); }
.cp-slide-enter-from,
.cp-slide-leave-to { transform: translateX(100%); }

.cp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  gap: 8px;
}

.cp-type-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  background: var(--bg-raised);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
  shrink: 0;
}

.cp-close-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  transition: background 0.15s, color 0.15s;
  flex-shrink: 0;
}

.cp-close-btn:hover {
  background: var(--bg-raised);
  color: var(--text-primary);
}

.cp-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.cp-section {
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}

.cp-section:last-child {
  border-bottom: none;
}

.cp-section-label {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.cp-link {
  font-size: 0.6875rem;
  color: var(--primary);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  transition: opacity 0.15s;
}

.cp-link:hover {
  opacity: 0.8;
  text-decoration: underline;
}

.cp-empty {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-style: italic;
  padding: 4px 0;
}

.cp-conn-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 5px 8px;
  border-radius: var(--radius-sm);
  gap: 8px;
  background: var(--bg-raised);
}

.cp-action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px 8px;
  border-radius: var(--radius-md);
  background: var(--bg-raised);
  border: 1px solid var(--border);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.cp-action-btn:hover {
  background: var(--bg-raised);
  border-color: var(--border-strong);
  color: var(--text-primary);
}
</style>
