<template>
  <!-- Grafana-style time series chart using Chart.js -->
  <div class="viz-line-chart" :style="{ height: `${height}px` }">
    <canvas ref="canvasRef" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from "vue";
import {
  Chart,
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  TimeScale,
  Filler,
  Tooltip,
  Legend,
  type ChartConfiguration,
} from "chart.js";
import "chartjs-adapter-date-fns";
import type { VizDataPoint } from "../../lib/viz-types";
import { VIZ_COLORS, defaultDatasetStyle } from "../../lib/viz-types";

Chart.register(LineController, LineElement, PointElement, LinearScale, TimeScale, Filler, Tooltip, Legend);

const props = withDefaults(defineProps<{
  points?: VizDataPoint[];
  label?: string;
  unit?: string;
  color?: string;
  height?: number;
  min?: number | null;
  max?: number | null;
}>(), {
  points: () => [],
  label: "Value",
  unit: "",
  color: VIZ_COLORS.blue,
  height: 220,
  min: null,
  max: null,
});

const canvasRef = ref<HTMLCanvasElement | null>(null);
let chart: Chart | null = null;

function buildData() {
  return (props.points ?? [])
    .filter((p) => p.v !== null)
    .map((p) => ({ x: p.t * 1000, y: p.v as number }));
}

function initChart() {
  if (!canvasRef.value) return;
  if (chart) { chart.destroy(); chart = null; }

  const ctx = canvasRef.value.getContext("2d");
  if (!ctx) return;

  const cfg: ChartConfiguration<"line"> = {
    type: "line",
    data: {
      datasets: [{
        label: props.label,
        data: buildData() as { x: number; y: number }[],
        ...defaultDatasetStyle(props.color),
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          mode: "index",
          intersect: false,
          backgroundColor: VIZ_COLORS.panel,
          borderColor: VIZ_COLORS.border,
          borderWidth: 1,
          titleColor: VIZ_COLORS.label,
          bodyColor: VIZ_COLORS.text,
          callbacks: {
            label: (ctx) => ` ${ctx.parsed.y}${props.unit ? " " + props.unit : ""}`,
          },
        },
      },
      scales: {
        x: {
          type: "time",
          time: { tooltipFormat: "HH:mm:ss", displayFormats: { minute: "HH:mm", hour: "HH:mm", day: "MMM d" } },
          grid: { color: VIZ_COLORS.border + "66" },
          ticks: { color: VIZ_COLORS.label, maxTicksLimit: 6, font: { size: 11 } },
          border: { color: VIZ_COLORS.border },
        },
        y: {
          min: props.min ?? undefined,
          max: props.max ?? undefined,
          grid: { color: VIZ_COLORS.border + "66" },
          ticks: {
            color: VIZ_COLORS.label,
            font: { size: 11 },
            callback: (v) => `${v}${props.unit ? " " + props.unit : ""}`,
          },
          border: { color: VIZ_COLORS.border },
        },
      },
    },
  };

  chart = new Chart(ctx, cfg);
}

function updateData() {
  if (!chart) return;
  chart.data.datasets[0].data = buildData() as { x: number; y: number }[];
  chart.update("none");
}

watch(() => props.points, updateData, { deep: true });

onMounted(initChart);
onUnmounted(() => { chart?.destroy(); chart = null; });
</script>

<style scoped>
.viz-line-chart {
  position: relative;
  width: 100%;
}
</style>
