<script setup lang="ts">
/**
 * BlockLibrary — lists available block types grouped by category.
 * Click to insert a block (emits "insert" with type + default props).
 */
import { computed } from "vue";
import { useI18n } from "vue-i18n";

const { t } = useI18n();

const emit = defineEmits<{
  (e: "insert", payload: { type: string; props: Record<string, any> }): void;
}>();

type BlockSpec = {
  type: string;
  label: string;
  icon: string;
  defaults: Record<string, any>;
};

type BlockGroup = {
  name: string;
  items: BlockSpec[];
};

const groups = computed<BlockGroup[]>(() => [
  {
    name: t("cms.components.blockLibrary.groups.layout"),
    items: [
      {
        type: "hero",
        label: t("cms.components.blockLibrary.items.hero"),
        icon: "🪧",
        defaults: {
          title: t("cms.components.blockLibrary.defaults.hero.title"),
          subtitle: t("cms.components.blockLibrary.defaults.hero.subtitle"),
          bg_color: "#111110",
          cta_text: t("cms.components.blockLibrary.defaults.hero.cta"),
          cta_link: "#",
          cta_secondary_text: "",
          cta_secondary_link: "",
        },
      },
      {
        type: "columns",
        label: t("cms.components.blockLibrary.items.columns"),
        icon: "▤",
        defaults: {
          count: 2,
          items: [
            { content: t("cms.components.blockLibrary.defaults.columns.col1") },
            { content: t("cms.components.blockLibrary.defaults.columns.col2") },
          ],
        },
      },
      { type: "spacer", label: t("cms.components.blockLibrary.items.spacer"), icon: "↕", defaults: { height: 40 } },
      {
        type: "divider",
        label: t("cms.components.blockLibrary.items.divider"),
        icon: "—",
        defaults: { style: "solid", width: 100 },
      },
    ],
  },
  {
    name: t("cms.components.blockLibrary.groups.content"),
    items: [
      {
        type: "heading",
        label: t("cms.components.blockLibrary.items.heading"),
        icon: "H",
        defaults: { level: "h2", text: t("cms.components.blockLibrary.defaults.heading.text"), align: "left" },
      },
      {
        type: "text",
        label: t("cms.components.blockLibrary.items.text"),
        icon: "T",
        defaults: { content: t("cms.components.blockLibrary.defaults.text.content") },
      },
      {
        type: "image",
        label: t("cms.components.blockLibrary.items.image"),
        icon: "🖼",
        defaults: { src: "", alt: "", caption: "", width: 800, align: "center" },
      },
      {
        type: "video",
        label: t("cms.components.blockLibrary.items.video"),
        icon: "▶",
        defaults: { url: "", caption: "", autoplay: false, aspect_ratio: "16:9" },
      },
      {
        type: "list",
        label: t("cms.components.blockLibrary.items.list"),
        icon: "•",
        defaults: {
          type: "ul",
          items: [
            t("cms.components.blockLibrary.defaults.list.firstItem"),
            t("cms.components.blockLibrary.defaults.list.secondItem"),
          ],
        },
      },
      {
        type: "quote",
        label: t("cms.components.blockLibrary.items.quote"),
        icon: "❝",
        defaults: { text: t("cms.components.blockLibrary.defaults.quote.text"), author: "", role: "", avatar: "" },
      },
      {
        type: "html",
        label: t("cms.components.blockLibrary.items.html"),
        icon: "</>",
        defaults: { content: t("cms.components.blockLibrary.defaults.html.content") },
      },
    ],
  },
  {
    name: t("cms.components.blockLibrary.groups.marketing"),
    items: [
      {
        type: "feature_grid",
        label: t("cms.components.blockLibrary.items.featureGrid"),
        icon: "▦",
        defaults: {
          columns: 3,
          items: [
            { icon: "", title: t("cms.components.blockLibrary.defaults.featureGrid.feature1Title"), description: t("cms.components.blockLibrary.defaults.featureGrid.featureDesc") },
            { icon: "", title: t("cms.components.blockLibrary.defaults.featureGrid.feature2Title"), description: t("cms.components.blockLibrary.defaults.featureGrid.featureDesc") },
            { icon: "", title: t("cms.components.blockLibrary.defaults.featureGrid.feature3Title"), description: t("cms.components.blockLibrary.defaults.featureGrid.featureDesc") },
          ],
        },
      },
      {
        type: "cta",
        label: t("cms.components.blockLibrary.items.cta"),
        icon: "→",
        defaults: {
          title: t("cms.components.blockLibrary.defaults.cta.title"),
          description: t("cms.components.blockLibrary.defaults.cta.description"),
          button_text: t("cms.components.blockLibrary.defaults.cta.buttonText"),
          button_link: "#",
          style: "amber",
        },
      },
      {
        type: "stats",
        label: t("cms.components.blockLibrary.items.stats"),
        icon: "123",
        defaults: {
          items: [
            { value: "1000+", label: t("cms.components.blockLibrary.defaults.stats.devicesLabel"), color: "#F5A623" },
            { value: "99.9%", label: t("cms.components.blockLibrary.defaults.stats.uptimeLabel"), color: "#2DD4BF" },
            { value: "24/7", label: t("cms.components.blockLibrary.defaults.stats.supportLabel"), color: "#F5A623" },
          ],
        },
      },
      {
        type: "button",
        label: t("cms.components.blockLibrary.items.button"),
        icon: "⬛",
        defaults: {
          text: t("cms.components.blockLibrary.defaults.button.text"),
          link: "#",
          style: "primary",
          size: "md",
          align: "left",
        },
      },
    ],
  },
  {
    name: t("cms.components.blockLibrary.groups.hubex"),
    items: [
      {
        type: "dashboard_embed",
        label: t("cms.components.blockLibrary.items.dashboardEmbed"),
        icon: "📊",
        defaults: { dashboard_id: 0, height: 600 },
      },
      {
        type: "variable_value",
        label: t("cms.components.blockLibrary.items.variableValue"),
        icon: "🔢",
        defaults: {
          key: "",
          device_uid: "",
          label: "",
          unit: "",
          decimals: 1,
          refresh_ms: 5000,
        },
      },
      {
        type: "device_card",
        label: t("cms.components.blockLibrary.items.deviceCard"),
        icon: "🖥",
        defaults: {
          device_uid: "",
          show_status: true,
          show_variables: true,
          refresh_ms: 10000,
        },
      },
      {
        type: "device_list",
        label: t("cms.components.blockLibrary.items.deviceList"),
        icon: "▦",
        defaults: { filter: "all", columns: 3, show_type: true },
      },
      {
        type: "tour_trigger",
        label: t("cms.components.blockLibrary.items.tourTrigger"),
        icon: "🎬",
        defaults: {
          tour_id: "getting-started",
          button_text: t("cms.components.blockLibrary.defaults.tourTrigger.buttonText"),
          style: "primary",
        },
      },
      {
        type: "alert_banner",
        label: t("cms.components.blockLibrary.items.alertBanner"),
        icon: "⚠",
        defaults: {
          severity_filter: "all",
          max_items: 3,
          auto_hide_if_none: true,
        },
      },
      {
        type: "metric_counter",
        label: t("cms.components.blockLibrary.items.metricCounter"),
        icon: "📡",
        defaults: {
          metric: "devices_online",
          label: t("cms.components.blockLibrary.defaults.metricCounter.label"),
          icon: "📡",
          color: "#2DD4BF",
        },
      },
      {
        type: "automation_status",
        label: t("cms.components.blockLibrary.items.automationStatus"),
        icon: "⚙",
        defaults: { automation_id: 0, show_last_fire: true },
      },
    ],
  },
]);

