<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";

const router = useRouter();
const toast = useToastStore();

type MenuItem = {
  id?: string;
  type: "page" | "link" | "section" | "divider";
  label?: string;
  url?: string;
  page_id?: number;
  target?: string;
  children?: MenuItem[];
};

type Menu = {
  id: number;
  name: string;
  location: string;
  items: MenuItem[] | null;
  created_at: string;
  updated_at: string;
};

const menus = ref<Menu[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

const createOpen = ref(false);
const newName = ref("");
const newLocation = ref("");
const saving = ref(false);

function countItems(items: MenuItem[] | null): number {
  if (!items) return 0;
  let n = 0;
  for (const it of items) {
    n += 1;
    if (it.children?.length) n += countItems(it.children);
  }
  return n;
}

async function load() {
  loading.value = true;
  error.value = null;
  try {
    menus.value = await apiFetch<Menu[]>("/api/v1/cms/menus");
  } catch (e: any) {
    error.value = e.message || "Failed to load menus";
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  newName.value = "";
  newLocation.value = "";
  createOpen.value = true;
}

async function createMenu() {
  if (!newName.value.trim() || !newLocation.value.trim()) {
    toast.show("Name and location are required", "error");
    return;
  }
  saving.value = true;
  try {
    const menu = await apiFetch<Menu>("/api/v1/cms/menus", {
      method: "POST",
      body: JSON.stringify({
        name: newName.value.trim(),
        location: newLocation.value.trim(),
        items: [],
      }),
    });
    toast.show("Menu created", "success");
    createOpen.value = false;
    router.push(`/cms/menus/${menu.id}/edit`);
  } catch (e: any) {
    toast.show(e.message || "Create failed", "error");
  } finally {
    saving.value = false;
  }
}

async function deleteMenu(id: number, name: string) {
  if (!confirm(`Delete menu "${name}"?`)) return;
  try {
    await apiFetch(`/api/v1/cms/menus/${id}`, { method: "DELETE" });
    toast.show("Menu deleted", "success");
    await load();
  } catch (e: any) {
    toast.show(e.message, "error");
  }
}

onMounted(load);
</script>

<template>
  <div class="page-wrap">
    <header class="page-head">
      <div>
        <h1 class="page-title">CMS Menus</h1>
        <p class="page-sub">Navigation menus composed of pages, external links, sections and dividers.</p>
      </div>
      <button class="btn-primary" @click="openCreate">+ New menu</button>
    </header>

    <div v-if="loading" class="state-msg">Loading…</div>
    <div v-else-if="error" class="state-msg error">{{ error }}</div>
    <div v-else-if="menus.length === 0" class="state-msg">
      No menus yet. Create one to build a navigation bar for your CMS pages.
    </div>
    <div v-else class="menu-grid">
      <div
        v-for="m in menus"
        :key="m.id"
        class="menu-card"
      >
        <div class="card-head">
          <h3 class="card-title" @click="router.push(`/cms/menus/${m.id}/edit`)">{{ m.name }}</h3>
          <span class="badge">{{ m.location }}</span>
        </div>
        <div class="card-meta">{{ countItems(m.items) }} items</div>
        <div class="card-actions">
          <button class="a-btn" @click="router.push(`/cms/menus/${m.id}/edit`)">Edit</button>
          <button class="a-btn danger" @click="deleteMenu(m.id, m.name)">Delete</button>
        </div>
      </div>
    </div>

    <div v-if="createOpen" class="modal-overlay" @click.self="createOpen = false">
      <div class="modal">
        <h2>New menu</h2>
        <label class="field">
          <span>Name</span>
          <input v-model="newName" type="text" placeholder="Main header" />
        </label>
        <label class="field">
          <span>Location</span>
          <select v-model="newLocation">
            <option value="">— choose —</option>
            <option value="header">header</option>
            <option value="footer">footer</option>
            <option value="sidebar">sidebar</option>
          </select>
          <small class="hint">Or type a custom value:</small>
          <input v-model="newLocation" type="text" placeholder="custom-slot" />
        </label>
        <div class="modal-actions">
          <button class="btn-secondary" @click="createOpen = false">Cancel</button>
          <button class="btn-primary" :disabled="saving" @click="createMenu">
            {{ saving ? 'Saving…' : 'Create' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-wrap {
  padding: 24px 32px;
  max-width: 1200px;
  margin: 0 auto;
}
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}
.page-title { font-size: 28px; font-weight: 700; color: #F5F5F5; margin: 0 0 4px; }
.page-sub { color: #A1A1AA; margin: 0; font-size: 14px; }
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
.btn-secondary {
  background: transparent;
  color: #E5E5E5;
  border: 1px solid rgba(255,255,255,0.15);
  padding: 10px 18px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}
.state-msg { padding: 48px 24px; text-align: center; color: #71717A; }
.state-msg.error { color: #ef4444; }
.menu-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}
.menu-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 20px;
  transition: border-color 0.15s;
}
.menu-card:hover { border-color: rgba(245,166,35,0.3); }
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 4px;
}
.card-title {
  color: #F5F5F5;
  font-weight: 600;
  font-size: 18px;
  margin: 0;
  cursor: pointer;
}
.card-title:hover { color: #F5A623; }
.badge {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  color: #2DD4BF;
  background: rgba(45,212,191,0.12);
  padding: 2px 10px;
  border-radius: 999px;
  text-transform: lowercase;
}
.card-meta { color: #A1A1AA; font-size: 13px; margin: 4px 0 14px; }
.card-actions {
  display: flex;
  gap: 6px;
}
.a-btn {
  background: transparent;
  color: #A1A1AA;
  border: 1px solid rgba(255,255,255,0.1);
  padding: 6px 12px;
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
.modal h2 { margin: 0 0 20px; font-size: 20px; color: #F5F5F5; }
.field { display: block; margin-bottom: 16px; }
.field span {
  display: block;
  font-size: 12px;
  color: #A1A1AA;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.field .hint {
  display: block;
  color: #71717A;
  font-size: 11px;
  margin: 6px 0 4px;
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
.field input:focus, .field select:focus { outline: none; border-color: #F5A623; }
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 24px;
}
</style>
