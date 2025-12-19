<script setup lang="ts">
import { ref } from "vue";
import { apiFetch, setToken } from "../lib/api";

const deviceUid = ref("");
const startResult = ref<any | null>(null);
const startError = ref<string | null>(null);

const confirming = ref(false);
const confirmResult = ref<any | null>(null);
const confirmError = ref<string | null>(null);

async function startPairing() {
  startError.value = null;
  confirmError.value = null;
  confirmResult.value = null;
  startResult.value = null;

  const uid = deviceUid.value.trim();
  if (!uid) {
    startError.value = "device_uid required";
    return;
  }

  try {
    // IMPORTANT: path must already include /api/v1 in VITE_API_BASE usage.
    // If your apiFetch expects a full URL, pass full URL. If it expects relative, keep relative.
    // Your current apiFetch takes "path" directly -> we use absolute via import.meta.env.
    const base = import.meta.env.VITE_API_BASE;
    startResult.value = await apiFetch(`${base}/pairing/start`, {
      method: "POST",
      body: JSON.stringify({ device_uid: uid }),
    });
  } catch (e: any) {
    startError.value = e?.message || String(e);
  }
}

async function confirmPairing() {
  confirmError.value = null;
  confirmResult.value = null;

  if (!startResult.value?.pairing_code) {
    confirmError.value = "no pairing_code (run Start first)";
    return;
  }

  confirming.value = true;
  try {
    const base = import.meta.env.VITE_API_BASE;
    confirmResult.value = await apiFetch(`${base}/pairing/confirm`, {
      method: "POST",
      body: JSON.stringify({
        device_uid: deviceUid.value.trim(),
        pairing_code: startResult.value.pairing_code,
      }),
    });
    if (confirmResult.value?.device_token) {
      setToken(confirmResult.value.device_token);
    }
  } catch (e: any) {
    confirmError.value = e?.message || String(e);
  } finally {
    confirming.value = false;
  }
}

async function copyToken() {
  const token = confirmResult.value?.device_token;
  if (!token) return;
  await navigator.clipboard.writeText(token);
  alert("device_token copied");
}
</script>

<template>
  <div style="max-width: 900px; margin: 0 auto; padding: 24px;">
    <h2>Pairing</h2>

    <div style="margin-top: 16px; padding: 16px; border: 1px solid #ddd; border-radius: 12px;">
      <h3>Pairing Start</h3>

      <div style="display: flex; gap: 12px; align-items: center; margin-top: 12px;">
        <input
          v-model="deviceUid"
          placeholder="device_uid"
          style="flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 8px;"
        />
        <button @click="startPairing" style="padding: 10px 16px;">
          Start
        </button>
      </div>

      <div v-if="startError" style="margin-top: 12px; color: #b00020;">
        {{ startError }}
      </div>

      <div v-if="startResult" style="margin-top: 12px;">
        <div><b>pairing_code:</b> {{ startResult.pairing_code }}</div>
        <div><b>expires_at:</b> {{ startResult.expires_at }}</div>
      </div>
    </div>

    <div
      v-if="startResult?.pairing_code"
      style="margin-top: 16px; padding: 16px; border: 1px solid #ddd; border-radius: 12px;"
    >
      <h3>Pairing Confirm</h3>

      <div style="display: flex; gap: 12px; align-items: center; margin-top: 12px;">
        <button @click="confirmPairing" :disabled="confirming" style="padding: 10px 16px;">
          {{ confirming ? "Confirming..." : "Confirm" }}
        </button>
      </div>

      <div v-if="confirmError" style="margin-top: 12px; color: #b00020; white-space: pre-wrap;">
        {{ confirmError }}
      </div>

      <div v-if="confirmResult" style="margin-top: 12px;">
        <div><b>device_id:</b> {{ confirmResult.device_id }}</div>
        <div><b>owner_user_id:</b> {{ confirmResult.owner_user_id }}</div>

        <div style="margin-top: 12px;">
          <div style="display:flex; justify-content: space-between; align-items: center; gap: 12px;">
            <b>device_token:</b>
            <button @click="copyToken" style="padding: 6px 10px;">Copy</button>
          </div>
          <pre style="margin-top: 8px; padding: 12px; background: #f6f6f6; border-radius: 10px; overflow:auto;">{{ confirmResult.device_token }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>
