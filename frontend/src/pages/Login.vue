<script setup lang="ts">
import { ref } from "vue";
import { apiFetch, setToken } from "../lib/api";
import { useRouter } from "vue-router";

const email = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);
const router = useRouter();

async function onSubmit() {
  error.value = "";
  loading.value = true;
  try {
    const res = await apiFetch<{ access_token: string }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: email.value, password: password.value }),
    });
    setToken(res.access_token);
    router.push("/devices");
  } catch (err: any) {
    error.value = err?.message || "Login failed";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl p-8 shadow-2xl">
    <h2 class="text-lg font-semibold text-[var(--text-primary)] mb-6">Sign in</h2>

    <div class="flex flex-col gap-4">
      <div class="flex flex-col gap-1">
        <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">Email</label>
        <input
          v-model="email"
          class="input w-full"
          placeholder="you@example.com"
          type="email"
          autocomplete="email"
          @keyup.enter="onSubmit"
        />
      </div>
      <div class="flex flex-col gap-1">
        <label class="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">Password</label>
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
      {{ loading ? "Signing in…" : "Sign in" }}
    </button>
  </div>
</template>
