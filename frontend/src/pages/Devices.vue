<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { apiFetch } from "../lib/api";

type Device = {
  id: number;
  device_uid: string;
  claimed: boolean;
  last_seen: string | null;
  online: boolean;
  health: "ok" | "stale" | "dead";
  last_seen_age_seconds: number | null;
};

const devices = ref<Device[]>([]);
const error = ref("");

let timer: number | null = null;

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

function fmtAge(seconds: number | null) {
  if (seconds === null || seconds === undefined) return "-";
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}

function healthClass(health: Device["health"]) {
  if (health === "ok") return "pill-ok";
  if (health === "stale") return "pill-warn";
  return "pill-bad";
}

onMounted(() => {
  load();
  timer = window.setInterval(load, 5000);
});

onUnmounted(() => {
  if (timer !== null) {
    window.clearInterval(timer);
    timer = null;
  }
});
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
          <th>Health</th>
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
          <td>
            <span :class="['pill', healthClass(d.health)]">
              {{ d.health }}
            </span>
          </td>
          <td>
            {{ fmtTime(d.last_seen) }}
            <span v-if="d.last_seen_age_seconds !== null">({{ fmtAge(d.last_seen_age_seconds) }})</span>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else>No devices.</div>
  </div>
</template>
