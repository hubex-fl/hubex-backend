<script setup lang="ts">
/**
 * BlockCanvas — renders a live preview of the block list for the editor.
 * Uses simple inline-styled HTML that mirrors (approximately) the backend
 * cms_renderer.py output. The backend is the source of truth for the final
 * HTML; this is only used for in-editor display.
 */
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { CmsBlock } from "../../stores/cmsEditor";

const { t } = useI18n();

const props = defineProps<{
  blocks: CmsBlock[];
  selectedIndex?: number;
}>();

const emit = defineEmits<{
  (e: "select", index: number): void;
  (e: "duplicate", index: number): void;
  (e: "delete", index: number): void;
  (e: "moveUp", index: number): void;
  (e: "moveDown", index: number): void;
}>();

function renderBlockHtml(block: CmsBlock): string {
  const p = block.props || {};
  switch (block.type) {
    case "heading": {
      const level = ["h1", "h2", "h3"].includes(p.level) ? p.level : "h2";
      const sizes: Record<string, number> = { h1: 44, h2: 30, h3: 22 };
      const align = ["left", "center", "right"].includes(p.align) ? p.align : "left";
      return `<${level} style="font-size:${sizes[level]}px;font-weight:700;color:#F5F5F5;margin:24px 0 12px;text-align:${align};">${escapeHtml(p.text || t("cms.components.blockCanvas.defaults.heading"))}</${level}>`;
    }
    case "text":
      return `<div style="color:#A1A1AA;line-height:1.7;font-size:16px;margin:12px 0;">${p.content || `<em>${escapeHtml(t("cms.components.blockCanvas.placeholders.emptyText"))}</em>`}</div>`;
    case "image": {
      const src = escapeAttr(p.src || "");
      if (!src) return `<div style="padding:24px;text-align:center;color:#71717A;border:1px dashed rgba(255,255,255,0.15);border-radius:8px;">${escapeHtml(t("cms.components.blockCanvas.placeholders.imageNoSrc"))}</div>`;
      const w = p.width ? `max-width:${p.width}px;` : "max-width:100%;";
      return `<figure style="margin:24px auto;${w}text-align:center;"><img src="${src}" alt="${escapeAttr(p.alt || "")}" style="max-width:100%;border-radius:10px;" />${p.caption ? `<figcaption style="color:#A1A1AA;font-size:13px;margin-top:8px;">${escapeHtml(p.caption)}</figcaption>` : ""}</figure>`;
    }
    case "hero": {
      const title = escapeHtml(p.title || t("cms.components.blockCanvas.defaults.heroTitle"));
      const subtitle = escapeHtml(p.subtitle || "");
      const ctaText = escapeHtml(p.cta_text || "");
      const ctaLink = escapeAttr(p.cta_link || "#");
      const cta2Text = escapeHtml(p.cta_secondary_text || "");
      const cta2Link = escapeAttr(p.cta_secondary_link || "#");
      const bg = escapeAttr(p.bg_color || "#111110");
      const btns = `${ctaText ? `<a href="${ctaLink}" style="display:inline-block;padding:14px 28px;background:#F5A623;color:#111110;border-radius:10px;font-weight:600;text-decoration:none;margin:0 6px;">${ctaText}</a>` : ""}${cta2Text ? `<a href="${cta2Link}" style="display:inline-block;padding:14px 28px;background:transparent;color:#2DD4BF;border-radius:10px;font-weight:600;text-decoration:none;border:1px solid #2DD4BF;margin:0 6px;">${cta2Text}</a>` : ""}`;
      return `<section style="padding:96px 24px;text-align:center;background:radial-gradient(ellipse at top,rgba(245,166,35,0.12),transparent),${bg};border-bottom:1px solid rgba(255,255,255,0.08);"><h1 style="font-size:56px;font-weight:800;margin:0 0 16px;color:#F5F5F5;">${title}</h1><p style="font-size:20px;color:#A1A1AA;max-width:640px;margin:0 auto 32px;">${subtitle}</p>${btns ? `<div style="margin-top:32px;">${btns}</div>` : ""}</section>`;
    }
    case "feature_grid": {
      const cols = Math.max(1, Math.min(6, Number(p.columns) || 3));
      const items: any[] = Array.isArray(p.items) ? p.items : [];
      const cards = items
        .map(
          (it) =>
            `<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:28px;">${it.icon ? `<div style="font-size:28px;margin-bottom:12px;">${escapeHtml(it.icon)}</div>` : ""}<h3 style="color:#F5A623;margin:0 0 12px;font-size:18px;">${escapeHtml(it.title || "")}</h3><p style="color:#A1A1AA;margin:0;line-height:1.6;">${escapeHtml(it.description || "")}</p></div>`,
        )
        .join("");
      return `<section style="display:grid;grid-template-columns:repeat(${cols},1fr);gap:24px;max-width:1200px;margin:48px auto;padding:0 24px;">${cards || `<div style="color:#71717A;padding:24px;text-align:center;grid-column:1/-1;">${escapeHtml(t("cms.components.blockCanvas.placeholders.noItemsYet"))}</div>`}</section>`;
    }
    case "cta": {
      const title = escapeHtml(p.title || t("cms.components.blockCanvas.defaults.ctaTitle"));
      const desc = escapeHtml(p.description || "");
      const btn = escapeHtml(p.button_text || t("cms.components.blockCanvas.defaults.ctaButton"));
      const link = escapeAttr(p.button_link || "#");
      return `<section style="padding:64px 24px;text-align:center;background:rgba(245,166,35,0.08);border-top:1px solid rgba(245,166,35,0.2);border-bottom:1px solid rgba(245,166,35,0.2);"><h2 style="font-size:32px;margin:0 0 12px;color:#F5F5F5;">${title}</h2><p style="color:#A1A1AA;margin:0 0 24px;">${desc}</p>${btn ? `<a href="${link}" style="display:inline-block;padding:12px 28px;background:#F5A623;color:#111110;border-radius:8px;font-weight:600;text-decoration:none;">${btn}</a>` : ""}</section>`;
    }
    case "spacer": {
      const h = Number(p.height) || 40;
      return `<div style="height:${h}px;background:rgba(255,255,255,0.02);border:1px dashed rgba(255,255,255,0.06);text-align:center;color:#52525B;font-size:11px;display:flex;align-items:center;justify-content:center;">${escapeHtml(t("cms.components.blockCanvas.placeholders.spacer", { height: h }))}</div>`;
    }
    case "divider": {
      const style = ["solid", "dashed", "dotted"].includes(p.style) ? p.style : "solid";
      const w = Number(p.width) || 100;
      return `<div style="margin:32px auto;width:${w}%;"><hr style="border:none;border-top:1px ${style} rgba(255,255,255,0.1);" /></div>`;
    }
    case "columns": {
      const count = Math.max(1, Math.min(6, Number(p.count) || 2));
      const items: any[] = Array.isArray(p.items) ? p.items : [];
      const cols = items
        .map(
          (it) =>
            `<div style="flex:1;min-width:0;padding:16px;border:1px dashed rgba(255,255,255,0.1);border-radius:6px;color:#A1A1AA;">${typeof it?.content === "string" ? it.content : `<em>${escapeHtml(t("cms.components.blockCanvas.placeholders.column"))}</em>`}</div>`,
        )
        .join("");
      return `<section style="display:grid;grid-template-columns:repeat(${count},1fr);gap:24px;max-width:1200px;margin:24px auto;padding:0 24px;">${cols}</section>`;
    }
    case "html":
      return p.content || `<div style="color:#71717A;padding:12px;font-style:italic;">${escapeHtml(t("cms.components.blockCanvas.placeholders.emptyHtml"))}</div>`;
    case "video": {
      const url = escapeAttr(p.url || "");
      if (!url) return `<div style="padding:24px;text-align:center;color:#71717A;border:1px dashed rgba(255,255,255,0.15);border-radius:8px;">${escapeHtml(t("cms.components.blockCanvas.placeholders.videoNoUrl"))}</div>`;
      const ratio = (p.aspect_ratio || "16:9").replace(":", "/");
      const isEmbed = /youtube\.com|youtu\.be|vimeo\.com/.test(url);
      const inner = isEmbed
        ? `<iframe src="${url}" frameborder="0" allowfullscreen style="position:absolute;inset:0;width:100%;height:100%;"></iframe>`
        : `<video src="${url}" controls style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;"></video>`;
      return `<div style="max-width:960px;margin:32px auto;padding:0 24px;"><div style="position:relative;aspect-ratio:${ratio};border-radius:12px;overflow:hidden;border:1px solid rgba(255,255,255,0.08);">${inner}</div>${p.caption ? `<div style="color:#A1A1AA;font-size:13px;text-align:center;margin-top:8px;">${escapeHtml(p.caption)}</div>` : ""}</div>`;
    }
    case "quote": {
      const text = escapeHtml(p.text || t("cms.components.blockCanvas.defaults.quoteText"));
      const author = escapeHtml(p.author || "");
      const role = escapeHtml(p.role || "");
      return `<blockquote style="max-width:800px;margin:48px auto;padding:40px;background:rgba(255,255,255,0.03);border-left:4px solid #F5A623;border-radius:12px;"><p style="font-size:22px;line-height:1.5;color:#F5F5F5;margin:0 0 20px;font-style:italic;">"${text}"</p>${author ? `<div><div style="color:#F5A623;font-weight:600;">${author}</div><div style="color:#A1A1AA;font-size:13px;">${role}</div></div>` : ""}</blockquote>`;
    }
    case "stats": {
      const items: any[] = Array.isArray(p.items) ? p.items : [];
      const cells = items
        .map(
          (it) =>
            `<div style="text-align:center;"><div style="font-family:'IBM Plex Mono',monospace;font-size:42px;color:${escapeAttr(it.color || "#F5A623")};font-weight:700;">${escapeHtml(String(it.value ?? ""))}</div><div style="color:#A1A1AA;font-size:12px;text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;">${escapeHtml(it.label || "")}</div></div>`,
        )
        .join("");
      const cols = Math.max(1, Math.min(6, items.length || 1));
      return `<section style="display:grid;grid-template-columns:repeat(${cols},1fr);gap:24px;max-width:1000px;margin:48px auto;padding:0 24px;">${cells || `<div style="color:#71717A;padding:24px;text-align:center;grid-column:1/-1;">${escapeHtml(t("cms.components.blockCanvas.placeholders.noStatsYet"))}</div>`}</section>`;
    }
    case "button": {
      const text = escapeHtml(p.text || t("cms.components.blockCanvas.defaults.buttonText"));
      const link = escapeAttr(p.link || "#");
      const align = ["left", "center", "right"].includes(p.align) ? p.align : "left";
      const variant = (p.style || "primary").toLowerCase();
      const size = (p.size || "md").toLowerCase();
      const pad =
        size === "sm"
          ? "8px 16px"
          : size === "lg"
            ? "16px 32px"
            : "12px 24px";
      const bgStyle =
        variant === "secondary"
          ? "background:transparent;color:#2DD4BF;border:1px solid #2DD4BF;"
          : variant === "ghost"
            ? "background:rgba(255,255,255,0.05);color:#E5E5E5;border:1px solid rgba(255,255,255,0.08);"
            : "background:#F5A623;color:#111110;border:none;";
      return `<div style="text-align:${align};margin:16px 0;"><a href="${link}" style="display:inline-block;padding:${pad};border-radius:8px;font-weight:600;text-decoration:none;${bgStyle}">${text}</a></div>`;
    }
    case "list": {
      const tag = p.type === "ol" ? "ol" : "ul";
      const items: string[] = Array.isArray(p.items) ? p.items : [];
      const lis = items.map((it) => `<li>${escapeHtml(String(it))}</li>`).join("");
      return `<${tag} style="color:#A1A1AA;max-width:800px;margin:16px auto;padding:0 24px 0 48px;line-height:1.8;">${lis || `<li><em>${escapeHtml(t("cms.components.blockCanvas.placeholders.noItems"))}</em></li>`}</${tag}>`;
    }
    // ── HubEx integration blocks (editor preview only — real values load at runtime) ──
    case "dashboard_embed": {
      const dashId = Number(p.dashboard_id || 0);
      const h = Number(p.height || 600);
      if (!dashId) {
        return `<div style="padding:32px;text-align:center;color:#71717A;border:1px dashed rgba(245,166,35,0.3);border-radius:12px;margin:16px auto;max-width:960px;"><div style="font-size:24px;margin-bottom:8px;">📊</div>${escapeHtml(t("cms.components.blockCanvas.dashboard.hint"))}</div>`;
      }
      return `<div style="margin:16px auto;max-width:1200px;padding:0 24px;"><div style="height:${h}px;background:#111110;border:1px solid rgba(255,255,255,0.08);border-radius:12px;display:flex;align-items:center;justify-content:center;color:#71717A;">📊 ${escapeHtml(t("cms.components.blockCanvas.dashboard.runtime", { id: dashId }))}</div></div>`;
    }
    case "variable_value": {
      const label = escapeHtml(p.label || p.key || t("cms.components.blockCanvas.defaults.variableLabel"));
      const unit = p.unit ? ` <span style="color:#A1A1AA;font-size:0.5em;">${escapeHtml(p.unit)}</span>` : "";
      return `<div style="max-width:360px;margin:16px auto;padding:20px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;text-align:center;"><div style="font-family:'IBM Plex Mono',monospace;font-size:44px;color:#F5A623;font-weight:700;">—${unit}</div><div style="color:#A1A1AA;margin-top:6px;font-size:13px;text-transform:uppercase;letter-spacing:0.05em;">${label}</div></div>`;
    }
    case "device_card": {
      const uid = escapeHtml(p.device_uid || "");
      const deviceLabel = escapeHtml(t("cms.components.blockCanvas.device.label", { uid: uid || t("cms.components.blockCanvas.defaults.notSet") }));
      return `<div style="max-width:520px;margin:16px auto;padding:20px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;"><div style="color:#F5F5F5;font-weight:600;">🖥 ${deviceLabel}</div><div style="color:#71717A;font-family:'IBM Plex Mono',monospace;font-size:12px;margin-top:4px;">${escapeHtml(t("cms.components.blockCanvas.device.loadsAtRuntime"))}</div></div>`;
    }
    case "device_list": {
      const cols = Math.max(1, Math.min(6, Number(p.columns) || 3));
      const filter = escapeHtml(p.filter || "all");
      return `<div style="max-width:1200px;margin:16px auto;padding:0 24px;"><div style="color:#A1A1AA;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">${escapeHtml(t("cms.components.blockCanvas.device.listHeader", { filter }))}</div><div style="display:grid;grid-template-columns:repeat(${cols},1fr);gap:16px;"><div style="grid-column:1/-1;padding:24px;text-align:center;color:#71717A;border:1px dashed rgba(255,255,255,0.08);border-radius:8px;">${escapeHtml(t("cms.components.blockCanvas.device.listRuntime"))}</div></div></div>`;
    }
    case "tour_trigger": {
      const text = escapeHtml(p.button_text || t("cms.components.blockCanvas.defaults.tourButtonText"));
      const tourId = escapeAttr(p.tour_id || "");
      const variant = (p.style || "primary").toLowerCase();
      const bg = variant === "secondary"
        ? "background:transparent;color:#2DD4BF;border:1px solid #2DD4BF;"
        : variant === "ghost"
          ? "background:rgba(255,255,255,0.05);color:#E5E5E5;border:1px solid rgba(255,255,255,0.08);"
          : "background:#F5A623;color:#111110;border:none;";
      return `<div style="text-align:center;margin:16px 0;"><button type="button" data-tour-trigger="${tourId}" style="display:inline-block;padding:12px 24px;border-radius:8px;font-weight:600;cursor:pointer;${bg}">${text}</button></div>`;
    }
    case "alert_banner": {
      const severity = escapeHtml(p.severity_filter || "all");
      return `<div style="max-width:960px;margin:16px auto;padding:14px 18px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:10px;color:#A1A1AA;">⚠ ${escapeHtml(t("cms.components.blockCanvas.alertBanner", { severity }))}</div>`;
    }
    case "metric_counter": {
      const label = escapeHtml(p.label || p.metric || t("cms.components.blockCanvas.defaults.metricLabel"));
      const color = escapeAttr(p.color || "#2DD4BF");
      const icon = p.icon ? `<div style="font-size:36px;">${escapeHtml(p.icon)}</div>` : "";
      return `<div style="max-width:360px;margin:16px auto;padding:20px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;display:flex;align-items:center;gap:16px;">${icon}<div><div style="font-family:'IBM Plex Mono',monospace;font-size:36px;color:${color};font-weight:700;">—</div><div style="color:#A1A1AA;font-size:12px;text-transform:uppercase;letter-spacing:0.08em;">${label}</div></div></div>`;
    }
    case "automation_status": {
      const id = Number(p.automation_id || 0);
      const ref = id ? `#${id}` : t("cms.components.blockCanvas.defaults.notSet");
      const automationLabel = escapeHtml(t("cms.components.blockCanvas.automation.label", { ref }));
      return `<div style="max-width:520px;margin:16px auto;padding:20px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;"><div style="color:#F5F5F5;font-weight:600;">⚙ ${automationLabel}</div><div style="color:#71717A;font-size:13px;margin-top:4px;">${escapeHtml(t("cms.components.blockCanvas.device.loadsAtRuntime"))}</div></div>`;
    }
    default:
      return `<div style="padding:16px;background:rgba(255,255,255,0.03);border:1px dashed rgba(255,255,255,0.1);border-radius:6px;color:#A1A1AA;">${escapeHtml(t("cms.components.blockCanvas.placeholders.blockFallback", { type: block.type }))}</div>`;
  }
}

