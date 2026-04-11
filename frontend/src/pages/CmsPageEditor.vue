<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";
import { useCmsEditorStore, type CmsBlock } from "../stores/cmsEditor";
import BlockCanvas from "../components/cms/BlockCanvas.vue";
import BlockLibrary from "../components/cms/BlockLibrary.vue";
import BlockPropertiesPanel from "../components/cms/BlockPropertiesPanel.vue";
import PageVersionHistory from "../components/cms/PageVersionHistory.vue";

const route = useRoute();
const router = useRouter();
const toast = useToastStore();
const { t } = useI18n();
const cmsEditor = useCmsEditorStore();

type CmsPage = {
  id: number;
  slug: string;
  title: string;
  description: string | null;
  content_html: string;
  content_mode: string;
  layout: string;
  meta_title: string | null;
  meta_description: string | null;
  og_image: string | null;
  visibility: string;
  public_token: string | null;
  has_pin: boolean;
  published: boolean;
  status?: string;
  scheduled_at?: string | null;
  view_count?: number;
  last_viewed_at?: string | null;
  blocks: CmsBlock[] | null;
};

const pageId = computed(() => Number(route.params.id));
const loading = ref(true);
const saving = ref(false);
const error = ref<string | null>(null);

const page = ref<CmsPage | null>(null);
const editTitle = ref("");
const editSlug = ref("");
const editDescription = ref("");
const editContent = ref("");
const editLayout = ref<"default" | "landing" | "minimal" | "fullscreen">("default");
const editContentMode = ref<"html" | "markdown" | "simple">("html");
const editMetaTitle = ref("");
const editMetaDescription = ref("");
const editOgImage = ref("");
const editVisibility = ref<"private" | "public" | "embed">("private");

// Editor mode: blocks (default), html, preview
const editorMode = ref<"blocks" | "html" | "preview">("blocks");
// HTML sub-view mode (for legacy HTML editor)
const viewMode = ref<"code" | "split" | "preview">("split");
const previewHtml = ref("");
const showMeta = ref(false);
const showStarters = ref(true);
const showHistory = ref(false);

// Debounce preview rendering
let debounceTimer: ReturnType<typeof setTimeout> | null = null;

async function loadPage() {
  loading.value = true;
  error.value = null;
  try {
    const p = await apiFetch<CmsPage>(`/api/v1/cms/pages/${pageId.value}`);
    page.value = p;
    editTitle.value = p.title;
    editSlug.value = p.slug;
    editDescription.value = p.description || "";
    editContent.value = p.content_html || "";
    editLayout.value = (p.layout as any) || "default";
    editContentMode.value = (p.content_mode as any) || "html";
    editMetaTitle.value = p.meta_title || "";
    editMetaDescription.value = p.meta_description || "";
    editOgImage.value = p.og_image || "";
    editVisibility.value = (p.visibility as any) || "private";
    // Hydrate block editor store
    cmsEditor.setBlocks(Array.isArray(p.blocks) ? p.blocks : []);
    // If page has no blocks but has legacy HTML, default to HTML mode
    if ((!p.blocks || p.blocks.length === 0) && (p.content_html || "").trim().length > 0) {
      editorMode.value = "html";
    } else {
      editorMode.value = "blocks";
    }
    await renderPreview();
  } catch (e: any) {
    error.value = e.message || t("cms.pageEditor.loadFailed");
  } finally {
    loading.value = false;
  }
}

function insertBlock(payload: { type: string; props: Record<string, any> }) {
  cmsEditor.addBlock(payload.type, payload.props);
}

function updateBlockProp(key: string, value: any) {
  if (cmsEditor.selectedIndex < 0) return;
  cmsEditor.setBlockProp(cmsEditor.selectedIndex, key, value);
}

async function renderPreview() {
  // Use the render endpoint for template variable substitution
  try {
    // Save unsaved changes to server is expensive; instead do a client-side
    // placeholder substitution for speed, then call server for accuracy.
    previewHtml.value = editContent.value;
  } catch {}
}

function schedulePreview() {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    previewHtml.value = editContent.value;
  }, 300);
}

watch(editContent, schedulePreview);

