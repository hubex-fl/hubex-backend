<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const toast = useToastStore();

type ItemType = "page" | "link" | "section" | "divider";

type MenuItem = {
  id: string;
  type: ItemType;
  label?: string;
  url?: string;
  page_id?: number;
  target?: "_self" | "_blank";
  children?: MenuItem[];
};

type Menu = {
  id: number;
  name: string;
  location: string;
  items: MenuItem[] | null;
};

type PageOption = {
  id: number;
  slug: string;
  title: string;
  published: boolean;
};

const menuId = computed(() => Number(route.params.id));
const menu = ref<Menu | null>(null);
const items = ref<MenuItem[]>([]);
const loading = ref(true);
const saving = ref(false);
const pages = ref<PageOption[]>([]);
const selectedId = ref<string | null>(null);

// Drag state
const dragItemId = ref<string | null>(null);
const dropTargetId = ref<string | null>(null);
const dropAsChild = ref(false);

function uid(): string {
  return "i_" + Math.random().toString(36).slice(2, 10);
}

function assignIds(list: MenuItem[]): MenuItem[] {
  return list.map((item) => ({
    ...item,
    id: item.id || uid(),
    children: item.children ? assignIds(item.children) : [],
  }));
}

async function load() {
  loading.value = true;
  try {
    const m = await apiFetch<Menu>(`/api/v1/cms/menus/${menuId.value}`);
    menu.value = m;
    items.value = assignIds(m.items || []);
    pages.value = await apiFetch<PageOption[]>("/api/v1/cms/pages");
  } catch (e: any) {
    toast.show(e.message || t("cms.menuEditor.loadFailed"), "error");
  } finally {
    loading.value = false;
  }
}

const selected = computed<MenuItem | null>(() => {
  if (!selectedId.value) return null;
  return findById(items.value, selectedId.value);
});

function findById(list: MenuItem[], id: string): MenuItem | null {
  for (const it of list) {
    if (it.id === id) return it;
    if (it.children) {
      const f = findById(it.children, id);
      if (f) return f;
    }
  }
  return null;
}

function removeById(list: MenuItem[], id: string): MenuItem | null {
  for (let i = 0; i < list.length; i++) {
    if (list[i].id === id) return list.splice(i, 1)[0];
    if (list[i].children) {
      const f = removeById(list[i].children!, id);
      if (f) return f;
    }
  }
  return null;
}

function insertAfter(list: MenuItem[], afterId: string, item: MenuItem): boolean {
  for (let i = 0; i < list.length; i++) {
    if (list[i].id === afterId) {
      list.splice(i + 1, 0, item);
      return true;
    }
    if (list[i].children && insertAfter(list[i].children!, afterId, item)) return true;
  }
  return false;
}

function insertAsChild(list: MenuItem[], parentId: string, item: MenuItem): boolean {
  for (let i = 0; i < list.length; i++) {
    if (list[i].id === parentId) {
      list[i].children = list[i].children || [];
      list[i].children!.push(item);
      return true;
    }
    if (list[i].children && insertAsChild(list[i].children!, parentId, item)) return true;
  }
  return false;
}

// Add items from the library panel
function addPage(pageId: number) {
  const p = pages.value.find((x) => x.id === pageId);
  if (!p) return;
  items.value.push({
    id: uid(),
    type: "page",
    page_id: pageId,
    label: p.title,
  });
}
function addLink() {
  items.value.push({
    id: uid(),
    type: "link",
    label: t("cms.menuEditor.defaults.externalLinkLabel"),
    url: "https://example.com",
    target: "_blank",
  });
}
function addSection() {
  items.value.push({
    id: uid(),
    type: "section",
    label: t("cms.menuEditor.defaults.sectionLabel"),
    children: [],
  });
}
function addDivider() {
  items.value.push({
    id: uid(),
    type: "divider",
  });
}

function removeSelected() {
  if (!selectedId.value) return;
  removeById(items.value, selectedId.value);
  selectedId.value = null;
}

