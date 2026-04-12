<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";
import TreeNode from "../components/cms/CmsPageTreeNode.vue";
import UInfoTooltip from "../components/ui/UInfoTooltip.vue";

const router = useRouter();
const toast = useToastStore();
const { t, tm, rt } = useI18n();

type CmsPageSummary = {
  id: number;
  slug: string;
  title: string;
  description: string | null;
  layout: string;
  visibility: string;
  published: boolean;
  published_at: string | null;
  status?: string;
  scheduled_at?: string | null;
  view_count?: number;
  last_viewed_at?: string | null;
  updated_at: string;
  created_at: string;
};

type SearchResult = {
  id: number;
  slug: string;
  title: string;
  layout: string;
  visibility: string;
  published: boolean;
  updated_at: string;
  snippet: string;
};

type CmsPageTreeNode = {
  id: number;
  slug: string;
  title: string;
  layout: string;
  visibility: string;
  published: boolean;
  parent_id: number | null;
  menu_order: number;
  show_in_menu: boolean;
  children: CmsPageTreeNode[];
};

const pages = ref<CmsPageSummary[]>([]);
const tree = ref<CmsPageTreeNode[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const filter = ref<"all" | "published" | "drafts" | "public">("all");
const viewMode = ref<"grid" | "tree">("grid");
const expandedIds = ref<Set<number>>(new Set());

// Drag-drop state (HTML5 DnD)
const dragNodeId = ref<number | null>(null);
const dropTargetId = ref<number | null>(null);
const dropAsChild = ref(false);

// Create modal
const createOpen = ref(false);
const newSlug = ref("");
const newTitle = ref("");
const newLayout = ref<"default" | "landing" | "minimal" | "fullscreen">("default");
const newParentId = ref<number | null>(null);
const saving = ref(false);

// Template picker
type CmsTemplate = {
  id: string;
  name: string;
  description: string;
  category: string;
  thumbnail: string;
  layout: string;
  content_mode: string;
};
const templatePickerOpen = ref(false);
const templates = ref<CmsTemplate[]>([]);
const templatesLoading = ref(false);
const selectedTemplate = ref<CmsTemplate | null>(null);

const filteredPages = computed(() => pages.value);

// Full-text search state
const searchQuery = ref("");
const searchResults = ref<SearchResult[]>([]);
const searchLoading = ref(false);
let searchTimer: ReturnType<typeof setTimeout> | null = null;

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer);
  const q = searchQuery.value.trim();
  if (!q) {
    searchResults.value = [];
    return;
  }
  searchTimer = setTimeout(async () => {
    searchLoading.value = true;
    try {
      const res = await apiFetch<{ results: SearchResult[] }>(
        `/api/v1/cms/search?q=${encodeURIComponent(q)}`
      );
      searchResults.value = res.results || [];
    } catch (e: any) {
      toast.show(e.message || t('cms.pages.searchFailed'), "error");
    } finally {
      searchLoading.value = false;
    }
  }, 300);
}

function clearSearch() {
  searchQuery.value = "";
  searchResults.value = [];
}

