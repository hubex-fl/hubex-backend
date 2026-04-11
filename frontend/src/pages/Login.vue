<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { apiFetch, getToken } from "../lib/api";
import { useI18n } from "vue-i18n";

const { t } = useI18n();
const email = ref("");
const password = ref("");
const mfaCode = ref("");
const error = ref("");
const loading = ref(false);
const router = useRouter();
const auth = useAuthStore();

// Sprint 8 R1-F01 — auto-redirect away from /login when already
// authenticated. Before: navigating to /login with a valid token
// still rendered the login form — confusing UX. Now: if a token
// is present at mount time, redirect immediately to the dashboard.
onMounted(() => {
  if (getToken()) {
    router.replace("/");
  }
});

async function onSubmit() {
  error.value = "";
  loading.value = true;
  try {
    const result = await auth.login(email.value, password.value);
    if (result === "ok") {
      router.push("/devices");
    }
    // "mfa_required" — UI switches automatically via auth.mfaPending
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Login failed";
    if (msg.includes("429") || msg.toLowerCase().includes("rate") || msg.toLowerCase().includes("too many")) {
      error.value = t('pages.login.tooManyAttempts');
    } else {
      error.value = msg;
    }
  } finally {
    loading.value = false;
  }
}

async function handleRegister() {
  if (!email.value || !password.value) { error.value = t('auth.enterEmailPassword'); return; }
  error.value = "";
  loading.value = true;
  try {
    await apiFetch("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email: email.value, password: password.value }),
    });
    // Auto-login after register
    const result = await auth.login(email.value, password.value);
    if (result === "ok") router.push("/");
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('auth.registerFailed');
  } finally {
    loading.value = false;
  }
}

async function onMfaSubmit() {
  error.value = "";
  loading.value = true;
  try {
    await auth.verifyMfa(mfaCode.value);
    router.push("/devices");
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('auth.invalidCode');
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl p-8 shadow-2xl">
    <!-- MFA Step -->
    <template v-if="auth.mfaPending">
      <h2 class="text-lg font-semibold text-[var(--text-primary)] mb-2">{{ t('pages.login.twoFactor') }}</h2>
      <p class="text-xs text-[var(--text-muted)] mb-6">{{ t('pages.login.enterCode') }}</p>

      <div class="flex flex-col gap-4">
        <div class="flex flex-col gap-1">
          <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">Code</label>
          <input
            v-model="mfaCode"
            class="input w-full text-center text-lg tracking-[0.5em] font-mono"
            placeholder="000000"
            type="text"
            maxlength="8"
            autocomplete="one-time-code"
            @keyup.enter="onMfaSubmit"
          />
          <p class="text-[10px] text-[var(--text-muted)] mt-1">{{ t('auth.orRecoveryCode') }}</p>
        </div>
      </div>

      <div v-if="error" class="mt-4 px-3 py-2 rounded-lg bg-[var(--status-bad-bg)] border border-[var(--status-bad)]/30 text-sm text-[var(--status-bad)]">
        {{ error }}
      </div>

      <button
        class="btn mt-6 w-full flex items-center justify-center gap-2"
        :disabled="loading || mfaCode.length < 6"
        @click="onMfaSubmit"
      >
        {{ loading ? t('auth.verifying') : t('mfa.verify') }}
      </button>
    </template>

    <!-- Login Step -->
    <template v-else>
      <h2 class="text-lg font-semibold text-[var(--text-primary)] mb-6">{{ t('auth.signIn') }}</h2>

      <div class="flex flex-col gap-4">
        <div class="flex flex-col gap-1">
          <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ t('auth.email') }}</label>
          <input
            v-model="email"
            class="input w-full"
            :placeholder="t('auth.emailPlaceholder')"
            type="email"
            autocomplete="email"
            @keyup.enter="onSubmit"
          />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{{ t('auth.password') }}</label>
          <input
            v-model="password"
            class="input w-full"
            placeholder="••••••••"
            type="password"
            autocomplete="current-password"
            @keyup.enter="onSubmit"
          />
        </div>
      </div>

      <div v-if="error" class="mt-4 px-3 py-2 rounded-lg bg-[var(--status-bad-bg)] border border-[var(--status-bad)]/30 text-sm text-[var(--status-bad)]">
        {{ error }}
      </div>

      <button
        class="btn mt-6 w-full flex items-center justify-center gap-2"
        :disabled="loading"
        @click="onSubmit"
      >
        <svg v-if="loading" class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
        {{ loading ? t('auth.signingIn') : t('auth.signIn') }}
      </button>
      <p class="mt-4 text-center text-xs text-[var(--text-muted)]">
        {{ t('auth.noAccountYet') }}
        <button class="text-[var(--primary)] hover:underline" @click="handleRegister">{{ t('auth.createOne') }}</button>
      </p>
      <!-- Sprint 8 R4 NU-F02 fix: brand-new visitors used to land on a bare
           login form with zero context about what HubEx is. A subtle link
           to the marketing page gives them an obvious way out. -->
      <p class="mt-6 text-center text-xs text-[var(--text-muted)]">
        <router-link to="/landing" class="hover:text-[var(--text-secondary)] transition-colors inline-flex items-center gap-1">
          <svg class="h-3 w-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z" />
          </svg>
          {{ t('auth.whatIsHubex') }} →
        </router-link>
      </p>
    </template>
  </div>
</template>
