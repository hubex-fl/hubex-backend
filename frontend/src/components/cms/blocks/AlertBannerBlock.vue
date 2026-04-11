<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useI18n } from "vue-i18n";

type Severity = "info" | "warning" | "critical";
type Props = {
  severity_filter?: Severity | "all";
  max_items?: number;
  auto_hide_if_none?: boolean;
  refresh_ms?: number;
};

const props = defineProps<{ props: Props }>();
const { t } = useI18n();

type Alert = {
  id: number;
  severity: Severity;
  message?: string;
  rule_name?: string;
  fired_at?: string;
};

const alerts = ref<Alert[]>([]);
const loading = ref(true);
let timer: ReturnType<typeof setInterval> | null = null;

const filtered = computed(() => {
  const f = props.props.severity_filter ?? "all";
  const cap = Math.max(1, props.props.max_items ?? 3);
  let list = alerts.value;
  if (f !== "all") list = list.filter((a) => a.severity === f);
  return list.slice(0, cap);
});

const hidden = computed(
  () => props.props.auto_hide_if_none !== false && !loading.value && filtered.value.length === 0
);

async function load() {
  try {
    const res = await fetch("/api/v1/alerts/public/active");
    if (!res.ok) throw new Error();
    const data = await res.json();
    alerts.value = Array.isArray(data) ? data : data.items ?? [];
  } catch {
    // ignore — keep old data
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  load();
  const ms = Math.max(5000, props.props.refresh_ms ?? 15000);
  timer = setInterval(load, ms);
});
onBeforeUnmount(() => { if (timer) clearInterval(timer); });
</script>

<template>
  <div v-if="!hidden" class="alert-banner">
    <div v-if="loading && !filtered.length" class="loading">{{ t('cms.components.blocks.alertBanner.loading') }}</div>
    <div v-else-if="!filtered.length" class="empty">{{ t('cms.components.blocks.alertBanner.empty') }}</div>
    <div v-else class="list">
      <div
        v-for="a in filtered"
        :key="a.id"
        class="alert"
        :class="`sev-${a.severity}`"
      >
        <div class="sev-dot"></div>
        <div class="alert-body">
          <div class="rule">{{ a.rule_name || t('cms.components.blocks.alertBanner.fallbackRule', { id: a.id }) }}</div>
          <div v-if="a.message" class="msg">{{ a.message }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.alert-banner { max-width: 960px; margin: 16px auto; padding: 0 24px; }
.loading, .empty {
  color: #71717A;
  text-align: center;
  padding: 12px;
}
.list { display: flex; flex-direction: column; gap: 8px; }
.alert {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 14px 18px;
  border-radius: 10px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
}
.sev-critical { border-color: rgba(239,68,68,0.4); background: rgba(239,68,68,0.08); }
.sev-warning { border-color: rgba(245,166,35,0.4); background: rgba(245,166,35,0.08); }
.sev-info { border-color: rgba(45,212,191,0.4); background: rgba(45,212,191,0.08); }

.sev-dot {
  width: 10px; height: 10px; border-radius: 50%; margin-top: 6px; flex-shrink: 0;
}
.sev-critical .sev-dot { background: #ef4444; }
.sev-warning .sev-dot { background: #F5A623; }
.sev-info .sev-dot { background: #2DD4BF; }

.rule { color: #F5F5F5; font-weight: 600; }
.msg { color: #A1A1AA; font-size: 14px; margin-top: 2px; }
</style>
