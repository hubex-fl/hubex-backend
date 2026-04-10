<script setup lang="ts">
/**
 * BlockLibrary — lists available block types grouped by category.
 * Click to insert a block (emits "insert" with type + default props).
 */
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

const groups: BlockGroup[] = [
  {
    name: "Layout",
    items: [
      {
        type: "hero",
        label: "Hero",
        icon: "🪧",
        defaults: {
          title: "Your Hero Title",
          subtitle: "A compelling subtitle that explains the value.",
          bg_color: "#111110",
          cta_text: "Get Started",
          cta_link: "#",
          cta_secondary_text: "",
          cta_secondary_link: "",
        },
      },
      {
        type: "columns",
        label: "Columns",
        icon: "▤",
        defaults: {
          count: 2,
          items: [
            { content: "Column 1 content" },
            { content: "Column 2 content" },
          ],
        },
      },
      { type: "spacer", label: "Spacer", icon: "↕", defaults: { height: 40 } },
      {
        type: "divider",
        label: "Divider",
        icon: "—",
        defaults: { style: "solid", width: 100 },
      },
    ],
  },
  {
    name: "Content",
    items: [
      {
        type: "heading",
        label: "Heading",
        icon: "H",
        defaults: { level: "h2", text: "Section heading", align: "left" },
      },
      {
        type: "text",
        label: "Text",
        icon: "T",
        defaults: { content: "<p>Your text here…</p>" },
      },
      {
        type: "image",
        label: "Image",
        icon: "🖼",
        defaults: { src: "", alt: "", caption: "", width: 800, align: "center" },
      },
      {
        type: "video",
        label: "Video",
        icon: "▶",
        defaults: { url: "", caption: "", autoplay: false, aspect_ratio: "16:9" },
      },
      {
        type: "list",
        label: "List",
        icon: "•",
        defaults: { type: "ul", items: ["First item", "Second item"] },
      },
      {
        type: "quote",
        label: "Quote",
        icon: "❝",
        defaults: { text: "A meaningful quote.", author: "", role: "", avatar: "" },
      },
      {
        type: "html",
        label: "Raw HTML",
        icon: "</>",
        defaults: { content: "<div>Custom HTML</div>" },
      },
    ],
  },
  {
    name: "Marketing",
    items: [
      {
        type: "feature_grid",
        label: "Feature Grid",
        icon: "▦",
        defaults: {
          columns: 3,
          items: [
            { icon: "", title: "Feature 1", description: "Describe the feature." },
            { icon: "", title: "Feature 2", description: "Describe the feature." },
            { icon: "", title: "Feature 3", description: "Describe the feature." },
          ],
        },
      },
      {
        type: "cta",
        label: "Call to Action",
        icon: "→",
        defaults: {
          title: "Ready to start?",
          description: "Join thousands already using HubEx.",
          button_text: "Try Free",
          button_link: "#",
          style: "amber",
        },
      },
      {
        type: "stats",
        label: "Stats",
        icon: "123",
        defaults: {
          items: [
            { value: "1000+", label: "Devices", color: "#F5A623" },
            { value: "99.9%", label: "Uptime", color: "#2DD4BF" },
            { value: "24/7", label: "Support", color: "#F5A623" },
          ],
        },
      },
      {
        type: "button",
        label: "Button",
        icon: "⬛",
        defaults: {
          text: "Click me",
          link: "#",
          style: "primary",
          size: "md",
          align: "left",
        },
      },
    ],
  },
  {
    name: "HubEx",
    items: [
      {
        type: "dashboard_embed",
        label: "Dashboard",
        icon: "📊",
        defaults: { dashboard_id: 0, height: 600 },
      },
      {
        type: "variable_value",
        label: "Variable",
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
        label: "Device Card",
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
        label: "Device List",
        icon: "▦",
        defaults: { filter: "all", columns: 3, show_type: true },
      },
      {
        type: "tour_trigger",
        label: "Tour Button",
        icon: "🎬",
        defaults: {
          tour_id: "getting-started",
          button_text: "Take a tour",
          style: "primary",
        },
      },
      {
        type: "alert_banner",
        label: "Alerts",
        icon: "⚠",
        defaults: {
          severity_filter: "all",
          max_items: 3,
          auto_hide_if_none: true,
        },
      },
      {
        type: "metric_counter",
        label: "Metric",
        icon: "📡",
        defaults: {
          metric: "devices_online",
          label: "Devices Online",
          icon: "📡",
          color: "#2DD4BF",
        },
      },
      {
        type: "automation_status",
        label: "Automation",
        icon: "⚙",
        defaults: { automation_id: 0, show_last_fire: true },
      },
    ],
  },
];

function insert(spec: BlockSpec) {
  emit("insert", {
    type: spec.type,
    props: JSON.parse(JSON.stringify(spec.defaults || {})),
  });
}
</script>

<template>
  <div class="block-library">
    <h4 class="lib-title">Blocks</h4>
    <div v-for="g in groups" :key="g.name" class="lib-group">
      <div class="lib-group-name">{{ g.name }}</div>
      <div class="lib-grid">
        <button
          v-for="it in g.items"
          :key="it.type"
          type="button"
          class="lib-item"
          :title="`Insert ${it.label}`"
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