// Export / Import
async function exportPage(p: CmsPageSummary) {
  try {
    const data = await apiFetch<any>(`/api/v1/cms/pages/${p.id}/export`);
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `cms-page-${p.slug || p.id}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    toast.show(t('cms.pages.exportedToast'), "success");
  } catch (e: any) {
    toast.show(e.message || t('cms.pages.exportFailed'), "error");
  }
}

const importFileInput = ref<HTMLInputElement | null>(null);
function triggerImport() {
  importFileInput.value?.click();
}
async function onImportFile(ev: Event) {
  const target = ev.target as HTMLInputElement;
  const file = target.files?.[0];
  target.value = "";
  if (!file) return;
  try {
    const text = await file.text();
    const data = JSON.parse(text);
    const created = await apiFetch<{ id: number; slug: string }>("/api/v1/cms/pages/import", {
      method: "POST",
      body: JSON.stringify(data),
    });
    toast.show(t('cms.pages.importedToast', { slug: created.slug }), "success");
    await loadPages();
  } catch (e: any) {
    toast.show(e.message || t('cms.pages.importFailed'), "error");
  }
}

async function loadPages() {
  loading.value = true;
  error.value = null;
  try {
    const url = filter.value === "all"
      ? "/api/v1/cms/pages"
      : `/api/v1/cms/pages?filter=${filter.value}`;
    pages.value = await apiFetch<CmsPageSummary[]>(url);
    if (viewMode.value === "tree") {
      await loadTree();
    }
  } catch (e: any) {
    error.value = e.message || t('cms.pages.loadFailed');
  } finally {
    loading.value = false;
  }
}

async function loadTree() {
  try {
    tree.value = await apiFetch<CmsPageTreeNode[]>("/api/v1/cms/pages/tree");
    // Expand the first level by default
    for (const node of tree.value) {
      expandedIds.value.add(node.id);
    }
  } catch (e: any) {
    error.value = e.message || t('cms.pages.loadTreeFailed');
  }
}

async function switchView(mode: "grid" | "tree") {
  viewMode.value = mode;
  if (mode === "tree" && tree.value.length === 0) {
    await loadTree();
  }
}

function toggleExpand(id: number) {
  const next = new Set(expandedIds.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  expandedIds.value = next;
}

function addChildPage(parentId: number) {
  openCreate();
  newParentId.value = parentId;
}

// HTML5 drag-drop handlers
function onDragStart(ev: DragEvent, node: CmsPageTreeNode) {
  dragNodeId.value = node.id;
  if (ev.dataTransfer) {
    ev.dataTransfer.effectAllowed = "move";
    ev.dataTransfer.setData("text/plain", String(node.id));
  }
}
function onDragOver(ev: DragEvent, node: CmsPageTreeNode, asChild = false) {
  if (dragNodeId.value === null || dragNodeId.value === node.id) return;
  ev.preventDefault();
  dropTargetId.value = node.id;
  dropAsChild.value = asChild;
}
function onDragLeave() {
  dropTargetId.value = null;
}
async function onDrop(ev: DragEvent, target: CmsPageTreeNode) {
  ev.preventDefault();
  const sourceId = dragNodeId.value;
  dragNodeId.value = null;
  dropTargetId.value = null;
  if (sourceId === null || sourceId === target.id) return;
  const newParent = dropAsChild.value ? target.id : target.parent_id;
  try {
    await apiFetch(`/api/v1/cms/pages/${sourceId}/move`, {
      method: "PUT",
      body: JSON.stringify({
        parent_id: newParent,
        menu_order: (target.menu_order || 0) + 1,
      }),
    });
    toast.show(t('cms.moved'), "success");
    await loadTree();
  } catch (e: any) {
    toast.show(e.message || t('cms.pages.moveFailed'), "error");
  }
}

async function openTemplatePicker() {
  selectedTemplate.value = null;
  templatePickerOpen.value = true;
  if (templates.value.length === 0) {
    templatesLoading.value = true;
    try {
      const res = await apiFetch<{ templates: CmsTemplate[] }>("/api/v1/cms/templates");
      templates.value = res.templates || [];
    } catch (e: any) {
      toast.show(e.message || t('cms.pages.templatesLoadFailed'), "error");
    } finally {
      templatesLoading.value = false;
    }
  }
}

function selectTemplate(tpl: CmsTemplate | null) {
  selectedTemplate.value = tpl;
  templatePickerOpen.value = false;
  newSlug.value = "";
  newTitle.value = "";
  newLayout.value = (tpl?.layout as any) || "default";
  newParentId.value = null;
  createOpen.value = true;
}

function openCreate() {
  // Default create flow: show template picker first
  openTemplatePicker();
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
    let page: { id: number };
    if (selectedTemplate.value) {
      // Create from template
      const params = new URLSearchParams({
        slug: newSlug.value.trim(),
        title: newTitle.value.trim(),
      });
      page = await apiFetch<{ id: number }>(
        `/api/v1/cms/pages/from-template/${selectedTemplate.value.id}?${params}`,
        { method: "POST" }
      );
    } else {
      page = await apiFetch<{ id: number }>("/api/v1/cms/pages", {
        method: "POST",
        body: JSON.stringify({
          slug: newSlug.value.trim(),
          title: newTitle.value.trim(),
          layout: newLayout.value,
          content_html: `<h1>${newTitle.value}</h1>\n<p>${t('cms.defaultContent')}</p>`,
          content_mode: "html",
          visibility: "private",
          published: false,
          parent_id: newParentId.value,
        }),
      });
    }
    toast.show(t('cms.created'), "success");
    createOpen.value = false;
    selectedTemplate.value = null;
    router.push(`/cms/${page.id}/edit`);
  } catch (e: any) {
    toast.show(e.message || t('cms.pages.createFailed'), "error");
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
        <div class="flex items-center">
          <h1 class="page-title">{{ t('cms.title') }}</h1>
          <UInfoTooltip
            :title="t('infoTooltips.cmsPages.title')"
            :items="tm('infoTooltips.cmsPages.items').map((i: any) => rt(i))"
            tourId="cms-overview"
          />
        </div>
        <p class="page-sub">{{ t('cms.subtitle') }}</p>
      </div>
      <div class="head-actions">
        <button class="btn-secondary" @click="triggerImport">{{ t('cms.pages.importButton') }}</button>
        <input
          ref="importFileInput"
          type="file"
          accept="application/json,.json"
          style="display:none"
          @change="onImportFile"
        />
        <button class="btn-primary" @click="openCreate">
          + {{ t('cms.createPage') }}
        </button>
      </div>
    </header>

    <!-- Full-text search bar -->
    <div class="search-wrap">
      <svg class="search-icon" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
      </svg>
      <input
        v-model="searchQuery"
        type="search"
        class="search-input"
        :placeholder="t('cms.pages.searchPlaceholder')"
        @input="onSearchInput"
      />
      <button v-if="searchQuery" class="search-clear" @click="clearSearch" :title="t('cms.pages.searchClearTitle')">×</button>
    </div>

    <!-- Search results -->
    <div v-if="searchQuery.trim()" class="search-results-wrap">
      <div v-if="searchLoading" class="state-msg small">{{ t('cms.pages.searching') }}</div>
      <div v-else-if="searchResults.length === 0" class="state-msg small">
        {{ t('cms.pages.searchNoResults', { query: searchQuery }) }}
      </div>
      <div v-else class="search-results">
        <div class="search-count">
          {{ searchResults.length === 1
            ? t('cms.pages.searchResultCountSingle', { n: searchResults.length })
            : t('cms.pages.searchResultCountPlural', { n: searchResults.length }) }}
        </div>
        <button
          v-for="r in searchResults"
          :key="r.id"
          class="search-result-card"
          @click="router.push(`/cms/${r.id}/edit`)"
        >
          <div class="sr-head">
            <span class="sr-title">{{ r.title }}</span>
            <span class="sr-slug">/{{ r.slug }}</span>
          </div>
          <div v-if="r.snippet" class="sr-snippet">{{ r.snippet }}</div>
        </button>
      </div>
    </div>

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
      <div class="view-toggle">
        <button
          class="view-btn"
          :class="{ active: viewMode === 'grid' }"
          @click="switchView('grid')"
          type="button"
          :title="t('cms.pages.viewGridTitle')"
        >
          ▤ {{ t('cms.pages.viewGrid') }}
        </button>
        <button
          class="view-btn"
          :class="{ active: viewMode === 'tree' }"
          @click="switchView('tree')"
          type="button"
          :title="t('cms.pages.viewTreeTitle')"
        >
          ▸ {{ t('cms.pages.viewTree') }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="state-msg">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="state-msg error">{{ error }}</div>

    <!-- Tree view -->
    <div v-else-if="viewMode === 'tree'" class="tree-wrap">
      <div v-if="tree.length === 0" class="state-msg">{{ t('cms.empty') }}</div>
      <ul v-else class="tree-list">
        <TreeNode
          v-for="node in tree"
          :key="node.id"
          :node="node"
          :expanded-ids="expandedIds"
          :drop-target-id="dropTargetId"
          :drop-as-child="dropAsChild"
          @toggle="toggleExpand"
          @edit="(id: number) => router.push(`/cms/${id}/edit`)"
          @add-child="addChildPage"
          @drag-start="onDragStart"
          @drag-over="onDragOver"
          @drag-leave="onDragLeave"
          @drop="onDrop"
        />
      </ul>
    </div>

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
            <span v-if="p.published" class="pub-tag">{{ t('cms.pages.publishedCheck', { label: t('cms.published') }) }}</span>
            <span v-else-if="p.status === 'scheduled'" class="sched-tag">⏰ {{ t('cms.pages.tagScheduled') }}</span>
            <span v-else-if="p.status === 'archived'" class="arch-tag">{{ t('cms.pages.tagArchived') }}</span>
            <span v-else class="draft-tag">{{ t('cms.draft') }}</span>
            <span v-if="(p.view_count ?? 0) > 0" class="views-tag" :title="t('cms.pages.viewsTitle')">
              👁 {{ t('cms.pages.viewsLabel', { n: p.view_count }) }}
            </span>
          </div>
        </div>
        <div class="card-actions">
          <button class="a-btn" @click="router.push(`/cms/${p.id}/edit`)">{{ t('common.edit') }}</button>
          <button class="a-btn" @click="togglePublish(p)">
            {{ p.published ? t('cms.unpublish') : t('cms.publish') }}
          </button>
          <button class="a-btn" @click="sharePage(p)">{{ t('cms.share') }}</button>
          <button class="a-btn" @click="clonePage(p.id)">{{ t('cms.clone') }}</button>
          <button class="a-btn" @click="exportPage(p)" :title="t('cms.pages.exportTitle')">{{ t('cms.pages.exportButton') }}</button>
          <button class="a-btn danger" @click="deletePage(p.id, p.title)">{{ t('common.delete') }}</button>
        </div>
      </div>
    </div>

    <!-- Template Picker Modal -->
    <div v-if="templatePickerOpen" class="modal-overlay" @click.self="templatePickerOpen = false">
      <div class="cms-modal tpl-modal">
        <div class="tpl-head">
          <h2>{{ t('cms.pages.templatePickerTitle') }}</h2>
          <button class="close-x" @click="templatePickerOpen = false">×</button>
        </div>
        <p class="tpl-sub">{{ t('cms.pages.templatePickerSubtitle') }}</p>
        <div v-if="templatesLoading" class="state-msg">{{ t('cms.pages.templatesLoading') }}</div>
        <div v-else class="tpl-grid">
          <button class="tpl-card blank" @click="selectTemplate(null)">
            <div class="tpl-thumb blank-thumb">+</div>
            <div class="tpl-body">
              <h3>{{ t('cms.pages.templateBlankTitle') }}</h3>
              <p>{{ t('cms.pages.templateBlankSubtitle') }}</p>
            </div>
          </button>
          <button
            v-for="tpl in templates"
            :key="tpl.id"
            class="tpl-card"
            @click="selectTemplate(tpl)"
          >
            <div class="tpl-thumb" :class="`layout-${tpl.layout}`">
              <div class="thumb-label">{{ tpl.layout }}</div>
            </div>
            <div class="tpl-body">
              <h3>{{ tpl.name }}</h3>
              <p>{{ tpl.description }}</p>
              <span class="tpl-cat">{{ tpl.category }}</span>
            </div>
          </button>
        </div>
      </div>
    </div>

    <!-- Create Modal -->
    <div v-if="createOpen" class="modal-overlay" @click.self="createOpen = false">
      <div class="cms-modal">
        <h2>
          {{ t('cms.createPage') }}
          <span v-if="selectedTemplate" class="tpl-tag">{{ t('cms.pages.createFromTemplate', { name: selectedTemplate.name }) }}</span>
        </h2>
        <label class="field">
          <span>{{ t('cms.fields.title') }}</span>
          <input v-model="newTitle" @input="onTitleInput" type="text" :placeholder="t('cms.fields.titlePlaceholder')" />
        </label>
        <label class="field">
          <span>{{ t('cms.fields.slug') }}</span>
          <input v-model="newSlug" type="text" placeholder="my-page" />
        </label>
        <label v-if="!selectedTemplate" class="field">
          <span>{{ t('cms.fields.layout') }}</span>
          <select v-model="newLayout">
            <option value="default">{{ t('cms.layout.default') }}</option>
            <option value="landing">{{ t('cms.layout.landing') }}</option>
            <option value="minimal">{{ t('cms.layout.minimal') }}</option>
            <option value="fullscreen">{{ t('cms.layout.fullscreen') }}</option>
          </select>
        </label>
        <label v-if="!selectedTemplate" class="field">
          <span>{{ t('cms.pages.parentPageOptional') }}</span>
          <select v-model="newParentId">
            <option :value="null">{{ t('cms.pages.parentNoneOption') }}</option>
            <option v-for="p in pages" :key="p.id" :value="p.id">
              {{ p.title }}
            </option>
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
  align-items: center;
}
.view-toggle {
  margin-left: auto;
  display: flex;
  gap: 4px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  padding: 2px;
}
.view-btn {
  background: transparent;
  color: #A1A1AA;
  border: none;
  padding: 6px 12px;
  font-size: 12px;
  border-radius: 6px;
  cursor: pointer;
}
.view-btn.active {
  background: rgba(245,166,35,0.2);
  color: #F5A623;
}
.tree-wrap {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  padding: 12px 16px;
}
.tree-list {
  list-style: none;
  padding: 0;
  margin: 0;
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
.state-msg.small { padding: 20px; font-size: 13px; }
.head-actions {
  display: flex;
  gap: 8px;
}
.search-wrap {
  position: relative;
  margin-bottom: 16px;
}
.search-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  color: #71717A;
  pointer-events: none;
}
.search-input {
  width: 100%;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.1);
  color: #F5F5F5;
  padding: 12px 40px;
  border-radius: 10px;
  font-size: 14px;
}
.search-input:focus {
  outline: none;
  border-color: #F5A623;
  background: rgba(255,255,255,0.06);
}
.search-clear {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  color: #A1A1AA;
  border: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 20px;
  line-height: 1;
}
.search-clear:hover { color: #F5F5F5; background: rgba(255,255,255,0.08); }
.search-results-wrap {
  margin-bottom: 20px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  padding: 8px;
}
.search-count {
  font-size: 11px;
  text-transform: uppercase;
  color: #71717A;
  letter-spacing: 0.05em;
  padding: 6px 10px;
}
.search-results {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.search-result-card {
  text-align: left;
  background: transparent;
  border: 1px solid transparent;
  color: #E5E5E5;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.search-result-card:hover {
  background: rgba(255,255,255,0.04);
  border-color: rgba(245,166,35,0.2);
}
.sr-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: baseline;
}
.sr-title { font-weight: 600; font-size: 14px; color: #F5F5F5; }
.sr-slug {
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
  color: #71717A;
}
.sr-snippet {
  margin-top: 4px;
  font-size: 12px;
  color: #A1A1AA;
  line-height: 1.5;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.sched-tag { color: #F5A623; }
.arch-tag { color: #71717A; text-transform: uppercase; font-size: 10px; letter-spacing: 0.05em; }
.views-tag {
  color: #71717A;
  margin-left: 8px;
  font-size: 11px;
}
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
/* Sprint 8 R4 CMS fix: was .modal which collided with the global .modal
   overlay rule in style.css (position:fixed inset:0 display:flex). The
   CMS pages use .modal-overlay for the overlay and .modal for the CARD
   — exactly the inverse of the global pattern — so the global
   position:fixed was leaking onto the card and collapsing the layout.
   Renamed the card class to .cms-modal. Applies to the plain create
   modal AND the .tpl-modal template picker variant. */
.cms-modal {
  background: #1a1a18;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px;
  padding: 28px;
  min-width: 420px;
  max-width: 500px;
}
.cms-modal h2 {
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

/* Template picker */
.tpl-modal {
  min-width: 720px;
  max-width: 900px;
  max-height: 80vh;
  overflow-y: auto;
}
.tpl-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.tpl-head h2 { margin: 0; }
.close-x {
  background: transparent;
  color: #71717A;
  border: none;
  font-size: 26px;
  cursor: pointer;
  line-height: 1;
  padding: 0 8px;
}
.close-x:hover { color: #ef4444; }
.tpl-sub {
  color: #A1A1AA;
  font-size: 13px;
  margin: 0 0 20px;
}
.tpl-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}
.tpl-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  text-align: left;
  padding: 0;
  transition: border-color 0.15s, transform 0.15s;
  color: inherit;
  font-family: inherit;
}
.tpl-card:hover {
  border-color: #F5A623;
  transform: translateY(-2px);
}
.tpl-thumb {
  height: 88px;
  background: linear-gradient(135deg, #1f1f1e 0%, #2a2a28 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}
.tpl-thumb.layout-landing { background: linear-gradient(135deg, rgba(245,166,35,0.2), rgba(45,212,191,0.1)); }
.tpl-thumb.layout-fullscreen { background: linear-gradient(135deg, #111110, #1f1f1e); }
.tpl-thumb.layout-minimal { background: #1a1a18; }
.tpl-thumb .thumb-label {
  font-family: 'IBM Plex Mono', monospace;
  color: rgba(255,255,255,0.4);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}
.blank-thumb {
  color: #F5A623;
  font-size: 36px;
  font-weight: 300;
}
.tpl-body { padding: 12px 14px 14px; }
.tpl-body h3 {
  font-size: 14px;
  color: #F5F5F5;
  margin: 0 0 4px;
}
.tpl-body p {
  color: #A1A1AA;
  font-size: 12px;
  margin: 0 0 8px;
  line-height: 1.4;
}
.tpl-cat {
  display: inline-block;
  font-size: 10px;
  color: #2DD4BF;
  background: rgba(45,212,191,0.1);
  padding: 2px 8px;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.tpl-tag {
  display: inline-block;
  font-size: 11px;
  color: #F5A623;
  background: rgba(245,166,35,0.1);
  padding: 2px 10px;
  border-radius: 999px;
  margin-left: 10px;
  font-weight: 500;
  vertical-align: middle;
}
</style>
