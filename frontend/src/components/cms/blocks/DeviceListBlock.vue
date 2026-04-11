<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";

type Props = {
  filter?: "all" | "online" | "offline";
  columns?: number;
  show_type?: boolean;
};

const props = defineProps<{ props: Props }>();
const { t } = useI18n();

type Item = {
  device_uid: string;
  name: string;
  device_type?: string;
  online?: boolean;
};

const devices = ref<Item[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

const columns = computed(() => Math.max(1, Math.min(6, props.props.columns ?? 3)));
const filtered = computed(() => {
  const f = props.props.filter ?? "all";
  if (f === "online") return devices.value.filter((d) => d.online);
  if (f === "offline") return devices.value.filter((d) => !d.online);
  return devices.value;
});

async function load() {
  try {
    const res = await fetch("/api/v1/devices/public");
    if (!res.ok) throw new Error(`${res.status}`);
    const data = await res.json();
    devices.value = Array.isArray(data) ? data : data.items ?? [];
    error.value = null;
  } catch (e: any) {
    error.value = t('cms.components.blocks.deviceList.loadFailed');
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="dev-list">
    <div v-if="loading" class="loading">{{ t('cms.components.blocks.deviceList.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="!filtered.length" class="empty">{{ t('cms.components.blocks.deviceList.empty') }}</div>
    <div v-else class="grid" :style="{ gridTemplateColumns: `repeat(${columns}, 1fr)` }">
      <div v-for="d in filtered" :key="d.device_uid" class="item">
        <div class="item-head">
          <div class="item-name">{{ d.name || d.device_uid }}</div>
          <div class="dot" :class="{ online: d.online }"></div>
        </div>
        <div class="item-uid">{{ d.device_uid }}</div>
        <div v-if="props.props.show_type !== false && d.device_type" class="item-type">
          {{ d.device_type }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dev-list {
  max-width: 1200px;
  margin: 24px auto;
  padding: 0 24px;
}
.loading, .error, .empty { color: #71717A; text-align: center; padding: 32px; }
.error { color: #ef4444; }
.grid {
  display: grid;
  gap: 16px;
}
.item {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  padding: 16px;
}
.item-head { display: flex; justify-content: space-between; align-items: center; }
.item-name { color: #F5F5F5; font-weight: 600; }
.dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #71717A;
}
.dot.online { background: #2DD4BF; box-shadow: 0 0 8px rgba(45,212,191,0.6); }
.item-uid {
  font-family: 'IBM Plex Mono', monospace;
  color: #71717A;
  font-size: 11px;
  margin-top: 4px;
}
.item-type {
  display: inline-block;
  margin-top: 8px;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(245,166,35,0.15);
  color: #F5A623;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
</style>
