<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from "vue";
import { useI18n } from "vue-i18n";

type Props = {
  key?: string;
  device_uid?: string;
  label?: string;
  unit?: string;
  decimals?: number;
  refresh_ms?: number;
};

const props = defineProps<{ props: Props }>();
const { t } = useI18n();

const current = ref<string | number | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
let timer: ReturnType<typeof setInterval> | null = null;

const displayValue = computed(() => {
  if (current.value === null || current.value === undefined) return "—";
  const n = Number(current.value);
  if (Number.isFinite(n)) {
    const d = props.props.decimals;
    if (typeof d === "number" && d >= 0) return n.toFixed(d);
    return n.toString();
  }
  return String(current.value);
});

const displayLabel = computed(
  () => props.props.label || props.props.key || t('cms.components.blocks.variableValue.defaultLabel')
);

async function fetchValue() {
  const key = props.props.key;
  if (!key) {
    loading.value = false;
    error.value = t('cms.components.blocks.variableValue.noKey');
    return;
  }
  try {
    // Use public endpoint — works without auth for published variables
    const qs = new URLSearchParams({ key });
    if (props.props.device_uid) qs.set("device_uid", props.props.device_uid);
    const res = await fetch(`/api/v1/variables/public/value?${qs.toString()}`);
    if (!res.ok) {
      throw new Error(`${res.status}`);
    }
    const data = await res.json();
    current.value = data.value ?? data.value_json ?? null;
    error.value = null;
  } catch (e: any) {
    error.value = "—";
  } finally {
    loading.value = false;
  }
}

function start() {
  fetchValue();
  const ms = Math.max(1000, props.props.refresh_ms ?? 5000);
  timer = setInterval(fetchValue, ms);
}

function stop() {
  if (timer) { clearInterval(timer); timer = null; }
}

onMounted(start);
onBeforeUnmount(stop);
watch(() => props.props, () => { stop(); start(); }, { deep: true });
</script>

<template>
  <div class="var-block">
    <div class="var-value">{{ displayValue }}<span v-if="props.props.unit" class="var-unit">{{ props.props.unit }}</span></div>
    <div class="var-label">{{ displayLabel }}</div>
  </div>
</template>

<style scoped>
.var-block {
  text-align: center;
  padding: 20px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  max-width: 360px;
  margin: 16px auto;
}
.var-value {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 44px;
  color: #F5A623;
  font-weight: 700;
  line-height: 1.1;
}
.var-unit {
  font-size: 0.5em;
  color: #A1A1AA;
  margin-left: 4px;
}
.var-label {
  color: #A1A1AA;
  margin-top: 6px;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
</style>
