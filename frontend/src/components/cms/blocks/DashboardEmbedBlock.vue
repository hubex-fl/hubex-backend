<script setup lang="ts">
import { computed } from "vue";

type Props = {
  dashboard_id?: number;
  height?: number;
};

const props = defineProps<{ props: Props }>();

const src = computed(() =>
  props.props.dashboard_id ? `/kiosk/${props.props.dashboard_id}` : ""
);
const height = computed(() => Math.max(120, props.props.height ?? 600));
</script>

<template>
  <div class="dash-embed">
    <div v-if="!src" class="missing">Dashboard not configured</div>
    <iframe
      v-else
      :src="src"
      :style="{ height: `${height}px` }"
      loading="lazy"
      frameborder="0"
    ></iframe>
  </div>
</template>

<style scoped>
.dash-embed {
  max-width: 1200px;
  margin: 16px auto;
  padding: 0 24px;
}
.dash-embed iframe {
  width: 100%;
  border: 0;
  border-radius: 12px;
  background: #111110;
  border: 1px solid rgba(255,255,255,0.08);
}
.missing {
  padding: 48px;
  text-align: center;
  color: #71717A;
  background: rgba(255,255,255,0.03);
  border: 1px dashed rgba(255,255,255,0.08);
  border-radius: 12px;
}
</style>
