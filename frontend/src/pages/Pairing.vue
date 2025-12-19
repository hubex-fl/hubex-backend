<script setup lang="ts">
import { ref } from "vue";
import { apiFetch } from "../lib/api";

const deviceUid = ref("");
const pairing = ref<any>(null);
const error = ref("");

async function onSubmit() {
  error.value = "";
  pairing.value = null;
  try {
    pairing.value = await apiFetch("/api/v1/pairing/start", {
      method: "POST",
      body: JSON.stringify({ device_uid: deviceUid.value }),
    });
  } catch (err: any) {
    error.value = err?.message || "Pairing failed";
  }
}
</script>

<template>
  <div class="card">
    <h2>Pairing Start</h2>
    <div class="row">
      <input v-model="deviceUid" class="input" placeholder="device_uid" />
      <button class="btn" @click="onSubmit">Start</button>
    </div>
    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="pairing" style="margin-top: 12px;">
      <div><strong>pairing_code:</strong> {{ pairing.pairing_code }}</div>
      <div><strong>expires_at:</strong> {{ pairing.expires_at }}</div>
    </div>
  </div>
</template>
