<template>
  <div class="viz-json">
    <div v-if="parsed === null" class="json-empty">No value</div>
    <div v-else class="json-root">
      <JsonNode :data="parsed" :depth="0" :expanded="true" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, ref, h } from "vue";

const props = withDefaults(defineProps<{
  currentValue?: unknown;
}>(), {
  currentValue: null,
});

const parsed = computed(() => {
  const v = props.currentValue;
  if (v === null || v === undefined) return null;
  if (typeof v === "object") return v;
  if (typeof v === "string") {
    try { return JSON.parse(v); } catch { return v; }
  }
  return v;
});

// Recursive JSON node renderer
const JsonNode = defineComponent({
  name: "JsonNode",
  props: {
    data: { required: true },
    depth: { type: Number, default: 0 },
    expanded: { type: Boolean, default: false },
    label: { type: String, default: "" },
  },
  setup(nodeProps) {
    const open = ref(nodeProps.expanded || nodeProps.depth < 2);

    return () => {
      const d = nodeProps.data as unknown;
      const indent = nodeProps.depth * 14;

      if (d === null) return h("span", { class: "jv-null" }, "null");
      if (typeof d === "boolean") return h("span", { class: "jv-bool" }, String(d));
      if (typeof d === "number") return h("span", { class: "jv-num" }, String(d));
      if (typeof d === "string") return h("span", { class: "jv-str" }, `"${d}"`);

      if (Array.isArray(d)) {
        if (!d.length) return h("span", { class: "jv-muted" }, "[]");
        return h("div", { class: "jv-node", style: { paddingLeft: `${indent}px` } }, [
          h("span", {
            class: "jv-toggle",
            onClick: () => { open.value = !open.value; },
          }, [
            h("span", { class: "jv-caret" }, open.value ? "▾" : "▸"),
            h("span", { class: "jv-bracket" }, `[${d.length}]`),
          ]),
          open.value
            ? h("div", d.map((item, i) =>
                h("div", { class: "jv-row" }, [
                  h("span", { class: "jv-key" }, `${i}: `),
                  h(JsonNode, { data: item, depth: nodeProps.depth + 1 }),
                ])
              ))
            : null,
        ]);
      }

      if (typeof d === "object") {
        const keys = Object.keys(d as object);
        if (!keys.length) return h("span", { class: "jv-muted" }, "{}");
        return h("div", { class: "jv-node", style: { paddingLeft: `${indent}px` } }, [
          h("span", {
            class: "jv-toggle",
            onClick: () => { open.value = !open.value; },
          }, [
            h("span", { class: "jv-caret" }, open.value ? "▾" : "▸"),
            h("span", { class: "jv-bracket" }, `{${keys.length}}`),
          ]),
          open.value
            ? h("div", keys.map((k) =>
                h("div", { class: "jv-row" }, [
                  h("span", { class: "jv-key" }, `${k}: `),
                  h(JsonNode, { data: (d as Record<string, unknown>)[k], depth: nodeProps.depth + 1 }),
                ])
              ))
            : null,
        ]);
      }

      return h("span", { class: "jv-muted" }, String(d));
    };
  },
});
</script>

<style scoped>
.viz-json {
  font-family: "JetBrains Mono", "Fira Code", monospace;
  font-size: 12px;
  background: #0d1117;
  border-radius: 4px;
  padding: 8px;
  overflow: auto;
}
.json-empty { color: #484f58; font-size: 11px; }
</style>

<style>
/* global so recursive component can use them */
.jv-node   { line-height: 1.7; }
.jv-row    { display: flex; align-items: baseline; gap: 4px; }
.jv-toggle { cursor: pointer; user-select: none; display: flex; align-items: baseline; gap: 4px; }
.jv-caret  { color: #8b949e; font-size: 10px; width: 10px; }
.jv-bracket{ color: #8b949e; font-size: 11px; }
.jv-key    { color: #79c0ff; flex-shrink: 0; }
.jv-str    { color: #a5d6ff; }
.jv-num    { color: #79c0ff; }
.jv-bool   { color: #56d364; }
.jv-null   { color: #8b949e; font-style: italic; }
.jv-muted  { color: #8b949e; }
</style>
