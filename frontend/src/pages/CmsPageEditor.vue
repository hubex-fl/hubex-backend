<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";

const route = useRoute();
const router = useRouter();
const toast = useToastStore();
const { t } = useI18n();

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

// View mode
const viewMode = ref<"code" | "split" | "preview">("split");
const previewHtml = ref("");
const showMeta = ref(false);
const showStarters = ref(true);

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
    await renderPreview();
  } catch (e: any) {
    error.value = e.message || "Failed to load";
  } finally {
    loading.value = false;
  }
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
      }),
    });
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
const templateVars = [
  { group: "Metrics", items: [
    { ref: "{{metric:devices_total}}", desc: "Total devices" },
    { ref: "{{metric:devices_online}}", desc: "Devices currently online" },
  ]},
  { group: "Variables", items: [
    { ref: "{{variable:your_key}}", desc: "Latest value of a variable" },
    { ref: "{{variable:device_uid:key}}", desc: "Latest value on a specific device" },
  ]},
  { group: "Devices", items: [
    { ref: "{{device:uid:name}}", desc: "Device display name" },
    { ref: "{{device:uid:status}}", desc: "online / offline" },
  ]},
  { group: "Timestamps", items: [
    { ref: "{{timestamp:date}}", desc: "Current date" },
    { ref: "{{timestamp:iso}}", desc: "Full ISO timestamp" },
  ]},
];

// HTML starter blocks
const starters = [
  {
    name: "Hero Section",
    html: `<section style="padding:80px 24px; text-align:center; background:radial-gradient(ellipse at top, rgba(245,166,35,0.1), transparent);">
  <h1 style="font-size:56px; font-weight:800; margin:0 0 16px; color:#F5F5F5;">Your Hero Title</h1>
  <p style="font-size:20px; color:#A1A1AA; max-width:640px; margin:0 auto 32px;">A compelling subtitle that explains the value proposition.</p>
  <a href="#" style="display:inline-block; padding:14px 28px; background:#F5A623; color:#111110; border-radius:10px; font-weight:600; text-decoration:none;">Get Started</a>
</section>`,
  },
  {
    name: "Feature Grid",
    html: `<section style="max-width:1200px; margin:0 auto; padding:64px 24px; display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:24px;">
  <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:28px;">
    <h3 style="color:#F5A623; margin:0 0 12px;">Feature 1</h3>
    <p style="color:#A1A1AA; margin:0;">Description of the first feature.</p>
  </div>
  <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:28px;">
    <h3 style="color:#2DD4BF; margin:0 0 12px;">Feature 2</h3>
    <p style="color:#A1A1AA; margin:0;">Description of the second feature.</p>
  </div>
  <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:28px;">
    <h3 style="color:#F5A623; margin:0 0 12px;">Feature 3</h3>
    <p style="color:#A1A1AA; margin:0;">Description of the third feature.</p>
  </div>
</section>`,
  },
  {
    name: "CTA",
    html: `<section style="padding:60px 24px; text-align:center; background:rgba(245,166,35,0.08); border-top:1px solid rgba(245,166,35,0.2); border-bottom:1px solid rgba(245,166,35,0.2);">
  <h2 style="font-size:32px; margin:0 0 12px; color:#F5F5F5;">Ready to start?</h2>
  <p style="color:#A1A1AA; margin:0 0 24px;">Join thousands of users already building with HubEx.</p>
  <a href="#" style="display:inline-block; padding:12px 28px; background:#F5A623; color:#111110; border-radius:8px; font-weight:600; text-decoration:none;">Try Free</a>
</section>`,
  },
  {
    name: "About",
    html: `<section style="max-width:900px; margin:0 auto; padding:64px 24px;">
  <h2 style="font-size:36px; color:#F5F5F5; margin:0 0 24px;">About Us</h2>
  <p style="color:#A1A1AA; line-height:1.7; font-size:17px;">Tell your story here. Explain the mission, the team, the values.</p>
</section>`,
  },
  {
    name: "Contact",
    html: `<section style="max-width:720px; margin:0 auto; padding:64px 24px;">
  <h2 style="color:#F5F5F5; margin:0 0 16px;">Contact</h2>
  <p style="color:#A1A1AA; margin:0 0 8px;">Email: <a href="mailto:hello@example.com" style="color:#2DD4BF;">hello@example.com</a></p>
  <p style="color:#A1A1AA; margin:0;">We usually reply within 24 hours.</p>
</section>`,
  },
  {
    name: "Stats",
    html: `<section style="display:grid; grid-template-columns:repeat(3,1fr); gap:24px; max-width:960px; margin:0 auto; padding:48px 24px; text-align:center;">
  <div>
    <div style="font-family:monospace; font-size:42px; color:#2DD4BF; font-weight:700;">{{metric:devices_total}}</div>
    <div style="color:#71717A; font-size:13px; text-transform:uppercase; letter-spacing:0.08em;">Devices</div>
  </div>
  <div>
    <div style="font-family:monospace; font-size:42px; color:#F5A623; font-weight:700;">{{metric:devices_online}}</div>
    <div style="color:#71717A; font-size:13px; text-transform:uppercase; letter-spacing:0.08em;">Online</div>
  </div>
  <div>
    <div style="font-family:monospace; font-size:42px; color:#F5F5F5; font-weight:700;">4</div>
    <div style="color:#71717A; font-size:13px; text-transform:uppercase; letter-spacing:0.08em;">Levels</div>
  </div>
</section>`,
  },
];

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
          <input v-model="editSlug" class="slug-input" placeholder="page-slug" />
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
        <button class="btn-secondary" :disabled="saving" @click="saveDraft">
          {{ saving ? '...' : t('common.save') }}
        </button>
        <button class="btn-primary" @click="publish">{{ t('cms.publish') }}</button>
        <button class="btn-primary" @click="share">{{ t('cms.share') }}</button>
      </div>
    </header>

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
      <!-- Code editor -->
      <div v-if="viewMode !== 'preview'" class="code-pane">
        <textarea
          class="code-editor"
          v-model="editContent"
          spellcheck="false"
          :placeholder="t('cms.editorPlaceholder')"
        ></textarea>
      </div>

      <!-- Preview -->
      <div v-if="viewMode !== 'code'" class="preview-pane">
        <iframe
          class="preview-frame"
          :srcdoc="previewHtml"
          sandbox="allow-same-origin"
        ></iframe>
      </div>

      <!-- Sidebar: variables + starters -->
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
</style>
