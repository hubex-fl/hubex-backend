<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";

type Props = {
  device_uid?: string;
  show_status?: boolean;
  show_variables?: boolean;
  refresh_ms?: number;
};

const props = defineProps<{ props: Props }>();

type DeviceData = {
  name: string;
  device_uid: string;
  device_type?: string;
  online?: boolean;
  variables?: { key: string; value: any; unit?: string }[];
};

const data = ref<DeviceData | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
let timer: ReturnType<typeof setInterval> | null = null;

async function load() {
  const uid = props.props.device_uid;
  if (!uid) {
    loading.value = false;
    error.value = "No device";
    return;
  }
  try {
    const res = await fetch(`/api/v1/devices/public/${encodeURIComponent(uid)}`);
    if (!res.ok) throw new Error(`${res.status}`);
    data.value = await res.json();
    error.value = null;
  } catch (e: any) {
    error.value = "Failed to load device";
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  load();
  const ms = Math.max(3000, props.props.refresh_ms ?? 10000);
  timer = setInterval(load, ms);
});
onBeforeUnmount(() => { if (timer) clearInterval(timer); });
</script>

<template>
  <div class="dev-card">
    <div v-if="loading" class="loading">Loading device…</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="data" class="body">
      <div class="head">
        <div class="name">{{ data.name || data.device_uid }}</div>
        <div v-if="props.props.show_status !== false" class="status" :class="{ online: data.online }">
          {{ data.online ? 'online' : 'offline' }}
        </div>
      </div>
      <div class="uid">{{ data.device_uid }}</div>
      <div v-if="props.props.show_variables !== false && data.variables?.length" class="vars">
        <div v-for="v in data.variables" :key="v.key" class="var-row">
          <span class="var-key">{{ v.key }}</span>
          <span class="var-val">{{ v.value }}<span v-if="v.unit" class="unit">{{ v.unit }}</span></span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dev-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 20px;
  max-width: 520px;
  margin: 16px auto;
}
.loading, .error { color: #71717A; text-align: center; padding: 24px 0; }
.error { color: #ef4444; }
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}
.name { color: #F5F5F5; font-size: 18px; font-weight: 600; }
.status {
  font-size: 11px;
  text-transform: uppercase;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255,255,255,0.08);
  color: #A1A1AA;
}
.status.online {
  background: rgba(45,212,191,0.15);
  color: #2DD4BF;
}
.uid {
  color: #71717A;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  margin-bottom: 12px;
}
.vars {
  border-top: 1px solid rgba(255,255,255,0.06);
  padding-top: 12px;
}
.var-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 14px;
}
.var-key { color: #A1A1AA; }
.var-val { color: #F5A623; font-family: 'IBM Plex Mono', monospace; font-weight: 600; }
.unit { color: #71717A; margin-left: 4px; font-weight: 400; font-size: 0.85em; }
</style>
