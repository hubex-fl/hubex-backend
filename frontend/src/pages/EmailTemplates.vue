<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";
import UModal from "../components/ui/UModal.vue";

const toast = useToastStore();

type Template = {
  id: number;
  name: string;
  category: string;
  subject: string;
  body_html: string;
  body_text: string;
  variables: string[] | null;
  is_builtin: boolean;
  created_at: string;
  updated_at: string;
};

const templates = ref<Template[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const categoryFilter = ref<string>("all");

const filteredTemplates = computed(() => {
  if (categoryFilter.value === "all") return templates.value;
  return templates.value.filter(t => t.category === categoryFilter.value);
});

const categories = computed(() => {
  const cats = new Set(templates.value.map(t => t.category));
  return ["all", ...Array.from(cats)];
});

// Edit modal
const editOpen = ref(false);
const editMode = ref<"create" | "edit">("create");
const editId = ref<number | null>(null);
const editName = ref("");
const editSubject = ref("");
const editBodyHtml = ref("");
const editBodyText = ref("");
const editVariables = ref("");
const editSaving = ref(false);

// Preview
const previewOpen = ref(false);
const previewSubject = ref("");
const previewHtml = ref("");

const CATEGORY_LABELS: Record<string, string> = {
  alert: "Alert",
  report: "Report",
  system: "System",
  custom: "Custom",
};

const CATEGORY_COLORS: Record<string, string> = {
  alert: "var(--status-bad)",
  report: "var(--primary)",
  system: "var(--accent)",
  custom: "var(--text-muted)",
};

async function loadTemplates() {
  loading.value = true;
  error.value = null;
  try {
    templates.value = await apiFetch<Template[]>("/api/v1/email-templates");
  } catch {
    error.value = "Failed to load templates";
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editMode.value = "create";
  editId.value = null;
  editName.value = "";
  editSubject.value = "";
  editBodyHtml.value = "";
  editBodyText.value = "";
  editVariables.value = "";
  editOpen.value = true;
}

function openEdit(tpl: Template) {
  editMode.value = "edit";
  editId.value = tpl.id;
  editName.value = tpl.name;
  editSubject.value = tpl.subject;
  editBodyHtml.value = tpl.body_html;
  editBodyText.value = tpl.body_text;
  editVariables.value = (tpl.variables || []).join(", ");
  editOpen.value = true;
}

async function handleSave() {
  editSaving.value = true;
  try {
    const vars = editVariables.value.split(",").map(s => s.trim()).filter(Boolean);
    if (editMode.value === "create") {
      await apiFetch("/api/v1/email-templates", {
        method: "POST",
        body: JSON.stringify({
          name: editName.value, subject: editSubject.value,
          body_html: editBodyHtml.value, body_text: editBodyText.value,
          variables: vars.length ? vars : null,
        }),
      });
      toast.addToast("Template created", "success");
    } else {
      await apiFetch(`/api/v1/email-templates/${editId.value}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: editName.value, subject: editSubject.value,
          body_html: editBodyHtml.value, body_text: editBodyText.value,
          variables: vars.length ? vars : null,
        }),
      });
      toast.addToast("Template updated", "success");
    }
    editOpen.value = false;
    await loadTemplates();
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : "Save failed", "error");
  } finally {
    editSaving.value = false;
  }
}

async function handleDelete(id: number) {
  if (!confirm("Delete this template?")) return;
  try {
    await apiFetch(`/api/v1/email-templates/${id}`, { method: "DELETE" });
    toast.addToast("Template deleted", "success");
    await loadTemplates();
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : "Delete failed", "error");
  }
}

async function handlePreview(tpl: Template) {
  try {
    const res = await apiFetch<{ subject: string; body_html: string }>("/api/v1/email-templates/preview", {
      method: "POST",
      body: JSON.stringify({ template_id: tpl.id, test_data: {} }),
    });
    previewSubject.value = res.subject;
    previewHtml.value = res.body_html;
    previewOpen.value = true;
  } catch {
    toast.addToast("Preview failed", "error");
  }
}

onMounted(loadTemplates);
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-xl font-semibold text-[var(--text-primary)]">Email Templates</h1>
        <p class="text-xs text-[var(--text-muted)] mt-0.5">
          Templates for automation emails, alerts, and reports. Use {variable_name} placeholders.
          <router-link to="/automations" class="text-[var(--primary)] hover:underline ml-1">Automations</router-link> ·
          <router-link to="/reports" class="text-[var(--primary)] hover:underline">Reports</router-link>
        </p>
      </div>
      <button
        class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black hover:bg-[var(--primary-hover)]"
        @click="openCreate"
      >
        + New Template
      </button>
    </div>

    <div v-if="loading" class="text-xs text-[var(--text-muted)]">Loading...</div>

    <div v-else-if="error" class="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-400">
      <p>{{ error }}</p>
      <button class="mt-2 px-2.5 py-1 rounded text-xs font-medium border border-red-500/30 hover:bg-red-500/10" @click="loadTemplates">Retry</button>
    </div>

    <template v-else-if="!templates.length">
      <div class="text-center py-8">
        <p class="text-sm text-[var(--text-muted)]">No templates yet</p>
        <button class="mt-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black" @click="openCreate">Create your first template</button>
      </div>
    </template>

    <template v-else>
      <!-- Category filter -->
      <div class="flex gap-1.5">
        <button
          v-for="cat in categories"
          :key="cat"
          :class="[
            'px-2.5 py-1 rounded-lg text-[10px] font-medium transition-colors',
            categoryFilter === cat
              ? 'bg-[var(--primary)]/15 text-[var(--primary)] border border-[var(--primary)]/30'
              : 'text-[var(--text-muted)] border border-[var(--border)] hover:border-[var(--primary)]/40',
          ]"
          @click="categoryFilter = cat"
        >{{ cat === 'all' ? 'All' : (CATEGORY_LABELS[cat] || cat) }}</button>
      </div>

    <div class="space-y-3">
      <div
        v-for="tpl in filteredTemplates"
        :key="tpl.id"
        class="border border-[var(--border)] rounded-xl bg-[var(--bg-surface)] px-5 py-4"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <span
                class="text-[10px] px-1.5 py-0.5 rounded font-medium"
                :style="{ background: CATEGORY_COLORS[tpl.category] + '20', color: CATEGORY_COLORS[tpl.category] }"
              >{{ CATEGORY_LABELS[tpl.category] || tpl.category }}</span>
              <span class="text-sm font-medium text-[var(--text-primary)]">{{ tpl.name }}</span>
              <span v-if="tpl.is_builtin" class="text-[10px] text-[var(--text-muted)]">built-in</span>
            </div>
            <p class="text-xs text-[var(--text-secondary)] font-mono truncate">{{ tpl.subject }}</p>
            <div v-if="tpl.variables?.length" class="flex flex-wrap gap-1 mt-2">
              <span
                v-for="v in tpl.variables"
                :key="v"
                class="text-[10px] px-1.5 py-0.5 rounded border border-[var(--border)] bg-[var(--bg-raised)] font-mono text-[var(--text-muted)]"
              >{<span>{{ v }}</span>}</span>
            </div>
          </div>
          <div class="flex items-center gap-1.5 shrink-0">
            <button
              class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--primary)] hover:bg-[var(--primary)]/10 transition-colors"
              title="Preview"
              @click="handlePreview(tpl)"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
            </button>
            <button
              class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
              title="Edit"
              @click="openEdit(tpl)"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z" /></svg>
            </button>
            <button
              v-if="!tpl.is_builtin"
              class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-red-400 hover:bg-red-500/10 transition-colors"
              title="Delete"
              @click="handleDelete(tpl.id)"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" /></svg>
            </button>
          </div>
        </div>
      </div>
    </div>
    </template>

    <!-- Edit/Create Modal -->
    <UModal :open="editOpen" :title="editMode === 'create' ? 'New Template' : 'Edit Template'" size="lg" @close="editOpen = false">
      <div class="space-y-3">
        <div>
          <label class="text-[10px] font-medium text-[var(--text-muted)]">Name *</label>
          <input v-model="editName" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)]" placeholder="Alert Notification" />
        </div>
        <div>
          <label class="text-[10px] font-medium text-[var(--text-muted)]">Subject *</label>
          <input v-model="editSubject" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)] font-mono" placeholder="[HUBEX] Alert: {alert_name}" />
        </div>
        <div>
          <label class="text-[10px] font-medium text-[var(--text-muted)]">HTML Body</label>
          <textarea v-model="editBodyHtml" rows="6" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)] font-mono" placeholder="<h2>Alert</h2><p>{variable_key} = {value}</p>" />
        </div>
        <div>
          <label class="text-[10px] font-medium text-[var(--text-muted)]">Text Body (fallback)</label>
          <textarea v-model="editBodyText" rows="3" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)] font-mono" placeholder="Alert: {alert_name}" />
        </div>
        <div>
          <label class="text-[10px] font-medium text-[var(--text-muted)]">Variables (comma-separated)</label>
          <input v-model="editVariables" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)] font-mono" placeholder="alert_name, device_name, value" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <button class="px-3 py-2 rounded-lg text-xs font-medium text-[var(--text-muted)]" @click="editOpen = false">Cancel</button>
          <button
            :disabled="editSaving || !editName.trim() || !editSubject.trim()"
            class="px-3 py-2 rounded-lg text-xs font-medium bg-[var(--primary)] text-black disabled:opacity-50"
            @click="handleSave"
          >{{ editSaving ? 'Saving...' : editMode === 'create' ? 'Create' : 'Save' }}</button>
        </div>
      </template>
    </UModal>

    <!-- Preview Modal -->
    <UModal :open="previewOpen" title="Email Preview" size="lg" @close="previewOpen = false">
      <div class="space-y-3">
        <div class="text-xs">
          <span class="text-[var(--text-muted)]">Subject: </span>
          <span class="font-medium text-[var(--text-primary)]">{{ previewSubject }}</span>
        </div>
        <div class="border border-[var(--border)] rounded-lg bg-white overflow-hidden">
          <iframe
            :srcdoc="previewHtml"
            sandbox=""
            class="w-full min-h-[200px] border-0"
            title="Email preview"
          />
        </div>
      </div>
    </UModal>
  </div>
</template>