function insert(spec: BlockSpec) {
  emit("insert", {
    type: spec.type,
    props: JSON.parse(JSON.stringify(spec.defaults || {})),
  });
}
</script>

<template>
  <div class="block-library">
    <h4 class="lib-title">{{ t("cms.components.blockLibrary.title") }}</h4>
    <div v-for="g in groups" :key="g.name" class="lib-group">
      <div class="lib-group-name">{{ g.name }}</div>
      <div class="lib-grid">
        <button
          v-for="it in g.items"
          :key="it.type"
          type="button"
          class="lib-item"
          :title="t('cms.components.blockLibrary.insertTitle', { label: it.label })"
          @click="insert(it)"
        >
          <span class="lib-icon">{{ it.icon }}</span>
          <span class="lib-label">{{ it.label }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.block-library {
  padding: 12px 10px;
  overflow-y: auto;
}
.lib-title {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #71717a;
  margin: 0 0 12px;
  padding: 0 4px;
}
.lib-group {
  margin-bottom: 16px;
}
.lib-group-name {
  font-size: 10px;
  color: #a16207;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0 4px 6px;
}
.lib-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
}
.lib-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 10px 4px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  color: #e5e5e5;
  cursor: pointer;
  font-size: 11px;
  text-align: center;
}
.lib-item:hover {
  background: rgba(245, 166, 35, 0.1);
  border-color: rgba(245, 166, 35, 0.3);
}
.lib-icon {
  font-size: 18px;
}
.lib-label {
  font-size: 11px;
  color: #a1a1aa;
}
</style>
