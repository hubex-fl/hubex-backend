<script setup lang="ts">
import { computed, ref } from "vue";
import { apiFetch, clearToken, getToken, setToken } from "../lib/api";
import { refreshCapabilities, useCapabilities } from "../lib/capabilities";
import { useAbortHandle } from "../lib/abort";

const tokenInput = ref("");
const email = ref("");
const password = ref("");
const error = ref("");
const loginBusy = ref(false);

const caps = useCapabilities();
const { signal } = useAbortHandle();

const status = computed(() => (getToken() ? "present" : "missing"));
const capList = computed(() => Array.from(caps.caps).sort().join(", "));

function saveToken() {
  const token = tokenInput.value.trim();
  if (!token) {
    return;
  }
  setToken(token);
  tokenInput.value = "";
  refreshCapabilities(signal);
}

function removeToken() {
  clearToken();
  refreshCapabilities(signal);
}

async function login() {
  error.value = "";
  if (!email.value.trim() || !password.value) {
    error.value = "Email and password are required.";
    return;
  }
  loginBusy.value = true;
  try {
    const res = await apiFetch<{ access_token: string }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: email.value.trim(), password: password.value }),
    });
    setToken(res.access_token);
    password.value = "";
    refreshCapabilities(signal);
  } catch (err: any) {
    error.value = err?.message || "Login failed.";
  } finally {
    loginBusy.value = false;
  }
}
</script>

<template>
  <div class="page">
    <h2>Auth (local only)</h2>
    <p class="muted">Token status: {{ status }}</p>

    <div class="form-row">
      <input
        v-model="tokenInput"
        class="input"
        placeholder="Paste JWT token"
      />
      <button class="btn" @click="saveToken">Save</button>
      <button class="btn secondary" @click="removeToken">Clear</button>
    </div>

    <div class="card" style="margin-top: 16px;">
      <h3>Login</h3>
      <div class="row">
        <input v-model="email" class="input" placeholder="email" />
        <input v-model="password" class="input" placeholder="password" type="password" />
      </div>
      <div class="row" style="margin-top: 12px;">
        <button class="btn" :disabled="loginBusy" @click="login">
          {{ loginBusy ? "Signing in..." : "Sign in" }}
        </button>
      </div>
      <div v-if="error" class="error" style="margin-top: 8px;">{{ error }}</div>
    </div>

    <div class="muted" style="margin-top: 12px;">
      Capabilities: {{ caps.status }}<span v-if="capList"> ({{ capList }})</span>
    </div>
  </div>
</template>
