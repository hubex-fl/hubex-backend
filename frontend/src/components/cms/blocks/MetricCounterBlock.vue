<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";

type Props = {
  metric?: string;
  label?: string;
  icon?: string;
  color?: string;
  refresh_ms?: number;
};

const props = defineProps<{ props: Props }>();

const value = ref<string | number>("—");
const loading = ref(true);
let timer: ReturnType<typeof setInterval> | null = null;

async function load() {
  if (!props.props.metric) {
    loading.value = false;
    return;
  }
  try {
    const res = await fetch(`/api/v1/metrics/public/${encodeURIComponent(props.props.metric)}`);
    if (!res.ok) throw new Error();
    const data = await res.json();
    value.value = data.value ?? "—";
  } catch {
    // keep old value
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
  <div class="metric-block">
    <div v-if="props.props.icon" class="icon">{{ props.props.icon }}</div>
    <div class="body">
      <div class="value" :style="{ color: props.props.color || '#2DD4BF' }">
        {{ value }}
      </div>
      <div class="label">{{ props.props.label || props.props.metric }}</div>
    </div>
  </div>
</template>

<style scoped>
.metric-block {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  max-width: 360px;
  margin: 16px auto;
}
.icon { font-size: 36px; }
.value {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 36px;
  font-weight: 700;
  line-height: 1.1;
}
.label {
  color: #A1A1AA;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-top: 4px;
}
</style>
