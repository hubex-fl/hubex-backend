<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";

const router = useRouter();
const toast = useToastStore();

type FormSummary = {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  enabled: boolean;
  action: string;
  submission_count: number;
  updated_at: string;
  created_at: string;
};

const forms = ref<FormSummary[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

const createOpen = ref(false);
const newName = ref("");
const newSlug = ref("");
const saving = ref(false);

function slugify(s: string): string {
  return s
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-");
}

async function loadForms() {
  loading.value = true;
  error.value = null;
  try {
    forms.value = await apiFetch<FormSummary[]>("/api/v1/cms/forms");
  } catch (e: any) {
    error.value = e.message || "Failed to load forms";
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  newName.value = "";
  newSlug.value = "";
  createOpen.value = true;
}

function onNameInput() {
  if (!newSlug.value && newName.value) {
    newSlug.value = slugify(newName.value);
  }
}

async function createForm() {
  if (!newName.value.trim() || !newSlug.value.trim()) {
    toast.show("Name and slug are required", "error");
    return;
  }
  saving.value = true;
  try {
    const form = await apiFetch<{ id: number }>("/api/v1/cms/forms", {
      method: "POST",
      body: JSON.stringify({
        name: newName.value.trim(),
        slug: newSlug.value.trim(),
        fields: [
          { id: "name", type: "text", label: "Name", required: true, placeholder: "Your name" },
          { id: "email", type: "email", label: "Email", required: true, placeholder: "you@example.com" },
          { id: "message", type: "textarea", label: "Message", required: true, placeholder: "How can we help?" },
        ],
        submit_button_text: "Submit",
        success_message: "Thank you!",
        action: "store",
        enabled: true,
      }),
    });
    toast.show("Form created", "success");
    createOpen.value = false;
    router.push(`/cms/forms/${form.id}/edit`);
  } catch (e: any) {
    toast.show(e.message || "Failed to create form", "error");
  } finally {
    saving.value = false;
  }
}

async function toggleEnabled(f: FormSummary) {
  try {
    await apiFetch(`/api/v1/cms/forms/${f.id}`, {
      method: "PUT",
      body: JSON.stringify({ enabled: !f.enabled }),
    });
    toast.show(f.enabled ? "Form disabled" : "Form enabled", "success");
    await loadForms();
  } catch (e: any) {
    toast.show(e.message, "error");
  }
}

async function deleteForm(id: number, name: string) {
  if (!confirm(`Delete form '${name}' and all its submissions? This cannot be undone.`)) return;
  try {
    await apiFetch(`/api/v1/cms/forms/${id}`, { method: "DELETE" });
    toast.show("Form deleted", "success");
    await loadForms();
  } catch (e: any) {
    toast.show(e.message, "error");
  }
}

onMounted(loadForms);
</script>

<template>
  <div class="page-wrap">
    <header class="page-head">
      <div>
        <h1 class="page-title">Forms</h1>
        <p class="page-sub">Build contact forms, surveys, and lead capture.</p>
      </div>
      <button class="btn-primary" @click="openCreate">+ Create Form</button>
    </header>

    <div v-if="loading" class="state-msg">Loading…</div>
    <div v-else-if="error" class="state-msg error">{{ error }}</div>
    <div v-else-if="forms.length === 0" class="state-msg">
      <p>No forms yet. Click “Create Form” to build your first one.</p>
    </div>
    <div v-else class="forms-grid">
      <div
        v-for="f in forms"
        :key="f.id"
        class="form-card"
      >
        <div class="card-head">
          <div class="card-head-main">
            <h3 class="card-title" @click="router.push(`/cms/forms/${f.id}/edit`)">{{ f.name }}</h3>
            <div class="card-slug">/{{ f.slug }}</div>
          </div>
          <label class="toggle">
            <input type="checkbox" :checked="f.enabled" @change="toggleEnabled(f)" />
            <span class="toggle-slider"></span>
          </label>
        </div>
        <p v-if="f.description" class="card-desc">{{ f.description }}</p>
        <div class="card-stats">
          <div class="stat">
            <div class="stat-label">Submissions</div>
            <div class="stat-value">{{ f.submission_count }}</div>
          </div>
          <div class="stat">
            <div class="stat-label">Action</div>
            <div class="stat-value stat-text">{{ f.action }}</div>
          </div>
        </div>
        <div class="card-actions">
          <button class="a-btn" @click="router.push(`/cms/forms/${f.id}/edit`)">Edit</button>
          <button class="a-btn" @click="router.push(`/cms/forms/${f.id}/submissions`)">
            View Submissions
          </button>
          <button class="a-btn danger" @click="deleteForm(f.id, f.name)">Delete</button>
        </div>
      </div>
    </div>

    <div v-if="createOpen" class="modal-overlay" @click.self="createOpen = false">
      <div class="modal">
        <h2>Create Form</h2>
        <label class="field">
          <span>Name</span>
          <input v-model="newName" @input="onNameInput" type="text" placeholder="Contact Form" />
        </label>
        <label class="field">
          <span>Slug</span>
          <input v-model="newSlug" type="text" placeholder="contact-form" />
        </label>
        <p class="hint">
          Your form will be available at
          <code>/api/v1/cms/forms/public/{{ newSlug || "your-slug" }}/submit</code>.
        </p>
        <div class="modal-actions">
          <button class="btn-secondary" @click="createOpen = false">Cancel</button>
          <button class="btn-primary" :disabled="saving" @click="createForm">
            {{ saving ? "Creating…" : "Create" }}
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
.state-msg { padding: 48px 24px; text-align: center; color: #71717A; }
.state-msg.error { color: #ef4444; }
.forms-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 20px;
}
.form-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 20px;
  transition: border-color 0.15s, transform 0.15s;
}
.form-card:hover {
  border-color: rgba(245,166,35,0.3);
  transform: translateY(-2px);
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}
.card-head-main { flex: 1; min-width: 0; }
.card-title {
  font-size: 18px;
  font-weight: 600;
  color: #F5F5F5;
  margin: 0 0 4px;
  cursor: pointer;
}
.card-title:hover { color: #F5A623; }
.card-slug {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  color: #71717A;
}
.card-desc {
  color: #A1A1AA;
  font-size: 13px;
  line-height: 1.5;
  margin: 0 0 12px;
}
.card-stats {
  display: flex;
  gap: 20px;
  margin: 16px 0;
  padding: 12px 0;
  border-top: 1px solid rgba(255,255,255,0.06);
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.stat { flex: 1; }
.stat-label {
  font-size: 10px;
  color: #71717A;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 4px;
}
.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: #F5A623;
  font-family: 'IBM Plex Mono', monospace;
}
.stat-value.stat-text {
  font-size: 14px;
  color: #2DD4BF;
  text-transform: uppercase;
  font-family: 'IBM Plex Mono', monospace;
}
.card-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.a-btn {
  background: transparent;
  color: #A1A1AA;
  border: 1px solid rgba(255,255,255,0.08);
  padding: 6px 12px;
  font-size: 12px;
  border-radius: 6px;
  cursor: pointer;
}
.a-btn:hover { background: rgba(255,255,255,0.05); color: #F5F5F5; }
.a-btn.danger:hover { color: #ef4444; border-color: #ef4444; }

/* Toggle switch */
.toggle {
  position: relative;
  display: inline-block;
  width: 36px;
  height: 20px;
  flex-shrink: 0;
}
.toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}
.toggle-slider {
  position: absolute;
  inset: 0;
  background: rgba(255,255,255,0.1);
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.2s;
}
.toggle-slider::before {
  content: "";
  position: absolute;
  width: 14px;
  height: 14px;
  background: #E5E5E5;
  border-radius: 50%;
  top: 3px;
  left: 3px;
  transition: transform 0.2s;
}
.toggle input:checked + .toggle-slider { background: #F5A623; }
.toggle input:checked + .toggle-slider::before { transform: translateX(16px); background: #111110; }

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
.field input {
  width: 100%;
  background: #111110;
  border: 1px solid rgba(255,255,255,0.1);
  color: #F5F5F5;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 14px;
}
.field input:focus { outline: none; border-color: #F5A623; }
.hint {
  font-size: 12px;
  color: #71717A;
  margin: 0 0 16px;
}
.hint code {
  background: rgba(255,255,255,0.06);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  color: #2DD4BF;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 24px;
}
</style>