async function saveDraft() {
  if (!page.value) return;
  saving.value = true;
  try {
    // Prepare blocks payload — null if empty so backend falls back to HTML
    const blocksPayload =
      cmsEditor.blocks.length > 0 ? cmsEditor.blocks : null;
    await apiFetch(`/api/v1/cms/pages/${page.value.id}`, {
      method: "PUT",
      body: JSON.stringify({
        title: editTitle.value,
        slug: editSlug.value,
        description: editDescription.value || null,
        content_html: editContent.value,
        content_mode: editContentMode.value,
        layout: editLayout.value,
        meta_title: editMetaTitle.value || null,
        meta_description: editMetaDescription.value || null,
        og_image: editOgImage.value || null,
        visibility: editVisibility.value,
        blocks: blocksPayload,
      }),
    });
    cmsEditor.markClean();
    toast.show(t('cms.saved'), "success");
  } catch (e: any) {
    toast.show(e.message, "error");
  } finally {
    saving.value = false;
  }
}

async function publish() {
  if (!page.value) return;
  await saveDraft();
  try {
    await apiFetch(`/api/v1/cms/pages/${page.value.id}/publish`, { method: "POST" });
    toast.show(t('cms.published'), "success");
    await loadPage();
  } catch (e: any) {
    toast.show(e.message, "error");
  }
}

// ── Publishing workflow ──
const showPublishMenu = ref(false);
const showScheduleModal = ref(false);
const scheduleDateTime = ref("");

async function unpublishPage() {
  if (!page.value) return;
  showPublishMenu.value = false;
  try {
    await apiFetch(`/api/v1/cms/pages/${page.value.id}/unpublish`, { method: "POST" });
    toast.show(t("cms.pageEditor.toasts.movedToDraft"), "success");
    await loadPage();
  } catch (e: any) {
    toast.show(e.message, "error");
  }
}

async function archivePage() {
  if (!page.value) return;
  showPublishMenu.value = false;
  if (!confirm(t("cms.pageEditor.confirmArchive"))) return;
  try {
    await apiFetch(`/api/v1/cms/pages/${page.value.id}/archive`, { method: "POST" });
    toast.show(t("cms.pageEditor.toasts.archived"), "success");
    await loadPage();
  } catch (e: any) {
    toast.show(e.message, "error");
  }
}

