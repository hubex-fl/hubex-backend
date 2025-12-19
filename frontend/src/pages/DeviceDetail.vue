<script setup lang="ts">
import { onMounted, ref } from "vue";
import { apiFetch } from "../lib/api";
import { useRoute } from "vue-router";

const route = useRoute();
const deviceId = route.params.id;
const device = ref<any>(null);
const error = ref("");

async function load() {
  error.value = "";
  try {
    device.value = await apiFetch(`/api/v1/devices/${deviceId}`);
  } catch (err: any) {
    error.value = err?.message || "Failed to load device";
  }
}

onMounted(load);
</script>

<template>
  <div class="card">
    <h2>Device Detail</h2>
    <div v-if="error" class="error">{{ error }}</div>
    <pre v-else>{{ device }}</pre>
  </div>
</template>
