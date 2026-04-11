<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { usePreferencesStore } from "../stores/preferences";
import { apiFetch } from "../lib/api";
import BrandLogo from "./BrandLogo.vue";

const router = useRouter();
const prefs = usePreferencesStore();
const { t } = useI18n();
const loading = ref(false);
const demoLoading = ref(false);

// Sprint 8 R3 NU-F04 fix: welcome screen was 100% English on DE locale.
// Categories now route through welcomeScreen.categories.* i18n keys.
// Icons + colors stay here — they don't need translation.
const CATEGORY_ICONS = {
  hardware: "M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z",
  service: "M2.25 15a4.5 4.5 0 004.5 4.5H18a3.75 3.75 0 001.332-7.257 3 3 0 00-3.758-3.848 5.25 5.25 0 00-10.233 2.33A4.502 4.502 0 002.25 15z",
  bridge: "M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244",
  agent: "M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25A2.25 2.25 0 015.25 3h13.5A2.25 2.25 0 0121 5.25z",
} as const;

const CATEGORY_COLORS = {
  hardware: "var(--cat-hardware, #60a5fa)",
  service: "var(--cat-service, #a78bfa)",
  bridge: "var(--cat-bridge, #34d399)",
  agent: "var(--cat-agent, #fb923c)",
} as const;

const categories = computed(() =>
  (["hardware", "service", "bridge", "agent"] as const).map((key) => ({
    key,
    icon: CATEGORY_ICONS[key],
    label: t(`welcomeScreen.categories.${key}.label`),
    description: t(`welcomeScreen.categories.${key}.description`),
    color: CATEGORY_COLORS[key],
  })),
);

async function selectCategory(cat: string) {
  await dismiss();
  router.push(`/devices?wizard=open&category=${cat}`);
}

async function lookAround() {
  await dismiss();
}

async function loadDemoData() {
  demoLoading.value = true;
  try {
    await apiFetch("/api/v1/system/demo-data", { method: "POST" });
    await dismiss();
    router.push("/");
  } catch {
    // Still dismiss
    await dismiss();
  } finally {
    demoLoading.value = false;
  }
}

async function dismiss() {
  await prefs.update("onboarding_completed", true);
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[100] flex items-center justify-center bg-[var(--bg-base)]/95 backdrop-blur-md">
      <div class="w-full max-w-2xl mx-4">
        <!-- Logo + Welcome -->
        <div class="text-center mb-8">
          <div class="flex justify-center mb-4">
            <BrandLogo :size="48" :show-text="false" />
          </div>
          <h1 class="text-2xl font-bold text-[var(--text-primary)] mb-2">
            {{ t('welcomeScreen.title') }}
          </h1>
          <p class="text-[var(--text-muted)]">
            {{ t('welcomeScreen.subtitle') }}
          </p>
        </div>

        <!-- Category Cards -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          <button
            v-for="cat in categories"
            :key="cat.key"
            class="group flex flex-col items-center gap-2 p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] hover:border-[var(--primary)] hover:bg-[var(--bg-raised)] transition-all duration-200 cursor-pointer"
            @click="selectCategory(cat.key)"
          >
            <div
              class="w-10 h-10 rounded-lg flex items-center justify-center transition-colors"
              :style="{ backgroundColor: cat.color + '15' }"
            >
              <svg class="w-5 h-5" :style="{ color: cat.color }" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" :d="cat.icon" />
              </svg>
            </div>
            <span class="text-sm font-medium text-[var(--text-primary)]">{{ cat.label }}</span>
            <span class="text-[10px] text-[var(--text-muted)] text-center leading-tight">{{ cat.description }}</span>
          </button>
        </div>

        <!-- Divider -->
        <div class="flex items-center gap-4 mb-6">
          <div class="flex-1 h-px bg-[var(--border)]" />
          <span class="text-xs text-[var(--text-muted)]">{{ t('welcomeScreen.or') }}</span>
          <div class="flex-1 h-px bg-[var(--border)]" />
        </div>

        <!-- Alternative Actions -->
        <div class="flex items-center justify-center gap-6">
          <button
            class="text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors underline underline-offset-2"
            @click="lookAround"
          >
            {{ t('welcomeScreen.justLookAround') }} →
          </button>
          <button
            :disabled="demoLoading"
            class="text-sm text-[var(--primary)] hover:text-[var(--primary-hover)] transition-colors underline underline-offset-2 disabled:opacity-50"
            @click="loadDemoData"
          >
            {{ demoLoading ? t('welcomeScreen.loading') : t('welcomeScreen.loadDemoData') + ' →' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
