<script setup lang="ts">
import { onMounted, ref } from "vue";
import { apiFetch } from "../lib/api";

type Device = {
  id: number;
  device_uid: string;
  firmware_version?: string | null;
  owner_user_id?: number | null;
};

const devices = ref<Device[]>([]);
const error = ref("");

async function load() {
  error.value = "";
  try {
    devices.value = await apiFetch<Device[]>("/api/v1/devices");
  } catch (err: any) {
    error.value = err?.message || "Failed to load devices";
  }
}

onMounted(load);
</script>

<template>
  <div class="card">
    <h2>Devices</h2>
    <div v-if="error" class="error">{{ error }}</div>
    <ul v-if="devices.length">
      <li v-for="d in devices" :key="d.id">
        <router-link :to="`/devices/${d.id}`">
          {{ d.device_uid }} (id {{ d.id }})
        </router-link>
      </li>
    </ul>
    <div v-else>No devices.</div>
  </div>
</template>
