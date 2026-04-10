<script setup lang="ts">
import { ref, onMounted } from "vue";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";

type Redirect = {
  id: number;
  from_path: string;
  to_path: string;
  status_code: number;
  enabled: boolean;
  hit_count: number;
  last_hit_at: string | null;
  created_at: string;
};

const toast = useToastStore();
const items = ref<Redirect[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// Form state
const createOpen = ref(false);
const editing = ref<Redirect | null>(null);
const form = ref({
  from_path: "",
  to_path: "",
  status_code: 301 as 301 | 302,
  enabled: true,
});
const saving = ref(false);

async function load() {
  loading.value = true;
  error.value = null;
  try {
    items.value = await apiFetch<Redirect[]>("/api/v1/cms/redirects");
  } catch (e: any) {
    error.value = e.message || "Failed to load";
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editing.value = null;
  form.value = { from_path: "", to_path: "", status_code: 301, enabled: true };
  createOpen.value = true;
}

function openEdit(r: Redirect) {
  editing.value = r;
  form.value = {
    from_path: r.from_path,
    to_path: r.to_path,
    status_code: r.status_code as 301 | 302,
    enabled: r.enabled,
  };
  createOpen.value = true;
}

async function save() {
  if (!form.value.from_path.trim() || !form.value.to_path.trim()) {
    toast.show("Both from and to paths are required", "error");
    return;
  }
  saving.value = true;
  try {
    if (editing.value) {
      await apiFetch(`/api/v1/cms/redirects/${editing.value.id}`, {
        method: "PUT",
        body: JSON.stringify(form.value),
      });
      toast.show("Redirect updated", "success");
    } else {
      await apiFetch("/api/v1/cms/redirects", {
        method: "POST",
        body: JSON.stringify(form.value),
      });
      toast.show("Redirect created", "success");
    }
    createOpen.value = false;
    await load();
  } catch (e: any) {
    toast.show(e.message || "Failed to save", "error");
  } finally {
    saving.value = false;
  }
}

async function remove(r: Redirect) {
  if (!confirm(`Delete redirect ${r.from_path} → ${r.to_path}?`)) return;
  try {
    await apiFetch(`/api/v1/cms/redirects/${r.id}`, { method: "DELETE" });
    toast.show("Deleted", "success");
    await load();
  } catch (e: any) {
    toast.show(e.message || "Failed to delete", "error");
  }
}

async function toggleEnabled(r: Redirect) {
  try {
    await apiFetch(`/api/v1/cms/redirects/${r.id}`, {
      method: "PUT",
      body: JSON.stringify({
        from_path: r.from_path,
        to_path: r.to_path,
        status_code: r.status_code,
        enabled: !r.enabled,
      }),
    });
    await load();
  } catch (e: any) {
    toast.show(e.message || "Failed to toggle", "error");
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

onMounted(load);
</script>

<template>
  <div class="page-wrap">
    <header class="page-head">
      <div>
        <h1 class="page-title">URL Redirects</h1>
        <p class="page-sub">
          Redirect old URLs to new ones. Useful for SEO-safe page migrations.
        </p>
      </div>
      <button class="btn-primary" @click="openCreate">+ New redirect</button>
    </header>

    <div v-if="loading" class="state-msg">Loading…</div>
    <div v-else-if="error" class="state-msg error">{{ error }}</div>
    <div v-else-if="items.length === 0" class="state-msg">
      No redirects yet. Create one to begin.
    </div>
    <div v-else class="table-wrap">
      <table class="redirect-table">
        <thead>
          <tr>
            <th>From</th>
            <th>To</th>
            <th>Code</th>
            <th>Enabled</th>
            <th>Hits</th>
            <th>Last hit</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in items" :key="r.id">
            <td class="mono">{{ r.from_path }}</td>
            <td class="mono">{{ r.to_path }}</td>
            <td>
              <span class="badge" :class="`code-${r.status_code}`">{{ r.status_code }}</span>
            </td>
            <td>
              <button class="toggle" :class="{ on: r.enabled }" @click="toggleEnabled(r)">
                {{ r.enabled ? "On" : "Off" }}
              </button>
            </td>
            <td>{{ r.hit_count }}</td>
            <td class="muted">{{ formatDate(r.last_hit_at) }}</td>
            <td class="actions">
              <button class="a-btn" @click="openEdit(r)">Edit</button>
              <button class="a-btn danger" @click="remove(r)">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create/Edit modal -->
    <div v-if="createOpen" class="modal-overlay" @click.self="createOpen = false">
      <div class="modal">
        <h2>{{ editing ? "Edit redirect" : "New redirect" }}</h2>
        <label class="field">
          <span>From path</span>
          <input v-model="form.from_path" type="text" placeholder="/old-url" />
        </label>
        <label class="field">
          <span>To path</span>
          <input v-model="form.to_path" type="text" placeholder="/new-url" />
        </label>
        <label class="field">
          <span>Status code</span>
          <select v-model.number="form.status_code">
            <option :value="301">301 Moved Permanently</option>
            <option :value="302">302 Found (Temporary)</option>
          </select>
        </label>
        <label class="field checkbox">
          <input type="checkbox" v-model="form.enabled" />
          <span>Enabled</span>
        </label>
        <div class="modal-actions">
          <button class="btn-secondary" @click="createOpen = false">Cancel</button>
          <button class="btn-primary" :disabled="saving" @click="save">
            {{ saving ? "Saving…" : (editing ? "Update" : "Create") }}
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
.state-msg {
  padding: 48px 24px;
  text-align: center;
  color: #71717A;
}
.state-msg.error { color: #ef4444; }
.table-wrap {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  overflow: hidden;
}
.redirect-table {
  width: 100%;
  border-collapse: collapse;
}
.redirect-table th,
.redirect-table td {
  text-align: left;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  font-size: 13px;
  color: #E5E5E5;
}
.redirect-table th {
  font-size: 11px;
  text-transform: uppercase;
  color: #71717A;
  letter-spacing: 0.05em;
  font-weight: 600;
  background: rgba(0,0,0,0.2);
}
.redirect-table tbody tr:last-child td { border-bottom: none; }
.redirect-table .mono {
  font-family: "IBM Plex Mono", monospace;
  font-size: 12px;
  color: #F5F5F5;
  word-break: break-all;
  max-width: 320px;
}
.redirect-table .muted { color: #71717A; font-size: 12px; }
.redirect-table .actions {
  display: flex;
  gap: 4px;
  justify-content: flex-end;
}
.badge {
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  font-weight: 600;
}
.code-301 { background: rgba(45,212,191,0.15); color: #2DD4BF; }
.code-302 { background: rgba(245,166,35,0.15); color: #F5A623; }
.toggle {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  color: #71717A;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  cursor: pointer;
  font-weight: 600;
}
.toggle.on {
  background: rgba(45,212,191,0.15);
  color: #2DD4BF;
  border-color: rgba(45,212,191,0.3);
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
  max-width: 520px;
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
.field > span {
  display: block;
  font-size: 12px;
  color: #A1A1AA;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.field input[type="text"],
.field select {
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
.field.checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
}
.field.checkbox > span {
  text-transform: none;
  letter-spacing: 0;
  margin: 0;
  font-size: 14px;
  color: #E5E5E5;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 24px;
}
</style>
