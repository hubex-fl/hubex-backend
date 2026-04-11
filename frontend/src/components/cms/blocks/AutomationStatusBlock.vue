<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";
import { useI18n } from "vue-i18n";

type Props = {
  automation_id?: number;
  show_last_fire?: boolean;
  refresh_ms?: number;
};

const props = defineProps<{ props: Props }>();
const { t } = useI18n();

type Automation = {
  id: number;
  name: string;
  enabled: boolean;
  last_fired_at?: string | null;
  fire_count?: number;
};

const data = ref<Automation | null>(null);
const loading = ref(true);
let timer: ReturnType<typeof setInterval> | null = null;

async function load() {
  if (!props.props.automation_id) {
    loading.value = false;
    return;
  }
  try {
    const res = await fetch(`/api/v1/automations/public/${props.props.automation_id}`);
    if (!res.ok) throw new Error();
    data.value = await res.json();
  } catch {
    // ignore
  } finally {
    loading.value = false;
  }
}

function formatDate(s?: string | null) {
  if (!s) return t('cms.components.blocks.automationStatus.never');
  try { return new Date(s).toLocaleString(); } catch { return s; }
}

onMounted(() => {
  load();
  const ms = Math.max(5000, props.props.refresh_ms ?? 15000);
  timer = setInterval(load, ms);
});
onBeforeUnmount(() => { if (timer) clearInterval(timer); });
</script>

<template>
  <div class="auto-block">
    <div v-if="loading" class="loading">{{ t('cms.components.blocks.automationStatus.loading') }}</div>
    <div v-else-if="!data" class="empty">{{ t('cms.components.blocks.automationStatus.notFound') }}</div>
    <div v-else class="body">
      <div class="head">
        <div class="name">{{ data.name }}</div>
        <div class="status" :class="{ enabled: data.enabled }">
          {{ data.enabled ? t('cms.components.blocks.automationStatus.enabled') : t('cms.components.blocks.automationStatus.disabled') }}
        </div>
      </div>
      <div v-if="props.props.show_last_fire !== false" class="last">
        {{ t('cms.components.blocks.automationStatus.lastFired') }} <strong>{{ formatDate(data.last_fired_at) }}</strong>
        <span v-if="typeof data.fire_count === 'number'"> · {{ t('cms.components.blocks.automationStatus.runs', { n: data.fire_count }) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auto-block {
  max-width: 520px;
  margin: 16px auto;
  padding: 20px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
}
.loading, .empty { color: #71717A; text-align: center; padding: 16px 0; }
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.name { color: #F5F5F5; font-weight: 600; font-size: 16px; }
.status {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  background: rgba(255,255,255,0.08);
  color: #A1A1AA;
}
.status.enabled {
  background: rgba(45,212,191,0.15);
  color: #2DD4BF;
}
.last {
  color: #A1A1AA;
  font-size: 13px;
}
.last strong { color: #E5E5E5; }
</style>
