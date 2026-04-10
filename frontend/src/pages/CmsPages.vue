<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";

const router = useRouter();
const toast = useToastStore();
const { t } = useI18n();

type CmsPageSummary = {
  id: number;
  slug: string;
  title: string;
  description: string | null;
  layout: string;
  visibility: string;
  published: boolean;
  published_at: string | null;
  updated_at: string;
  created_at: string;
};

const pages = ref<CmsPageSummary[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const filter = ref<"all" | "published" | "drafts" | "public">("all");

// Create modal
const createOpen = ref(false);
const newSlug = ref("");
const newTitle = ref("");
const newLayout = ref<"default" | "landing" | "minimal" | "fullscreen">("default");
const saving = ref(false);

const filteredPages = computed(() => pages.value);

async function loadPages() {
  loading.value = true;
  error.value = null;
  try {
    const url = filter.value === "all"
      ? "/api/v1/cms/pages"
      : `/api/v1/cms/pages?filter=${filter.value}`;
    pages.value = await apiFetch<CmsPageSummary[]>(url);
  } catch (e: any) {
    error.value = e.message || "Failed to load pages";
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  newSlug.value = "";
  newTitle.value = "";
  newLayout.value = "default";
  createOpen.value = true;
}

function slugify(s: string): string {
  return s
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-");
}

function onTitleInput() {
  if (!newSlug.value && newTitle.value) {
    newSlug.value = slugify(newTitle.value);
  }
}

async function createPage() {
  if (!newSlug.value.trim() || !newTitle.value.trim()) {
    toast.show(t('cms.slugTitleRequired'), "error");
    return;
  }
  saving.value = true;
  try {
    const page = await apiFetch<{ id: number }>("/api/v1/cms/pages", {
      method: "POST",
      body: JSON.stringify({
        slug: newSlug.value.trim(),
        title: newTitle.value.trim(),
        layout: newLayout.value,
        content_html: `<h1>${newTitle.value}</h1>\n<p>${t('cms.defaultContent')}</p>`,
        content_mode: "html",
        visibility: "private",
        published: false,
      }),
    });
    toast.show(t('cms.created'), "success");
    createOpen.value = false;
    router.push(`/cms/${page.id}/edit`);
  } catch (e: any) {
    toast.show(e.message || "Failed to create", "error");
  } finally {
    saving.value = false;
  }
}

async function clonePage(id: number) {
  try {
    await apiFetch<any>(`/api/v1/cms/pages/${id}/clone`, { method: "POST" });
    toast.show(t('cms.cloned'), "success");
    await loadPages();
  } catch (e: any) {
    toast.show(e.message, "error");
  }
}

async function deletePage(id: number, title: string) {
  if (!confirm(t('cms.confirmDelete', { title }))) return;
  try {
    await apiFetch(`/api/v1/cms/pages/${id}`, { method: "DELETE" });
    toast.show(t('cms.deleted'), "success");
    await loadPages();
  } catch (e: any) {
    toast.show(e.message, "error");
  }
}

async function togglePublish(p: CmsPageSummary) {
  try {
    const ep = p.published ? "unpublish" : "publish";
    await apiFetch(`/api/v1/cms/pages/${p.id}/${ep}`, { method: "POST" });
    toast.show(p.published ? t('cms.unpublished') : t('cms.published'), "success");
    await loadPages();
  } catch (e: any) {
    toast.show(e.message, "error");
  }
}

async function sharePage(p: CmsPageSummary) {
  try {
    const res = await apiFetch<{ public_token: string }>(`/api/v1/cms/pages/${p.id}/share`, { method: "POST" });
    const url = `${window.location.origin}/p/${p.slug}`;
    try { await navigator.clipboard.writeText(url); } catch {}
    toast.show(`${t('cms.shareCopied')}: ${url}`, "success");
    await loadPages();
  } catch (e: any) {
    toast.show(e.message, "error");
  }
}

onMounted(loadPages);
</script>

<template>
  <div class="page-wrap">
    <header class="page-head">
      <div>
        <h1 class="page-title">{{ t('cms.title') }}</h1>
        <p class="page-sub">{{ t('cms.subtitle') }}</p>
      </div>
      <button class="btn-primary" @click="openCreate">
        + {{ t('cms.createPage') }}
      </button>
    </header>

    <div class="filter-bar">
      <button
        v-for="f in ['all','published','drafts','public'] as const"
        :key="f"
        class="filter-chip"
        :class="{ active: filter === f }"
        @click="filter = f; loadPages()"
      >
        {{ t(`cms.filter.${f}`) }}
      </button>
    </div>

    <div v-if="loading" class="state-msg">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="state-msg error">{{ error }}</div>
    <div v-else-if="filteredPages.length === 0" class="state-msg">
      {{ t('cms.empty') }}
    </div>
    <div v-else class="pages-grid">
      <div
        v-for="p in filteredPages"
        :key="p.id"
        class="page-card"
      >
        <div class="card-thumb" :class="`layout-${p.layout}`">
          <div class="thumb-label">{{ p.layout }}</div>
        </div>
        <div class="card-body">
          <div class="card-head">
            <h3 class="card-title" @click="router.push(`/cms/${p.id}/edit`)">{{ p.title }}</h3>
            <span class="badge" :class="`badge-${p.visibility}`">{{ t(`cms.visibility.${p.visibility}`) }}</span>
          </div>
          <div class="card-slug">/{{ p.slug }}</div>
          <p v-if="p.description" class="card-desc">{{ p.description }}</p>
          <div class="card-meta">
            <span v-if="p.published" class="pub-tag">✓ {{ t('cms.published') }}</span>
            <span v-else class="draft-tag">{{ t('cms.draft') }}</span>
          </div>
        </div>
        <div class="card-actions">
          <button class="a-btn" @click="router.push(`/cms/${p.id}/edit`)">{{ t('common.edit') }}</button>
          <button class="a-btn" @click="togglePublish(p)">
            {{ p.published ? t('cms.unpublish') : t('cms.publish') }}
          </button>
          <button class="a-btn" @click="sharePage(p)">{{ t('cms.share') }}</button>
          <button class="a-btn" @click="clonePage(p.id)">{{ t('cms.clone') }}</button>
          <button class="a-btn danger" @click="deletePage(p.id, p.title)">{{ t('common.delete') }}</button>
        </div>
      </div>
    </div>

    <!-- Create Modal -->
    <div v-if="createOpen" class="modal-overlay" @click.self="createOpen = false">
      <div class="modal">
        <h2>{{ t('cms.createPage') }}</h2>
        <label class="field">
          <span>{{ t('cms.fields.title') }}</span>
          <input v-model="newTitle" @input="onTitleInput" type="text" :placeholder="t('cms.fields.titlePlaceholder')" />
        </label>
        <label class="field">
          <span>{{ t('cms.fields.slug') }}</span>
          <input v-model="newSlug" type="text" placeholder="my-page" />
        </label>
        <label class="field">
          <span>{{ t('cms.fields.layout') }}</span>
          <select v-model="newLayout">
            <option value="default">{{ t('cms.layout.default') }}</option>
            <option value="landing">{{ t('cms.layout.landing') }}</option>
            <option value="minimal">{{ t('cms.layout.minimal') }}</option>
            <option value="fullscreen">{{ t('cms.layout.fullscreen') }}</option>
          </select>
        </label>
        <div class="modal-actions">
          <button class="btn-secondary" @click="createOpen = false">{{ t('common.cancel') }}</button>
          <button class="btn-primary" :disabled="saving" @click="createPage">
            {{ saving ? t('common.loading') : t('common.create') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-wrap {
  padding: 24px 32px;
  max-width: 1400px;
  margin: 0 auto;
}
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}
.page-title {
  font-size: 28px;
  font-weight: 700;
  color: #F5F5F5;
  margin: 0 0 4px;
}
.page-sub {
  color: #A1A1AA;
  margin: 0;
  font-size: 14px;
}
.btn-primary {
  background: #F5A623;
  color: #111110;
  border: none;
  padding: 10px 18px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  font-size: 14px;
}
.btn-primary:hover { background: #e89915; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary {
  background: transparent;
  color: #E5E5E5;
  border: 1px solid rgba(255,255,255,0.15);
  padding: 10px 18px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}
.filter-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}
.filter-chip {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  color: #A1A1AA;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 13px;
  cursor: pointer;
}
.filter-chip.active {
  background: rgba(245,166,35,0.15);
  border-color: #F5A623;
  color: #F5A623;
}
.state-msg {
  padding: 48px 24px;
  text-align: center;
  color: #71717A;
}
.state-msg.error { color: #ef4444; }
.pages-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}
.page-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  overflow: hidden;
  transition: border-color 0.15s, transform 0.15s;
}
.page-card:hover {
  border-color: rgba(245,166,35,0.3);
  transform: translateY(-2px);
}
.card-thumb {
  height: 120px;
  background: linear-gradient(135deg, #1f1f1e 0%, #2a2a28 100%);
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.card-thumb.layout-landing { background: linear-gradient(135deg, rgba(245,166,35,0.2), rgba(45,212,191,0.1)); }
.card-thumb.layout-fullscreen { background: linear-gradient(135deg, #111110, #1f1f1e); }
.card-thumb.layout-minimal { background: #1a1a18; }
.thumb-label {
  font-family: 'IBM Plex Mono', monospace;
  color: rgba(255,255,255,0.4);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}
.card-body { padding: 16px; }
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 4px;
}
.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #F5F5F5;
  margin: 0;
  cursor: pointer;
}
.card-title:hover { color: #F5A623; }
.card-slug {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  color: #71717A;
  margin-bottom: 8px;
}
.card-desc {
  color: #A1A1AA;
  font-size: 13px;
  line-height: 1.5;
  margin: 0 0 12px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.card-meta {
  font-size: 12px;
}
.pub-tag { color: #2DD4BF; }
.draft-tag { color: #71717A; }
.badge {
  font-size: 10px;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 999px;
  font-weight: 600;
  letter-spacing: 0.05em;
}
.badge-private { background: rgba(255,255,255,0.08); color: #A1A1AA; }
.badge-public { background: rgba(45,212,191,0.15); color: #2DD4BF; }
.badge-embed { background: rgba(245,166,35,0.15); color: #F5A623; }
.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 12px 16px;
  border-top: 1px solid rgba(255,255,255,0.06);
  background: rgba(0,0,0,0.2);
}
.a-btn {
  background: transparent;
  color: #A1A1AA;
  border: 1px solid rgba(255,255,255,0.08);
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 6px;
  cursor: pointer;
}
.a-btn:hover { background: rgba(255,255,255,0.05); color: #F5F5F5; }
.a-btn.danger:hover { color: #ef4444; border-color: #ef4444; }

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal {
  background: #1a1a18;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px;
  padding: 28px;
  min-width: 420px;
  max-width: 500px;
}
.modal h2 {
  margin: 0 0 20px;
  font-size: 20px;
  color: #F5F5F5;
}
.field {
  display: block;
  margin-bottom: 16px;
}
.field span {
  display: block;
  font-size: 12px;
  color: #A1A1AA;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.field input, .field select {
  width: 100%;
  background: #111110;
  border: 1px solid rgba(255,255,255,0.1);
  color: #F5F5F5;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 14px;
}
.field input:focus, .field select:focus {
  outline: none;
  border-color: #F5A623;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 24px;
}
</style>
