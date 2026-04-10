<script setup lang="ts">
/**
 * BlockRenderer
 *
 * Two complementary modes:
 *
 * 1. `blocks` prop: client-side renders each HubEx integration block directly
 *    as a Vue component. Non-HubEx blocks are ignored here (they're expected
 *    to be rendered by the server and passed via v-html).
 *
 * 2. `html` prop: takes server-rendered HTML that contains HubEx
 *    placeholder divs and hydrates each placeholder with the matching Vue
 *    component via a teleport-style scan of the DOM.
 *
 * Both modes can be used together: pass server HTML via v-html AND then
 * mount this renderer with `mode=hydrate` to upgrade placeholders in place.
 */
import {
  computed,
  onMounted,
  onBeforeUnmount,
  ref,
  watch,
  createApp,
  type App,
} from "vue";
import VariableValueBlock from "./blocks/VariableValueBlock.vue";
import DeviceCardBlock from "./blocks/DeviceCardBlock.vue";
import DeviceListBlock from "./blocks/DeviceListBlock.vue";
import DashboardEmbedBlock from "./blocks/DashboardEmbedBlock.vue";
import TourTriggerBlock from "./blocks/TourTriggerBlock.vue";
import AlertBannerBlock from "./blocks/AlertBannerBlock.vue";
import MetricCounterBlock from "./blocks/MetricCounterBlock.vue";
import AutomationStatusBlock from "./blocks/AutomationStatusBlock.vue";
import { useTourStore } from "../../stores/tour";

type Block = {
  id?: string;
  type: string;
  props?: Record<string, any>;
};

type Props = {
  blocks?: Block[] | null;
  html?: string | null;
  mode?: "client" | "hydrate";
};

const props = withDefaults(defineProps<Props>(), {
  blocks: null,
  html: null,
  mode: "client",
});

const HUBEX_COMPONENTS: Record<string, any> = {
  variable_value: VariableValueBlock,
  device_card: DeviceCardBlock,
  device_list: DeviceListBlock,
  dashboard_embed: DashboardEmbedBlock,
  tour_trigger: TourTriggerBlock,
  alert_banner: AlertBannerBlock,
  metric_counter: MetricCounterBlock,
  automation_status: AutomationStatusBlock,
};

const container = ref<HTMLElement | null>(null);
const mountedApps: App[] = [];
const tourStore = useTourStore();

function cleanup() {
  for (const app of mountedApps) {
    try { app.unmount(); } catch { /* noop */ }
  }
  mountedApps.length = 0;
}

function hydrateContainer() {
  if (props.mode !== "hydrate") return;
  if (!container.value) return;
  cleanup();

  // Hubex placeholder divs written by the backend renderer
  const nodes = container.value.querySelectorAll<HTMLElement>("[data-hubex-block]");
  nodes.forEach((node) => {
    const type = node.getAttribute("data-hubex-block") || "";
    const rawProps = node.getAttribute("data-hubex-props") || "{}";
    let parsed: Record<string, any> = {};
    try {
      parsed = JSON.parse(rawProps);
    } catch {
      parsed = {};
    }
    const Component = HUBEX_COMPONENTS[type];
    if (!Component) return;
    // Clear the placeholder content before mounting
    node.innerHTML = "";
    const app = createApp(Component, { props: parsed });
    // Make the tour store available inside the mounted component
    try {
      const pinia = (window as any).__hubex_pinia;
      if (pinia) app.use(pinia);
    } catch { /* noop */ }
    try {
      app.mount(node);
      mountedApps.push(app);
    } catch {
      /* noop */
    }
  });

  // Bind tour triggers (plain buttons with data-tour-trigger attribute)
  const triggers = container.value.querySelectorAll<HTMLElement>("[data-tour-trigger]");
  triggers.forEach((el) => {
    const tourId = el.getAttribute("data-tour-trigger") || "";
    if (!tourId) return;
    const handler = () => {
      tourStore.start(tourId).catch(() => { /* noop */ });
    };
    el.addEventListener("click", handler);
    // Store for cleanup on unmount
    (el as any).__tourCleanup = handler;
  });
}

const clientBlocks = computed<Block[]>(() => {
  if (!props.blocks) return [];
  return props.blocks.filter((b) => HUBEX_COMPONENTS[b.type]);
});

function componentFor(type: string) {
  return HUBEX_COMPONENTS[type] ?? null;
}

onMounted(hydrateContainer);
onBeforeUnmount(() => {
  cleanup();
  if (container.value) {
    container.value
      .querySelectorAll<HTMLElement>("[data-tour-trigger]")
      .forEach((el) => {
        const h = (el as any).__tourCleanup;
        if (h) el.removeEventListener("click", h);
      });
  }
});

watch(() => props.html, hydrateContainer);
</script>

<template>
  <!-- Hydrate mode: render server HTML with v-html, then upgrade placeholders -->
  <div v-if="mode === 'hydrate'" ref="container" class="block-renderer hydrate" v-html="html || ''" />

  <!-- Client mode: render HubEx blocks directly from the blocks array -->
  <div v-else class="block-renderer client">
    <template v-for="(block, i) in clientBlocks" :key="block.id || i">
      <component
        :is="componentFor(block.type)"
        :props="block.props || {}"
      />
    </template>
  </div>
</template>

<style scoped>
.block-renderer { width: 100%; }
</style>
