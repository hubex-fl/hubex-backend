<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute } from "vue-router";

const { t } = useI18n();
import { branding } from "../lib/branding";

const route = useRoute();
const token = route.params.token as string;

type Widget = {
  id: number; widget_type: string; variable_key: string | null;
  device_uid: string | null; label: string | null; unit: string | null;
  min_value: number | null; max_value: number | null;
  display_config: Record<string, unknown> | null;
  sort_order: number;
};

type Dashboard = {
  id: number; name: string; description: string | null;
  widgets: Widget[];
};

const dashboard = ref<Dashboard | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
const needsPin = ref(false);
const pinInput = ref("");
const pinError = ref("");

async function loadDashboard(pin?: string) {
  loading.value = true;
  error.value = null;
  try {
    const url = `/api/v1/dashboards/public/${token}` + (pin ? `?pin=${pin}` : "");
    const res = await fetch(url);
    if (res.status === 403) {
      const data = await res.json();
      if (data.detail?.includes("PIN")) {
        needsPin.value = true;
        if (pin) pinError.value = "Invalid PIN";
        loading.value = false;
        return;
      }
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    dashboard.value = await res.json();
    needsPin.value = false;
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "Failed to load dashboard";
  } finally {
    loading.value = false;
  }
}

function submitPin() {
  if (pinInput.value.length >= 4) {
    pinError.value = "";
    loadDashboard(pinInput.value);
  }
}

onMounted(() => loadDashboard());
</script>

<template>
  <div class="min-h-screen bg-[var(--bg-base)] flex flex-col">
    <!-- Minimal header -->
    <div class="flex items-center justify-center px-4 py-3 border-b border-[var(--border)] bg-[var(--bg-surface)]">
      <div class="flex items-center gap-2">
        <img v-if="branding.logoUrl" :src="branding.logoUrl" :alt="branding.productName" class="h-6" />
        <span v-else class="text-sm font-bold text-[var(--primary)] tracking-widest">{{ branding.productName }}</span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <p class="text-sm text-[var(--text-muted)]">{{ t('pages.publicDashboard.loading') }}</p>
    </div>

    <!-- PIN required -->
    <div v-else-if="needsPin" class="flex-1 flex items-center justify-center">
      <div class="bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl p-8 shadow-2xl w-full max-w-sm">
        <h2 class="text-lg font-semibold text-[var(--text-primary)] mb-2">{{ t('pages.publicDashboard.protectedTitle') }}</h2>
        <p class="text-xs text-[var(--text-muted)] mb-4">{{ t('pages.publicDashboard.enterPin') }}</p>
        <input
          v-model="pinInput"
          type="password"
          maxlength="6"
          class="w-full px-4 py-3 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-center text-xl tracking-[0.5em] font-mono text-[var(--text-primary)]"
          placeholder="****"
          autofocus
          @keyup.enter="submitPin"
        />
        <div v-if="pinError" class="mt-2 text-xs text-red-400">{{ pinError }}</div>
        <button
          class="mt-4 w-full px-4 py-2 rounded-lg bg-[var(--primary)] text-black font-medium text-sm"
          :disabled="pinInput.length < 4"
          @click="submitPin"
        >Unlock</button>
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex-1 flex items-center justify-center">
      <div class="text-center">
        <p class="text-sm text-red-400">{{ error }}</p>
        <button class="mt-3 px-3 py-1.5 rounded-lg text-xs border border-[var(--border)] text-[var(--text-muted)]" @click="loadDashboard()">Retry</button>
      </div>
    </div>

    <!-- Dashboard content -->
    <div v-else-if="dashboard" class="flex-1 p-4">
      <h1 class="text-lg font-semibold text-[var(--text-primary)] mb-1">{{ dashboard.name }}</h1>
      <p v-if="dashboard.description" class="text-xs text-[var(--text-muted)] mb-4">{{ dashboard.description }}</p>

      <div v-if="!dashboard.widgets.length" class="text-center py-12">
        <p class="text-sm text-[var(--text-muted)]">{{ t('pages.publicDashboard.noWidgets') }}</p>
      </div>

      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="w in dashboard.widgets"
          :key="w.id"
          class="border border-[var(--border)] rounded-xl bg-[var(--bg-surface)] p-4"
        >
          <div class="text-xs font-medium text-[var(--text-primary)] mb-2">{{ w.label || w.variable_key || w.widget_type }}</div>
          <div class="text-2xl font-bold text-[var(--primary)] font-mono">
            {{ w.variable_key || '—' }}
          </div>
          <div class="text-[10px] text-[var(--text-muted)] mt-1">{{ w.widget_type }}{{ w.unit ? ` (${w.unit})` : '' }}</div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="px-4 py-2 border-t border-[var(--border)] text-center">
      <span class="text-[10px] text-[var(--text-muted)]">Powered by {{ branding.productName }}</span>
    </div>
  </div>
</template>