// Drag-drop reordering within the right panel
function onDragStart(ev: DragEvent, item: MenuItem) {
  dragItemId.value = item.id;
  if (ev.dataTransfer) ev.dataTransfer.effectAllowed = "move";
}
function onDragOver(ev: DragEvent, item: MenuItem, asChild = false) {
  if (!dragItemId.value || dragItemId.value === item.id) return;
  ev.preventDefault();
  dropTargetId.value = item.id;
  dropAsChild.value = asChild;
}
function onDragLeave() {
  dropTargetId.value = null;
}
function onDrop(ev: DragEvent, target: MenuItem) {
  ev.preventDefault();
  const sourceId = dragItemId.value;
  dragItemId.value = null;
  const asChild = dropAsChild.value;
  dropTargetId.value = null;
  if (!sourceId || sourceId === target.id) return;
  const removed = removeById(items.value, sourceId);
  if (!removed) return;
  if (asChild && target.type === "section") {
    insertAsChild(items.value, target.id, removed);
  } else {
    insertAfter(items.value, target.id, removed);
  }
}

async function save() {
  if (!menu.value) return;
  saving.value = true;
  try {
    await apiFetch(`/api/v1/cms/menus/${menuId.value}`, {
      method: "PUT",
      body: JSON.stringify({ items: stripIds(items.value) }),
    });
    toast.show(t("cms.menuEditor.saved"), "success");
  } catch (e: any) {
    toast.show(e.message || t("cms.menuEditor.saveFailed"), "error");
  } finally {
    saving.value = false;
  }
}

function stripIds(list: MenuItem[]): MenuItem[] {
  return list.map((it) => ({
    ...it,
    // keep ids (harmless server-side, useful for round-trip)
    children: it.children ? stripIds(it.children) : undefined,
  }));
}

watch(selectedId, () => { /* keep binding reactive */ });

onMounted(load);
</script>

