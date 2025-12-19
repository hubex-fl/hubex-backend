<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { apiFetch } from "../lib/api";

const route = useRoute();
const deviceId = route.params.id as string;

const telemetry = ref<any[]>([]);
const telemetryError = ref<string | null>(null);
let refreshId: number | undefined;

async function loadTelemetry() {
  telemetryError.value = null;
  try {
    telemetry.value = await apiFetch(
      `/api/v1/devices/${deviceId}/telemetry/recent?limit=5`
    );
  } catch (e: any) {
    telemetryError.value = e.message || String(e);
  }
}

onMounted(() => {
  loadTelemetry();
  refreshId = window.setInterval(loadTelemetry, 5000);
});

onBeforeUnmount(() => {
  if (refreshId !== undefined) {
    window.clearInterval(refreshId);
  }
});
</script>

<template>
  <div class="card">
    <h2>Device Telemetry (last 5)</h2>

    <div v-if="telemetryError" class="error">
      {{ telemetryError }}
    </div>

    <div v-else-if="telemetry.length === 0">
      No telemetry yet
    </div>

    <table v-else class="table">
      <thead>
        <tr>
          <th>Time</th>
          <th>Temperature</th>
          <th>Humidity</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="t in telemetry" :key="t.id">
          <td>{{ new Date(t.received_at).toLocaleString() }}</td>
          <td>{{ t.payload?.temperature ?? "-" }} °C</td>
          <td>{{ t.payload?.humidity ?? "-" }} %</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
