<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";
import { apiFetch } from "../lib/api";

const route = useRoute();
const deviceId = route.params.id as string;

type TelemetryItem = {
  id: number;
  created_at: string;
  event_type: string;
  payload: Record<string, any>;
};

const telemetry = ref<TelemetryItem[]>([]);
const telemetryError = ref<string | null>(null);

let timer: number | null = null;

async function loadTelemetry() {
  telemetryError.value = null;
  try {
    telemetry.value = await apiFetch<TelemetryItem[]>(
      `/api/v1/devices/${deviceId}/telemetry/recent?limit=5`
    );
  } catch (e: any) {
    telemetryError.value = e?.message || String(e);
  }
}

function fmtTime(iso: string) {
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

onMounted(async () => {
  await loadTelemetry();
  timer = window.setInterval(loadTelemetry, 5000);
});

onUnmounted(() => {
  if (timer) window.clearInterval(timer);
});
</script>

<template>
  <div class="card">
    <h2>Device Telemetry (last 5)</h2>

    <div v-if="telemetryError" class="error">{{ telemetryError }}</div>

    <table v-else class="table">
      <thead>
        <tr>
          <th>Time</th>
          <th>Temperature</th>
          <th>Humidity</th>
          <th>Event</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="t in telemetry" :key="t.id">
          <td>{{ fmtTime(t.created_at) }}</td>
          <td>{{ t.payload?.temperature ?? "—" }}</td>
          <td>{{ t.payload?.humidity ?? "—" }}</td>
          <td>{{ t.event_type }}</td>
        </tr>
        <tr v-if="telemetry.length === 0">
          <td colspan="4">No telemetry yet</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>