function escapeHtml(s: string): string {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeAttr(s: string): string {
  return escapeHtml(s);
}

const items = computed(() =>
  props.blocks.map((b, i) => ({
    block: b,
    html: renderBlockHtml(b),
    index: i,
  })),
);
</script>

<template>
  <div class="block-canvas">
    <div v-if="blocks.length === 0" class="empty">
      <div class="empty-inner">
        <div class="empty-title">{{ t('cms.components.blockCanvas.empty.title') }}</div>
        <div class="empty-sub">
          {{ t('cms.components.blockCanvas.empty.subtitle') }}
        </div>
      </div>
    </div>
    <div
      v-for="item in items"
      :key="item.block.id"
      class="block-wrap"
      :class="{ selected: item.index === selectedIndex }"
      @click.stop="emit('select', item.index)"
    >
      <div class="block-controls">
        <span class="block-type">{{ item.block.type }}</span>
        <div class="block-btns">
          <button
            type="button"
            @click.stop="emit('moveUp', item.index)"
            :disabled="item.index === 0"
            :title="t('cms.components.blockCanvas.controls.moveUp')"
          >
            ▲
          </button>
          <button
            type="button"
            @click.stop="emit('moveDown', item.index)"
            :disabled="item.index === blocks.length - 1"
            :title="t('cms.components.blockCanvas.controls.moveDown')"
          >
            ▼
          </button>
          <button
            type="button"
            @click.stop="emit('duplicate', item.index)"
            :title="t('cms.components.blockCanvas.controls.duplicate')"
          >
            ⎘
          </button>
          <button
            type="button"
            class="danger"
            @click.stop="emit('delete', item.index)"
            :title="t('cms.components.blockCanvas.controls.delete')"
          >
            ×
          </button>
        </div>
      </div>
      <div class="block-preview" v-html="item.html"></div>
    </div>
  </div>
</template>

<style scoped>
.block-canvas {
  background: #111110;
  min-height: 100%;
  padding: 24px 16px;
  overflow-y: auto;
}
.empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 16px;
}
.empty-inner {
  text-align: center;
  color: #52525b;
}
.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: #a1a1aa;
  margin-bottom: 6px;
}
.empty-sub { font-size: 13px; }
.block-wrap {
  position: relative;
  margin-bottom: 12px;
  border: 1px solid transparent;
  border-radius: 10px;
  transition: border-color 0.1s, box-shadow 0.1s;
  cursor: pointer;
}
.block-wrap:hover {
  border-color: rgba(255, 255, 255, 0.12);
}
.block-wrap.selected {
  border-color: #f5a623;
  box-shadow: 0 0 0 2px rgba(245, 166, 35, 0.12);
}
.block-controls {
  position: absolute;
  top: -10px;
  left: 12px;
  right: 12px;
  display: flex;
  justify-content: space-between;
  gap: 8px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s;
  z-index: 2;
}
.block-wrap:hover .block-controls,
.block-wrap.selected .block-controls {
  opacity: 1;
  pointer-events: auto;
}
.block-type {
  font-family: "IBM Plex Mono", monospace;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #111110;
  background: #f5a623;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 700;
}
.block-btns {
  display: flex;
  gap: 2px;
  background: #111110;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  padding: 2px;
}
.block-btns button {
  background: transparent;
  border: none;
  color: #a1a1aa;
  width: 22px;
  height: 22px;
  font-size: 11px;
  cursor: pointer;
  border-radius: 3px;
}
.block-btns button:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #f5f5f5;
}
.block-btns button.danger:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}
.block-btns button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.block-preview {
  border-radius: 10px;
  overflow: hidden;
}
</style>
