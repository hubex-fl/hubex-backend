<script setup lang="ts">
import { computed, ref } from "vue";
import { clearToken, getToken, setToken } from "../lib/api";
import { refreshCapabilities, useCapabilities } from "../lib/capabilities";
import { useAbortHandle } from "../lib/abort";

const tokenInput = ref("");
const caps = useCapabilities();
const { signal } = useAbortHandle();

const status = computed(() => (getToken() ? "present" : "missing"));

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

    <div class="muted">Capabilities: {{ caps.status }}</div>
  </div>
</template>