function openSchedule() {
  showPublishMenu.value = false;
  // Default: one hour from now, formatted for datetime-local input
  const d = new Date(Date.now() + 60 * 60 * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  scheduleDateTime.value =
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  showScheduleModal.value = true;
}

async function submitSchedule() {
  if (!page.value || !scheduleDateTime.value) return;
  await saveDraft();
  const iso = new Date(scheduleDateTime.value).toISOString();
  try {
    await apiFetch(`/api/v1/cms/pages/${page.value.id}/schedule`, {
      method: "POST",
      body: JSON.stringify({ published_at: iso }),
    });
    toast.show(t("cms.pageEditor.toasts.scheduled"), "success");
    showScheduleModal.value = false;
    await loadPage();
  } catch (e: any) {
    toast.show(e.message, "error");
  }
}

// Relative time helper for stats
function relativeTime(iso: string | null | undefined): string {
  if (!iso) return t("cms.pageEditor.relativeTime.never");
  try {
    const diffMs = Date.now() - new Date(iso).getTime();
    const sec = Math.floor(diffMs / 1000);
    if (sec < 60) return t("cms.pageEditor.relativeTime.seconds", { n: sec });
    const min = Math.floor(sec / 60);
    if (min < 60) return t("cms.pageEditor.relativeTime.minutes", { n: min });
    const hr = Math.floor(min / 60);
    if (hr < 24) return t("cms.pageEditor.relativeTime.hours", { n: hr });
    const days = Math.floor(hr / 24);
    return t("cms.pageEditor.relativeTime.days", { n: days });
  } catch {
    return iso;
  }
}

async function share() {
  if (!page.value) return;
  try {
    const res = await apiFetch<{ public_token: string }>(`/api/v1/cms/pages/${page.value.id}/share`, {
      method: "POST",
    });
    const url = `${window.location.origin}/p/${editSlug.value}`;
    try { await navigator.clipboard.writeText(url); } catch {}
    toast.show(`${t('cms.shareCopied')}: ${url}`, "success");
    await loadPage();
  } catch (e: any) {
    toast.show(e.message, "error");
  }
}

// Template variables reference
const templateVars = computed(() => [
  { group: t("cms.pageEditor.templateVars.groups.metrics"), items: [
    { ref: "{{metric:devices_total}}", desc: t("cms.pageEditor.templateVars.descriptions.devicesTotal") },
    { ref: "{{metric:devices_online}}", desc: t("cms.pageEditor.templateVars.descriptions.devicesOnline") },
  ]},
  { group: t("cms.pageEditor.templateVars.groups.variables"), items: [
    { ref: "{{variable:your_key}}", desc: t("cms.pageEditor.templateVars.descriptions.variableLatest") },
    { ref: "{{variable:device_uid:key}}", desc: t("cms.pageEditor.templateVars.descriptions.variableDeviceLatest") },
  ]},
  { group: t("cms.pageEditor.templateVars.groups.devices"), items: [
    { ref: "{{device:uid:name}}", desc: t("cms.pageEditor.templateVars.descriptions.deviceName") },
    { ref: "{{device:uid:status}}", desc: t("cms.pageEditor.templateVars.descriptions.deviceStatus") },
  ]},
  { group: t("cms.pageEditor.templateVars.groups.timestamps"), items: [
    { ref: "{{timestamp:date}}", desc: t("cms.pageEditor.templateVars.descriptions.timestampDate") },
    { ref: "{{timestamp:iso}}", desc: t("cms.pageEditor.templateVars.descriptions.timestampIso") },
  ]},
]);

// HTML starter blocks
const starters = computed(() => [
  {
    name: t("cms.pageEditor.starters.hero.name"),
    html: `<section style="padding:80px 24px; text-align:center; background:radial-gradient(ellipse at top, rgba(245,166,35,0.1), transparent);">
  <h1 style="font-size:56px; font-weight:800; margin:0 0 16px; color:#F5F5F5;">${t("cms.pageEditor.starters.hero.title")}</h1>
  <p style="font-size:20px; color:#A1A1AA; max-width:640px; margin:0 auto 32px;">${t("cms.pageEditor.starters.hero.subtitle")}</p>
  <a href="#" style="display:inline-block; padding:14px 28px; background:#F5A623; color:#111110; border-radius:10px; font-weight:600; text-decoration:none;">${t("cms.pageEditor.starters.hero.cta")}</a>
</section>`,
  },
  {
    name: t("cms.pageEditor.starters.featureGrid.name"),
    html: `<section style="max-width:1200px; margin:0 auto; padding:64px 24px; display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:24px;">
  <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:28px;">
    <h3 style="color:#F5A623; margin:0 0 12px;">${t("cms.pageEditor.starters.featureGrid.feature1Title")}</h3>
    <p style="color:#A1A1AA; margin:0;">${t("cms.pageEditor.starters.featureGrid.feature1Desc")}</p>
  </div>
  <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:28px;">
    <h3 style="color:#2DD4BF; margin:0 0 12px;">${t("cms.pageEditor.starters.featureGrid.feature2Title")}</h3>
    <p style="color:#A1A1AA; margin:0;">${t("cms.pageEditor.starters.featureGrid.feature2Desc")}</p>
  </div>
  <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:28px;">
    <h3 style="color:#F5A623; margin:0 0 12px;">${t("cms.pageEditor.starters.featureGrid.feature3Title")}</h3>
    <p style="color:#A1A1AA; margin:0;">${t("cms.pageEditor.starters.featureGrid.feature3Desc")}</p>
  </div>
</section>`,
  },
  {
    name: t("cms.pageEditor.starters.cta.name"),
    html: `<section style="padding:60px 24px; text-align:center; background:rgba(245,166,35,0.08); border-top:1px solid rgba(245,166,35,0.2); border-bottom:1px solid rgba(245,166,35,0.2);">
  <h2 style="font-size:32px; margin:0 0 12px; color:#F5F5F5;">${t("cms.pageEditor.starters.cta.title")}</h2>
  <p style="color:#A1A1AA; margin:0 0 24px;">${t("cms.pageEditor.starters.cta.subtitle")}</p>
  <a href="#" style="display:inline-block; padding:12px 28px; background:#F5A623; color:#111110; border-radius:8px; font-weight:600; text-decoration:none;">${t("cms.pageEditor.starters.cta.button")}</a>
</section>`,
  },
  {
    name: t("cms.pageEditor.starters.about.name"),
    html: `<section style="max-width:900px; margin:0 auto; padding:64px 24px;">
  <h2 style="font-size:36px; color:#F5F5F5; margin:0 0 24px;">${t("cms.pageEditor.starters.about.title")}</h2>
  <p style="color:#A1A1AA; line-height:1.7; font-size:17px;">${t("cms.pageEditor.starters.about.body")}</p>
</section>`,
  },
  {
    name: t("cms.pageEditor.starters.contact.name"),
    html: `<section style="max-width:720px; margin:0 auto; padding:64px 24px;">
  <h2 style="color:#F5F5F5; margin:0 0 16px;">${t("cms.pageEditor.starters.contact.title")}</h2>
  <p style="color:#A1A1AA; margin:0 0 8px;">${t("cms.pageEditor.starters.contact.emailLabel")}: <a href="mailto:hello@example.com" style="color:#2DD4BF;">hello@example.com</a></p>
  <p style="color:#A1A1AA; margin:0;">${t("cms.pageEditor.starters.contact.reply")}</p>
</section>`,
  },
  {
    name: t("cms.pageEditor.starters.stats.name"),
    html: `<section style="display:grid; grid-template-columns:repeat(3,1fr); gap:24px; max-width:960px; margin:0 auto; padding:48px 24px; text-align:center;">
  <div>
    <div style="font-family:monospace; font-size:42px; color:#2DD4BF; font-weight:700;">{{metric:devices_total}}</div>
    <div style="color:#71717A; font-size:13px; text-transform:uppercase; letter-spacing:0.08em;">${t("cms.pageEditor.starters.stats.devicesLabel")}</div>
  </div>
  <div>
    <div style="font-family:monospace; font-size:42px; color:#F5A623; font-weight:700;">{{metric:devices_online}}</div>
    <div style="color:#71717A; font-size:13px; text-transform:uppercase; letter-spacing:0.08em;">${t("cms.pageEditor.starters.stats.onlineLabel")}</div>
  </div>
  <div>
    <div style="font-family:monospace; font-size:42px; color:#F5F5F5; font-weight:700;">4</div>
    <div style="color:#71717A; font-size:13px; text-transform:uppercase; letter-spacing:0.08em;">${t("cms.pageEditor.starters.stats.levelsLabel")}</div>
  </div>
</section>`,
  },
]);

function insertStarter(html: string) {
  const textarea = document.querySelector('textarea.code-editor') as HTMLTextAreaElement | null;
  if (!textarea) {
    editContent.value += "\n\n" + html;
    return;
  }
  const start = textarea.selectionStart || editContent.value.length;
  const end = textarea.selectionEnd || editContent.value.length;
  editContent.value = editContent.value.slice(0, start) + html + editContent.value.slice(end);
  nextTick(() => {
    textarea.focus();
    textarea.setSelectionRange(start + html.length, start + html.length);
  });
}

function insertVar(ref: string) {
  const textarea = document.querySelector('textarea.code-editor') as HTMLTextAreaElement | null;
  if (!textarea) {
    editContent.value += ref;
    return;
  }
  const start = textarea.selectionStart || editContent.value.length;
  const end = textarea.selectionEnd || editContent.value.length;
  editContent.value = editContent.value.slice(0, start) + ref + editContent.value.slice(end);
  nextTick(() => {
    textarea.focus();
    textarea.setSelectionRange(start + ref.length, start + ref.length);
  });
}

function backToList() {
  router.push("/cms");
}

onMounted(loadPage);
</script>

<template>
  <div class="editor-wrap" v-if="!loading && page">
    <header class="editor-head">
      <div class="head-left">
        <button class="btn-ghost" @click="backToList">← {{ t('common.back') }}</button>
        <input v-model="editTitle" class="title-input" :placeholder="t('cms.fields.title')" />
        <div class="slug-row">
          <span class="slug-prefix">/p/</span>
          <input v-model="editSlug" class="slug-input" :placeholder="t('cms.pageEditor.slugPlaceholder')" />
        </div>
      </div>
      <div class="head-right">
        <select v-model="editLayout" class="layout-select">
          <option value="default">{{ t('cms.layout.default') }}</option>
          <option value="landing">{{ t('cms.layout.landing') }}</option>
          <option value="minimal">{{ t('cms.layout.minimal') }}</option>
          <option value="fullscreen">{{ t('cms.layout.fullscreen') }}</option>
        </select>
        <button class="btn-ghost" @click="showMeta = !showMeta">{{ t('cms.meta') }}</button>
        <button class="btn-ghost" @click="showHistory = true">{{ t('cms.pageEditor.historyButton') }}</button>
        <button class="btn-secondary" :disabled="saving" @click="saveDraft">
          {{ saving ? t('cms.pageEditor.savingDots') : t('common.save') }}
        </button>
        <div class="publish-dropdown">
          <button class="btn-primary" @click="publish">{{ t('cms.publish') }}</button>
          <button class="btn-primary dropdown-caret" @click="showPublishMenu = !showPublishMenu" :title="t('cms.pageEditor.publishingOptions')">▾</button>
          <div v-if="showPublishMenu" class="publish-menu" @click.self="showPublishMenu = false">
            <button class="publish-item" @click="publish">
              <span>{{ t('cms.pageEditor.publishMenu.publishNow') }}</span>
              <span class="hint">{{ t('cms.pageEditor.publishMenu.publishNowHint') }}</span>
            </button>
            <button class="publish-item" @click="openSchedule">
              <span>{{ t('cms.pageEditor.publishMenu.schedule') }}</span>
              <span class="hint">{{ t('cms.pageEditor.publishMenu.scheduleHint') }}</span>
            </button>
            <button class="publish-item" @click="saveDraft(); showPublishMenu = false">
              <span>{{ t('cms.pageEditor.publishMenu.saveDraft') }}</span>
              <span class="hint">{{ t('cms.pageEditor.publishMenu.saveDraftHint') }}</span>
            </button>
            <button class="publish-item" v-if="page?.published" @click="unpublishPage">
              <span>{{ t('cms.pageEditor.publishMenu.unpublish') }}</span>
              <span class="hint">{{ t('cms.pageEditor.publishMenu.unpublishHint') }}</span>
            </button>
            <button class="publish-item danger" @click="archivePage">
              <span>{{ t('cms.pageEditor.publishMenu.archive') }}</span>
              <span class="hint">{{ t('cms.pageEditor.publishMenu.archiveHint') }}</span>
            </button>
          </div>
        </div>
        <button class="btn-primary" @click="share">{{ t('cms.share') }}</button>
      </div>
    </header>

    <!-- Stats panel -->
    <div v-if="page" class="stats-panel">
      <div class="stat-item">
        <span class="stat-label">{{ t('cms.pageEditor.stats.views') }}</span>
        <span class="stat-value">{{ page.view_count ?? 0 }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">{{ t('cms.pageEditor.stats.lastViewed') }}</span>
        <span class="stat-value">{{ relativeTime(page.last_viewed_at) }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">{{ t('cms.pageEditor.stats.status') }}</span>
        <span class="stat-value">{{ page.status || (page.published ? t('cms.pageEditor.statusValues.published') : t('cms.pageEditor.statusValues.draft')) }}</span>
      </div>
      <div v-if="page.scheduled_at" class="stat-item">
        <span class="stat-label">{{ t('cms.pageEditor.stats.scheduled') }}</span>
        <span class="stat-value">{{ new Date(page.scheduled_at).toLocaleString() }}</span>
      </div>
    </div>

    <!-- Schedule modal -->
    <div v-if="showScheduleModal" class="modal-overlay" @click.self="showScheduleModal = false">
      <div class="cms-modal">
        <h2>{{ t('cms.pageEditor.scheduleModal.title') }}</h2>
        <p class="schedule-hint">{{ t('cms.pageEditor.scheduleModal.hint') }}</p>
        <label class="field">
          <span>{{ t('cms.pageEditor.scheduleModal.whenLabel') }}</span>
          <input v-model="scheduleDateTime" type="datetime-local" />
        </label>
        <div class="modal-actions">
          <button class="btn-secondary" @click="showScheduleModal = false">{{ t('cms.pageEditor.scheduleModal.cancel') }}</button>
          <button class="btn-primary" @click="submitSchedule">{{ t('cms.pageEditor.scheduleModal.schedule') }}</button>
        </div>
      </div>
    </div>

    <!-- Editor mode tabs -->
    <div class="mode-bar">
      <div class="mode-tabs">
        <button
          type="button"
          class="mode-tab"
          :class="{ active: editorMode === 'blocks' }"
          @click="editorMode = 'blocks'"
        >
          {{ t('cms.pageEditor.modes.blocks') }}
        </button>
        <button
          type="button"
          class="mode-tab"
          :class="{ active: editorMode === 'html' }"
          @click="editorMode = 'html'"
        >
          {{ t('cms.pageEditor.modes.html') }}
        </button>
        <button
          type="button"
          class="mode-tab"
          :class="{ active: editorMode === 'preview' }"
          @click="editorMode = 'preview'"
        >
          {{ t('cms.pageEditor.modes.preview') }}
        </button>
      </div>
      <div v-if="editorMode === 'blocks'" class="mode-actions">
        <button
          type="button"
          class="btn-ghost sm"
          :disabled="!cmsEditor.canUndo"
          @click="cmsEditor.undo()"
          :title="t('cms.pageEditor.undoTitle')"
        >
          {{ t('cms.pageEditor.undoButton') }}
        </button>
        <button
          type="button"
          class="btn-ghost sm"
          :disabled="!cmsEditor.canRedo"
          @click="cmsEditor.redo()"
          :title="t('cms.pageEditor.redoTitle')"
        >
          {{ t('cms.pageEditor.redoButton') }}
        </button>
      </div>
    </div>

    <div v-if="showMeta" class="meta-panel">
      <label class="meta-field">
        <span>{{ t('cms.fields.description') }}</span>
        <input v-model="editDescription" type="text" />
      </label>
      <label class="meta-field">
        <span>{{ t('cms.fields.metaTitle') }}</span>
        <input v-model="editMetaTitle" type="text" />
      </label>
      <label class="meta-field full">
        <span>{{ t('cms.fields.metaDescription') }}</span>
        <textarea v-model="editMetaDescription" rows="2"></textarea>
      </label>
      <label class="meta-field">
        <span>{{ t('cms.fields.ogImage') }}</span>
        <input v-model="editOgImage" type="text" placeholder="https://..." />
      </label>
      <label class="meta-field">
        <span>{{ t('cms.fields.visibility') }}</span>
        <select v-model="editVisibility">
          <option value="private">{{ t('cms.visibility.private') }}</option>
          <option value="public">{{ t('cms.visibility.public') }}</option>
          <option value="embed">{{ t('cms.visibility.embed') }}</option>
        </select>
      </label>
    </div>

    <!-- BLOCK EDITOR MODE -->
    <div v-if="editorMode === 'blocks'" class="blocks-grid">
      <aside class="blocks-lib">
        <BlockLibrary @insert="insertBlock" />
      </aside>
      <main
        class="blocks-canvas-pane"
        @click="cmsEditor.selectBlock(-1)"
      >
        <BlockCanvas
          :blocks="cmsEditor.blocks"
          :selected-index="cmsEditor.selectedIndex"
          @select="(i:number) => cmsEditor.selectBlock(i)"
          @duplicate="(i:number) => cmsEditor.duplicateBlock(i)"
          @delete="(i:number) => cmsEditor.deleteBlock(i)"
          @move-up="(i:number) => cmsEditor.moveBlock(i, i-1)"
          @move-down="(i:number) => cmsEditor.moveBlock(i, i+1)"
        />
      </main>
      <aside class="blocks-props">
        <BlockPropertiesPanel
          :block="cmsEditor.selectedBlock"
          @update="updateBlockProp"
        />
      </aside>
    </div>

    <!-- HTML EDITOR MODE (legacy) -->
    <div v-else-if="editorMode === 'html'" class="html-mode-wrap">
      <div class="view-bar">
        <div class="view-tabs">
          <button
            v-for="m in ['code','split','preview'] as const"
            :key="m"
            class="view-tab"
            :class="{ active: viewMode === m }"
            @click="viewMode = m"
          >
            {{ t(`cms.view.${m}`) }}
          </button>
        </div>
      </div>

      <div class="editor-grid" :class="`view-${viewMode}`">
        <div v-if="viewMode !== 'preview'" class="code-pane">
          <textarea
            class="code-editor"
            v-model="editContent"
            spellcheck="false"
            :placeholder="t('cms.editorPlaceholder')"
          ></textarea>
        </div>

        <div v-if="viewMode !== 'code'" class="preview-pane">
          <iframe
            class="preview-frame"
            :srcdoc="previewHtml"
            sandbox="allow-same-origin"
          ></iframe>
        </div>

        <aside class="sidebar">
          <div class="sidebar-section">
            <h4>{{ t('cms.templateVars') }}</h4>
            <div v-for="g in templateVars" :key="g.group" class="var-group">
              <div class="var-group-head">{{ g.group }}</div>
              <div
                v-for="v in g.items"
                :key="v.ref"
                class="var-row"
                @click="insertVar(v.ref)"
                :title="t('cms.clickToInsert')"
              >
                <code class="var-ref">{{ v.ref }}</code>
                <div class="var-desc">{{ v.desc }}</div>
              </div>
            </div>
          </div>
          <div class="sidebar-section">
            <h4 @click="showStarters = !showStarters" class="collapsible">
              {{ t('cms.starters') }} {{ showStarters ? '−' : '+' }}
            </h4>
            <div v-if="showStarters">
              <button
                v-for="s in starters"
                :key="s.name"
                class="starter-btn"
                @click="insertStarter(s.html)"
              >
                + {{ s.name }}
              </button>
            </div>
          </div>
        </aside>
      </div>
    </div>

    <!-- PREVIEW MODE -->
    <div v-else class="preview-only">
      <iframe
        class="preview-frame"
        :srcdoc="previewHtml"
        sandbox="allow-same-origin"
      ></iframe>
    </div>

    <!-- Version history modal -->
    <PageVersionHistory
      v-if="showHistory && page"
      :page-id="page.id"
      @close="showHistory = false"
      @restored="loadPage"
    />
  </div>
  <div v-else-if="loading" class="loading">{{ t('common.loading') }}</div>
  <div v-else-if="error" class="loading error">{{ error }}</div>
</template>

<style scoped>
.editor-wrap {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #0c0c0b;
}
.editor-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 24px;
  background: #111110;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  gap: 16px;
}
.head-left {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1;
  min-width: 0;
}
.head-right { display: flex; align-items: center; gap: 8px; }
.title-input {
  background: transparent;
  border: none;
  color: #F5F5F5;
  font-size: 20px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
  min-width: 200px;
}
.title-input:focus { outline: none; background: rgba(255,255,255,0.05); }
.slug-row {
  display: flex;
  align-items: center;
  gap: 2px;
  background: rgba(255,255,255,0.04);
  padding: 4px 8px;
  border-radius: 6px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
}
.slug-prefix { color: #71717A; }
.slug-input {
  background: transparent;
  border: none;
  color: #2DD4BF;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  outline: none;
  min-width: 120px;
}
.layout-select {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.1);
  color: #E5E5E5;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 13px;
}
.btn-primary {
  background: #F5A623;
  color: #111110;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  font-size: 13px;
}
.btn-secondary {
  background: rgba(45,212,191,0.15);
  color: #2DD4BF;
  border: 1px solid rgba(45,212,191,0.3);
  padding: 8px 16px;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  font-size: 13px;
}
.btn-ghost {
  background: transparent;
  color: #A1A1AA;
  border: 1px solid rgba(255,255,255,0.1);
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
.btn-ghost:hover { color: #F5F5F5; background: rgba(255,255,255,0.05); }

.meta-panel {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 16px 24px;
  background: rgba(255,255,255,0.03);
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.meta-field { display: flex; flex-direction: column; gap: 4px; }
.meta-field.full { grid-column: 1 / -1; }
.meta-field span {
  font-size: 11px;
  color: #71717A;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.meta-field input, .meta-field select, .meta-field textarea {
  background: #0c0c0b;
  border: 1px solid rgba(255,255,255,0.1);
  color: #E5E5E5;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 13px;
  font-family: inherit;
}

.view-bar {
  padding: 8px 24px;
  background: #0f0f0e;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.view-tabs {
  display: inline-flex;
  gap: 2px;
  background: rgba(255,255,255,0.04);
  padding: 3px;
  border-radius: 8px;
}
.view-tab {
  background: transparent;
  border: none;
  color: #71717A;
  padding: 6px 14px;
  font-size: 12px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
}
.view-tab.active {
  background: rgba(245,166,35,0.2);
  color: #F5A623;
}

.editor-grid {
  display: grid;
  flex: 1;
  overflow: hidden;
  grid-template-columns: 1fr 260px;
}
.editor-grid.view-split { grid-template-columns: 1fr 1fr 260px; }
.editor-grid.view-code { grid-template-columns: 1fr 260px; }
.editor-grid.view-preview { grid-template-columns: 1fr 260px; }

.code-pane {
  display: flex;
  background: #0c0c0b;
  overflow: hidden;
}
.code-editor {
  width: 100%;
  flex: 1;
  background: transparent;
  border: none;
  color: #E5E5E5;
  font-family: 'IBM Plex Mono', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  padding: 20px;
  resize: none;
}
.code-editor:focus { outline: none; }

.preview-pane {
  background: #fff;
  overflow: hidden;
  border-left: 1px solid rgba(255,255,255,0.08);
}
.preview-frame {
  width: 100%;
  height: 100%;
  border: none;
}

.sidebar {
  background: #111110;
  border-left: 1px solid rgba(255,255,255,0.08);
  overflow-y: auto;
  padding: 16px;
}
.sidebar-section {
  margin-bottom: 24px;
}
.sidebar-section h4 {
  font-size: 11px;
  color: #71717A;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0 0 10px;
  font-weight: 600;
}
.sidebar-section h4.collapsible { cursor: pointer; }
.var-group { margin-bottom: 12px; }
.var-group-head {
  font-size: 10px;
  color: #a16207;
  text-transform: uppercase;
  margin-bottom: 4px;
  letter-spacing: 0.05em;
}
.var-row {
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.1s;
}
.var-row:hover { background: rgba(245,166,35,0.1); }
.var-ref {
  display: block;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  color: #F5A623;
}
.var-desc {
  font-size: 11px;
  color: #71717A;
  margin-top: 2px;
}
.starter-btn {
  display: block;
  width: 100%;
  text-align: left;
  background: rgba(45,212,191,0.06);
  color: #2DD4BF;
  border: 1px solid rgba(45,212,191,0.15);
  padding: 8px 12px;
  margin-bottom: 6px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
}
.starter-btn:hover { background: rgba(45,212,191,0.15); }

.loading {
  padding: 80px 24px;
  text-align: center;
  color: #71717A;
}
.loading.error { color: #ef4444; }

/* Editor mode bar (blocks/html/preview) */
.mode-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 24px;
  background: #0f0f0e;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.mode-tabs {
  display: inline-flex;
  gap: 2px;
  background: rgba(255, 255, 255, 0.04);
  padding: 3px;
  border-radius: 8px;
}
.mode-tab {
  background: transparent;
  border: none;
  color: #71717a;
  padding: 6px 18px;
  font-size: 13px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}
.mode-tab.active {
  background: rgba(245, 166, 35, 0.2);
  color: #f5a623;
}
.mode-actions {
  display: flex;
  gap: 6px;
}
.btn-ghost.sm {
  padding: 4px 10px;
  font-size: 12px;
}

/* Blocks grid: library | canvas | properties */
.blocks-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 220px 1fr 280px;
  overflow: hidden;
}
.blocks-lib {
  background: #111110;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  overflow-y: auto;
}
.blocks-canvas-pane {
  background: #0c0c0b;
  overflow-y: auto;
}
.blocks-props {
  background: #111110;
  border-left: 1px solid rgba(255, 255, 255, 0.08);
  overflow-y: auto;
}

/* HTML mode wrapper */
.html-mode-wrap {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}
.html-mode-wrap .editor-grid {
  flex: 1;
}

/* Preview-only mode */
.preview-only {
  flex: 1;
  background: #fff;
  overflow: hidden;
}
.preview-only .preview-frame {
  width: 100%;
  height: 100%;
  border: none;
}

/* Publishing dropdown */
.publish-dropdown {
  position: relative;
  display: flex;
}
.publish-dropdown .btn-primary {
  border-radius: 8px 0 0 8px;
}
.publish-dropdown .dropdown-caret {
  border-radius: 0 8px 8px 0;
  border-left: 1px solid rgba(0, 0, 0, 0.2);
  padding: 10px 12px;
}
.publish-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  min-width: 220px;
  background: #1a1a18;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
  padding: 6px;
  z-index: 100;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.publish-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 10px 12px;
  border: none;
  background: transparent;
  color: #E5E5E5;
  text-align: left;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
.publish-item:hover { background: rgba(255, 255, 255, 0.05); }
.publish-item.danger { color: #fca5a5; }
.publish-item.danger:hover { background: rgba(239, 68, 68, 0.1); }
.publish-item .hint {
  font-size: 11px;
  color: #71717A;
  font-weight: 400;
}

/* Stats panel */
.stats-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 10px 24px;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 12px;
}
.stat-item {
  display: flex;
  gap: 6px;
  align-items: baseline;
}
.stat-label {
  color: #71717A;
  text-transform: uppercase;
  font-size: 10px;
  letter-spacing: 0.05em;
  font-weight: 600;
}
.stat-value {
  color: #F5F5F5;
  font-family: "IBM Plex Mono", monospace;
}

/* Schedule modal */
.schedule-hint {
  color: #A1A1AA;
  font-size: 13px;
  margin: 0 0 16px;
}
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}
/* Sprint 8 R4 CMS fix: was .modal → collided with global .modal overlay
   rule in style.css which added position:fixed inset:0 to the card. */
.cms-modal {
  background: #1a1a18;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 28px;
  min-width: 420px;
  max-width: 500px;
}
.cms-modal h2 {
  margin: 0 0 12px;
  font-size: 20px;
  color: #F5F5F5;
}
.cms-modal .field {
  display: block;
  margin-bottom: 16px;
}
.cms-modal .field span {
  display: block;
  font-size: 11px;
  color: #A1A1AA;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.cms-modal .field input {
  width: 100%;
  background: #111110;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #F5F5F5;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 14px;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
</style>
