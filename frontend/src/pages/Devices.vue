<script setup lang="ts">
import { onMounted, ref } from "vue";
import { apiFetch } from "../lib/api";

type Device = {
  id: number;
  device_uid: string;
  claimed: boolean;
  last_seen: string | null;
  online: boolean;
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

function fmtTime(iso: string | null) {
  if (!iso) return "-";
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

onMounted(load);
</script>

<template>
  <div class="card">
    <h2>Devices</h2>
    <div v-if="error" class="error">{{ error }}</div>

    <table v-if="devices.length" class="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>UID</th>
          <th>Status</th>
          <th>Last seen</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="d in devices" :key="d.id">
          <td>{{ d.id }}</td>
          <td>
            <router-link :to="`/devices/${d.id}`">
              {{ d.device_uid }}
            </router-link>
          </td>
          <td>
            <span :class="['pill', d.online ? 'pill-ok' : 'pill-bad']">
              {{ d.online ? "online" : "offline" }}
            </span>
          </td>
          <td>{{ fmtTime(d.last_seen) }}</td>
        </tr>
      </tbody>
    </table>
    <div v-else>No devices.</div>
  </div>
</template>
