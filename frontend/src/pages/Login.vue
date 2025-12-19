<script setup lang="ts">
import { ref } from "vue";
import { apiFetch, setToken } from "../lib/api";
import { useRouter } from "vue-router";

const email = ref("");
const password = ref("");
const error = ref("");
const router = useRouter();

async function onSubmit() {
  error.value = "";
  try {
    const res = await apiFetch<{ access_token: string }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: email.value, password: password.value }),
    });
    setToken(res.access_token);
    router.push("/devices");
  } catch (err: any) {
    error.value = err?.message || "Login failed";
  }
}
</script>

<template>
  <div class="card">
    <h2>Login</h2>
    <div class="row">
      <input v-model="email" class="input" placeholder="email" />
      <input v-model="password" class="input" placeholder="password" type="password" />
    </div>
    <div class="row" style="margin-top: 12px;">
      <button class="btn" @click="onSubmit">Sign in</button>
    </div>
    <div v-if="error" class="error">{{ error }}</div>
  </div>
</template>