<template>
  <div class="editor-wrap">
    <header class="ed-head">
      <button class="back-btn" @click="router.push('/cms/menus')">{{ t("cms.menuEditor.backToMenus") }}</button>
      <div class="ed-title">
        <h1>{{ menu?.name || t("cms.menuEditor.titleFallback") }}</h1>
        <span class="ed-loc">{{ menu?.location }}</span>
      </div>
      <button class="btn-primary" :disabled="saving" @click="save">
        {{ saving ? t("cms.menuEditor.saving") : t("cms.menuEditor.save") }}
      </button>
    </header>

    <div v-if="loading" class="state">{{ t("cms.menuEditor.loading") }}</div>

    <div v-else class="panels">
      <!-- Left: library -->
      <aside class="panel-left">
        <h2 class="panel-title">{{ t("cms.menuEditor.library.title") }}</h2>

        <div class="section">
          <h3>{{ t("cms.menuEditor.library.quickAdd") }}</h3>
          <button class="add-btn" @click="addLink">{{ t("cms.menuEditor.library.addExternalLink") }}</button>
          <button class="add-btn" @click="addSection">{{ t("cms.menuEditor.library.addSection") }}</button>
          <button class="add-btn" @click="addDivider">{{ t("cms.menuEditor.library.addDivider") }}</button>
        </div>

        <div class="section">
          <h3>{{ t("cms.menuEditor.library.existingPages") }}</h3>
          <div class="page-list">
            <button
              v-for="p in pages"
              :key="p.id"
              class="page-item"
              :class="{ unpublished: !p.published }"
              @click="addPage(p.id)"
              :title="p.published ? t('cms.menuEditor.library.pageAddTitlePublished') : t('cms.menuEditor.library.pageAddTitleDraft')"
            >
              <span class="pg-title">{{ p.title }}</span>
              <span class="pg-slug">/{{ p.slug }}</span>
            </button>
          </div>
        </div>
      </aside>

      <!-- Right: current menu -->
      <section class="panel-right">
        <h2 class="panel-title">{{ t("cms.menuEditor.structure.title") }}</h2>
        <div v-if="!items.length" class="empty">
          {{ t("cms.menuEditor.structure.empty") }}
        </div>
        <ul v-else class="menu-tree">
          <li
            v-for="it in items"
            :key="it.id"
            class="m-node"
          >
            <div
              class="m-row"
              :class="{
                selected: selectedId === it.id,
                'drop-above': dropTargetId === it.id && !dropAsChild,
                'drop-as-child': dropTargetId === it.id && dropAsChild,
              }"
              draggable="true"
              @dragstart="onDragStart($event, it)"
              @dragover.prevent="onDragOver($event, it, false)"
              @dragleave="onDragLeave"
              @drop="onDrop($event, it)"
              @click="selectedId = it.id"
            >
              <span class="type-tag" :class="`t-${it.type}`">{{ t(`cms.menuEditor.itemType.${it.type}`) }}</span>
              <span v-if="it.type === 'divider'" class="m-label muted">{{ t("cms.menuEditor.dividerPlaceholder") }}</span>
              <span v-else class="m-label">{{ it.label || t("cms.menuEditor.noLabel") }}</span>
              <span v-if="it.url" class="m-url">{{ it.url }}</span>
            </div>

            <ul v-if="it.type === 'section' && it.children?.length" class="m-children">
              <li v-for="c in it.children" :key="c.id" class="m-node">
                <div
                  class="m-row"
                  :class="{ selected: selectedId === c.id }"
                  draggable="true"
                  @dragstart="onDragStart($event, c)"
                  @dragover.prevent="onDragOver($event, c, false)"
                  @dragleave="onDragLeave"
                  @drop="onDrop($event, c)"
                  @click="selectedId = c.id"
                >
                  <span class="type-tag" :class="`t-${c.type}`">{{ t(`cms.menuEditor.itemType.${c.type}`) }}</span>
                  <span v-if="c.type === 'divider'" class="m-label muted">{{ t("cms.menuEditor.dividerPlaceholder") }}</span>
                  <span v-else class="m-label">{{ c.label || t("cms.menuEditor.noLabel") }}</span>
                </div>
              </li>
            </ul>
          </li>
        </ul>

        <!-- Inspector for selected item -->
        <div v-if="selected" class="inspector">
          <h3>{{ t("cms.menuEditor.inspector.title") }}</h3>
          <label v-if="selected.type !== 'divider'" class="f">
            <span>{{ t("cms.menuEditor.inspector.labelField") }}</span>
            <input v-model="selected.label" type="text" />
          </label>
          <label v-if="selected.type === 'link'" class="f">
            <span>{{ t("cms.menuEditor.inspector.urlField") }}</span>
            <input v-model="selected.url" type="url" placeholder="https://…" />
          </label>
          <label v-if="selected.type === 'link'" class="f">
            <span>{{ t("cms.menuEditor.inspector.targetField") }}</span>
            <select v-model="selected.target">
              <option value="_self">{{ t("cms.menuEditor.inspector.targetSelf") }}</option>
              <option value="_blank">{{ t("cms.menuEditor.inspector.targetBlank") }}</option>
            </select>
          </label>
          <label v-if="selected.type === 'page'" class="f">
            <span>{{ t("cms.menuEditor.inspector.pageField") }}</span>
            <select v-model.number="selected.page_id">
              <option v-for="p in pages" :key="p.id" :value="p.id">{{ p.title }}</option>
            </select>
          </label>
          <button class="btn-danger" @click="removeSelected">{{ t("cms.menuEditor.inspector.removeItem") }}</button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.editor-wrap {
  min-height: 100vh;
  background: #111110;
  color: #E5E5E5;
}
.ed-head {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.02);
}
.back-btn {
  background: transparent;
  color: #A1A1AA;
  border: 1px solid rgba(255,255,255,0.08);
  padding: 8px 14px;
  border-radius: 8px;
  cursor: pointer;
}
.ed-title { display: flex; align-items: baseline; gap: 10px; flex: 1; }
.ed-title h1 { margin: 0; font-size: 20px; color: #F5F5F5; }
.ed-loc {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  color: #2DD4BF;
  background: rgba(45,212,191,0.1);
  padding: 2px 8px;
  border-radius: 999px;
}
.btn-primary {
  background: #F5A623;
  color: #111110;
  border: none;
  padding: 10px 18px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
}
.btn-primary:disabled { opacity: 0.6; cursor: wait; }

.state { padding: 48px; text-align: center; color: #71717A; }

.panels {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 16px;
  padding: 16px 24px 48px;
  max-width: 1400px;
  margin: 0 auto;
}

.panel-left, .panel-right {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 16px;
}
.panel-title {
  margin: 0 0 14px;
  font-size: 14px;
  color: #A1A1AA;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.section { margin-bottom: 20px; }
.section h3 {
  font-size: 11px;
  color: #71717A;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0 0 8px;
}
.add-btn {
  display: block;
  width: 100%;
  text-align: left;
  background: rgba(255,255,255,0.03);
  color: #E5E5E5;
  border: 1px solid rgba(255,255,255,0.08);
  padding: 10px 14px;
  border-radius: 8px;
  margin-bottom: 6px;
  cursor: pointer;
}
.add-btn:hover { background: rgba(245,166,35,0.1); color: #F5A623; }

.page-list {
  max-height: 360px;
  overflow-y: auto;
}
.page-item {
  display: block;
  width: 100%;
  text-align: left;
  background: transparent;
  color: #E5E5E5;
  border: 1px solid rgba(255,255,255,0.06);
  padding: 8px 12px;
  border-radius: 6px;
  margin-bottom: 4px;
  cursor: pointer;
}
.page-item:hover { background: rgba(255,255,255,0.04); }
.page-item.unpublished { opacity: 0.6; }
.pg-title { display: block; font-weight: 600; color: #F5F5F5; font-size: 13px; }
.pg-slug { display: block; font-family: 'IBM Plex Mono', monospace; color: #71717A; font-size: 11px; }

.empty {
  padding: 40px 16px;
  color: #71717A;
  text-align: center;
  border: 1px dashed rgba(255,255,255,0.08);
  border-radius: 8px;
}
.menu-tree {
  list-style: none;
  padding: 0;
  margin: 0;
}
.m-children {
  list-style: none;
  padding-left: 28px;
  margin: 4px 0 0;
}
.m-node { margin-bottom: 4px; }
.m-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.02);
  cursor: grab;
  transition: background 0.15s, border-color 0.15s;
}
.m-row:hover { border-color: rgba(245,166,35,0.3); }
.m-row.selected { border-color: #F5A623; background: rgba(245,166,35,0.08); }
.m-row.drop-above { border-top: 2px solid #F5A623; }
.m-row.drop-as-child { background: rgba(245,166,35,0.15); }
.type-tag {
  font-size: 10px;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 999px;
  font-family: 'IBM Plex Mono', monospace;
  background: rgba(255,255,255,0.08);
  color: #A1A1AA;
}
.t-page { background: rgba(245,166,35,0.15); color: #F5A623; }
.t-link { background: rgba(45,212,191,0.15); color: #2DD4BF; }
.t-section { background: rgba(167,139,250,0.15); color: #A78BFA; }
.t-divider { background: rgba(255,255,255,0.05); color: #71717A; }
.m-label { color: #F5F5F5; font-weight: 500; }
.m-label.muted { color: #71717A; font-style: italic; }
.m-url { margin-left: auto; color: #71717A; font-size: 12px; font-family: 'IBM Plex Mono', monospace; }

.inspector {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid rgba(255,255,255,0.08);
}
.inspector h3 {
  font-size: 12px;
  color: #A1A1AA;
  text-transform: uppercase;
  margin: 0 0 12px;
  letter-spacing: 0.08em;
}
.f { display: block; margin-bottom: 12px; }
.f span {
  display: block;
  font-size: 11px;
  color: #71717A;
  margin-bottom: 4px;
  text-transform: uppercase;
}
.f input, .f select {
  width: 100%;
  background: #111110;
  border: 1px solid rgba(255,255,255,0.1);
  color: #F5F5F5;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
}
.f input:focus, .f select:focus { outline: none; border-color: #F5A623; }
.btn-danger {
  background: transparent;
  color: #ef4444;
  border: 1px solid rgba(239,68,68,0.3);
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  margin-top: 8px;
}
.btn-danger:hover { background: rgba(239,68,68,0.1); }
</style>
