<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { useTourStore } from "../../../stores/tour";

type Props = {
  tour_id?: string;
  button_text?: string;
  style?: "primary" | "secondary" | "ghost";
};

const props = defineProps<{ props: Props }>();
const tour = useTourStore();
const { t } = useI18n();

const buttonText = computed(
  () => props.props.button_text || t('cms.components.blocks.tourTrigger.defaultButtonText')
);
const variant = computed(() => props.props.style || "primary");

async function startTour() {
  const id = props.props.tour_id;
  if (!id) return;
  try {
    await tour.start(id);
  } catch (e) {
    console.warn("[TourTrigger] failed to start", id, e);
  }
}
</script>

<template>
  <div class="tour-trigger-wrap">
    <button
      type="button"
      class="tour-btn"
      :class="`variant-${variant}`"
      :data-tour-trigger="props.props.tour_id"
      @click="startTour"
    >
      {{ buttonText }}
    </button>
  </div>
</template>

<style scoped>
.tour-trigger-wrap {
  text-align: center;
  margin: 16px 0;
}
.tour-btn {
  display: inline-block;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 15px;
  cursor: pointer;
  border: none;
}
.variant-primary {
  background: #F5A623;
  color: #111110;
}
.variant-primary:hover { background: #e89915; }
.variant-secondary {
  background: transparent;
  color: #2DD4BF;
  border: 1px solid #2DD4BF;
}
.variant-secondary:hover { background: rgba(45,212,191,0.08); }
.variant-ghost {
  background: rgba(255,255,255,0.05);
  color: #E5E5E5;
  border: 1px solid rgba(255,255,255,0.08);
}
.variant-ghost:hover { background: rgba(255,255,255,0.08); }
</style>
