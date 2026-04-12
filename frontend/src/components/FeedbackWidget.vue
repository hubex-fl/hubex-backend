<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";

const { t } = useI18n();
const toast = useToastStore();
const open = ref(false);
const type = ref<"bug" | "feature" | "other">("bug");
const message = ref("");
const sending = ref(false);

// Track recent navigation for context
const recentPages: string[] = [];
const MAX_PAGES = 10;

function trackPage() {
  const path = window.location.pathname;
  if (recentPages[recentPages.length - 1] !== path) {
    recentPages.push(path);
    if (recentPages.length > MAX_PAGES) recentPages.shift();
  }
}
// Track on load and on history change
trackPage();
if (typeof window !== "undefined") {
  const origPushState = history.pushState;
  history.pushState = function (...args: any[]) {
    origPushState.apply(this, args);
    trackPage();
  };
  window.addEventListener("popstate", trackPage);
}

/** Collect silent metadata for analysis — user doesn't see this */
function collectMetadata(): Record<string, unknown> {
  return {
    page: window.location.pathname + window.location.search,
    recentPages: [...recentPages],
    viewport: `${window.innerWidth}x${window.innerHeight}`,
    userAgent: navigator.userAgent,
    language: navigator.language,
    theme: document.documentElement.getAttribute("data-theme") || "unknown",
    timestamp: new Date().toISOString(),
    sessionDuration: Math.round(performance.now() / 1000),
    referrer: document.referrer || undefined,
    // Collect recent console errors if available
    consoleErrors: (window as any).__hubex_console_errors?.slice(-5) || [],
  };
}

async function submit() {
  if (!message.value.trim()) return;
  sending.value = true;
  try {
    await apiFetch("/api/v1/feedback", {
      method: "POST",
      body: JSON.stringify({
        type: type.value,
        message: message.value.trim(),
        metadata: collectMetadata(),
      }),
    });
    toast.addToast(t("feedback.sent"), "success");
    message.value = "";
    open.value = false;
  } catch {
    // Fallback: try the events endpoint
    try {
      await apiFetch("/api/v1/events/emit", {
        method: "POST",
        body: JSON.stringify({
          type: `feedback.${type.value}`,
          payload: {
            message: message.value.trim(),
            ...collectMetadata(),
          },
        }),
      });
      toast.addToast(t("feedback.sent"), "success");
      message.value = "";
      open.value = false;
    } catch {
      toast.addToast(t("feedback.error"), "error");
    }
  } finally {
    sending.value = false;
  }
}

// Capture console errors for feedback context
if (typeof window !== "undefined") {
  (window as any).__hubex_console_errors = [];
  const origError = console.error;
  console.error = function (...args: any[]) {
    const errors = (window as any).__hubex_console_errors;
    errors.push(args.map(String).join(" ").slice(0, 200));
    if (errors.length > 10) errors.shift();
    origError.apply(console, args);
  };
}
</script>

<template>
  <!-- Feedback Button (bottom-right) -->
  <button
    v-if="!open"
    class="fixed bottom-4 right-4 z-40 px-3 py-2 rounded-full bg-[var(--primary)] text-black text-xs font-medium shadow-lg hover:bg-[var(--primary-hover)] transition-all"
    @click="open = true"
    data-tour="feedback-button"
  >
    💬 {{ t('feedback.button') }}
  </button>

  <!-- Feedback Panel -->
  <Teleport to="body">
    <div v-if="open" class="fixed bottom-4 right-4 z-50 w-80 bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl shadow-2xl p-4 space-y-3">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('feedback.title') }}</h3>
        <button class="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]" @click="open = false">×</button>
      </div>

      <div class="flex gap-1.5">
        <button
          v-for="btn in [['bug', t('feedback.typeBug')], ['feature', t('feedback.typeFeature')], ['other', t('feedback.typeOther')]]"
          :key="btn[0]"
          :class="['px-2.5 py-1 rounded-lg text-[10px] font-medium transition-colors', type === btn[0] ? 'bg-[var(--primary)]/15 text-[var(--primary)] border border-[var(--primary)]/30' : 'text-[var(--text-muted)] border border-[var(--border)]']"
          @click="type = btn[0] as any"
        >{{ btn[1] }}</button>
      </div>

      <textarea
        v-model="message"
        rows="3"
        class="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)] resize-none"
        :placeholder="t('feedback.placeholder')"
      />

      <p class="text-[8px] text-[var(--text-muted)] leading-tight">
        {{ t('feedback.metaHint') }}
      </p>

      <div class="flex justify-end gap-2">
        <button class="text-xs text-[var(--text-muted)]" @click="open = false">{{ t('common.cancel') }}</button>
        <button
          :disabled="sending || !message.trim()"
          class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black disabled:opacity-50"
          @click="submit"
        >{{ sending ? t('feedback.sending') : t('feedback.send') }}</button>
      </div>
    </div>
  </Teleport>
</template>
