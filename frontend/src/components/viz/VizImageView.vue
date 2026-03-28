<template>
  <div class="viz-image">
    <div v-if="!imageUrl" class="img-placeholder">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#484f58" stroke-width="1.5">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
        <circle cx="8.5" cy="8.5" r="1.5"/>
        <polyline points="21 15 16 10 5 21"/>
      </svg>
      <span>No image URL</span>
    </div>
    <template v-else>
      <img
        :src="imageUrl"
        :key="refreshKey"
        :style="{ maxHeight: `${maxHeight}px` }"
        class="viz-img"
        :alt="label"
        @error="onError"
        @load="onLoad"
      />
      <div v-if="imgError" class="img-error">
        <span>Could not load image</span>
        <span class="img-url">{{ imageUrl }}</span>
      </div>
      <div class="img-footer" v-if="autoRefresh && refreshInterval">
        <span class="img-badge">↻ {{ refreshInterval }}s</span>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";

const props = withDefaults(defineProps<{
  currentValue?: unknown;  // URL string
  label?: string;
  maxHeight?: number;
  autoRefresh?: boolean;
  refreshInterval?: number; // seconds
}>(), {
  currentValue: null,
  label: "image",
  maxHeight: 300,
  autoRefresh: false,
  refreshInterval: 30,
});

const refreshKey = ref(0);
const imgError   = ref(false);

const imageUrl = computed(() => {
  const v = props.currentValue;
  if (!v) return null;
  const s = String(v).trim();
  return s.startsWith("http") ? s : null;
});

function onError() { imgError.value = true; }
function onLoad()  { imgError.value = false; }

watch(imageUrl, () => { imgError.value = false; });

let timer: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  if (props.autoRefresh && props.refreshInterval) {
    timer = setInterval(() => { refreshKey.value++; }, props.refreshInterval * 1000);
  }
});
onUnmounted(() => { if (timer) clearInterval(timer); });
</script>

<style scoped>
.viz-image { width: 100%; }
.img-placeholder {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 8px; color: #484f58; font-size: 12px; padding: 24px;
  background: #0d1117; border-radius: 4px;
}
.viz-img {
  display: block; width: 100%; height: auto;
  border-radius: 4px; object-fit: contain;
  background: #0d1117;
}
.img-error {
  display: flex; flex-direction: column; gap: 4px;
  color: #f85149; font-size: 12px; padding: 8px;
}
.img-url { color: #8b949e; font-size: 10px; font-family: monospace; word-break: break-all; }
.img-footer {
  display: flex; justify-content: flex-end;
  padding: 4px 0; gap: 6px;
}
.img-badge {
  font-size: 10px; color: #8b949e; background: #21262d;
  padding: 2px 6px; border-radius: 10px;
}
</style>
