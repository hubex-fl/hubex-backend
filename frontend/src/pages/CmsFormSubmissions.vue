<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const toast = useToastStore();

type FieldDef = { id: string; label: string; type: string };
type Form = {
  id: number;
  name: string;
  slug: string;
  fields: FieldDef[];
};
type Submission = {
  id: number;
  form_id: number;
  data: Record<string, any>;
  submitted_at: string;
  ip_address: string | null;
  user_agent: string | null;
  read: boolean;
};

const formId = computed(() => Number(route.params.id));
const form = ref<Form | null>(null);
const submissions = ref<Submission[]>([]);
const loading = ref(true);
const selected = ref<Submission | null>(null);

async function loadAll() {
  loading.value = true;
  try {
    form.value = await apiFetch<Form>(`/api/v1/cms/forms/${formId.value}`);
    submissions.value = await apiFetch<Submission[]>(
      `/api/v1/cms/forms/${formId.value}/submissions`,
    );
  } catch (e: any) {
    toast.show(e.message || t("cms.formSubmissions.loadFailed"), "error");
  } finally {
    loading.value = false;
  }
}

function fieldLabel(id: string): string {
  if (!form.value) return id;
  const f = form.value.fields.find((ff) => ff.id === id);
  return f?.label || id;
}

async function viewSubmission(sub: Submission) {
  try {
    const full = await apiFetch<Submission>(
      `/api/v1/cms/forms/${formId.value}/submissions/${sub.id}`,
    );
    selected.value = full;
    sub.read = true;
  } catch (e: any) {
    toast.show(e.message, "error");
  }
}

async function deleteSubmission(sub: Submission) {
  if (!confirm(t("cms.formSubmissions.confirmDelete"))) return;
  try {
    await apiFetch(
      `/api/v1/cms/forms/${formId.value}/submissions/${sub.id}`,
      { method: "DELETE" },
    );
    toast.show(t("cms.formSubmissions.deleted"), "success");
    if (selected.value?.id === sub.id) selected.value = null;
    await loadAll();
  } catch (e: any) {
    toast.show(e.message, "error");
  }
}

function exportCsv() {
  if (!form.value || submissions.value.length === 0) {
    toast.show(t("cms.formSubmissions.noneToExport"), "error");
    return;
  }
  // Collect all unique field IDs
  const fieldIds = new Set<string>();
  for (const s of submissions.value) {
    for (const k of Object.keys(s.data)) fieldIds.add(k);
  }
  const cols = ["id", "submitted_at", "ip_address", ...fieldIds];
  const escape = (val: any): string => {
    if (val === null || val === undefined) return "";
    const s = typeof val === "string" ? val : JSON.stringify(val);
    return `"${s.replace(/"/g, '""')}"`;
  };
  const rows = [cols.map(escape).join(",")];
  for (const s of submissions.value) {
    const row = [
      escape(s.id),
      escape(s.submitted_at),
      escape(s.ip_address || ""),
      ...Array.from(fieldIds).map((k) => escape(s.data[k])),
    ];
    rows.push(row.join(","));
  }
  const csv = rows.join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${form.value.slug}-submissions.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

function formatDate(s: string): string {
  try {
    return new Date(s).toLocaleString();
  } catch {
    return s;
  }
}

function previewData(data: Record<string, any>): string {
  const entries = Object.entries(data).slice(0, 3);
  return entries
    .map(([k, v]) => {
      const val = typeof v === "string" ? v : JSON.stringify(v);
      return `${fieldLabel(k)}: ${val.slice(0, 40)}`;
    })
    .join(" • ");
}

onMounted(loadAll);
</script>

<template>
  <div class="page-wrap">
    <header class="page-head">
      <button class="back-btn" @click="router.push('/cms/forms')">{{ t("cms.formSubmissions.backToForms") }}</button>
      <div class="head-title">
        <h1>{{ form?.name || t("cms.formSubmissions.titleFallback") }}</h1>
        <div class="head-sub">{{ t("cms.formSubmissions.countLabel", { n: submissions.length }) }}</div>
      </div>
      <div class="head-actions">
        <button class="btn-secondary" @click="exportCsv">{{ t("cms.formSubmissions.exportCsv") }}</button>
        <button class="btn-secondary" @click="router.push(`/cms/forms/${formId}/edit`)">
          {{ t("cms.formSubmissions.editForm") }}
        </button>
      </div>
    </header>

    <div v-if="loading" class="state-msg">{{ t("cms.formSubmissions.loading") }}</div>
    <div v-else-if="submissions.length === 0" class="state-msg">
      {{ t("cms.formSubmissions.empty") }}
    </div>
    <div v-else class="submissions-layout">
      <div class="table-wrap">
        <table class="sub-table">
          <thead>
            <tr>
              <th>{{ t("cms.formSubmissions.columns.status") }}</th>
              <th>{{ t("cms.formSubmissions.columns.date") }}</th>
              <th>{{ t("cms.formSubmissions.columns.preview") }}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="s in submissions"
              :key="s.id"
              class="sub-row"
              :class="{ unread: !s.read, selected: selected?.id === s.id }"
              @click="viewSubmission(s)"
            >
              <td>
                <span v-if="!s.read" class="dot unread-dot" :title="t('cms.formSubmissions.unread')"></span>
                <span v-else class="dot read-dot" :title="t('cms.formSubmissions.read')"></span>
              </td>
              <td>{{ formatDate(s.submitted_at) }}</td>
              <td class="preview-cell">{{ previewData(s.data) }}</td>
              <td>
                <button class="mini-btn danger" :title="t('cms.formSubmissions.deleteTitle')" @click.stop="deleteSubmission(s)">×</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <aside v-if="selected" class="detail-panel">
        <div class="detail-head">
          <h3>{{ t("cms.formSubmissions.detailHeading", { id: selected.id }) }}</h3>
          <button class="close-btn" :title="t('cms.formSubmissions.close')" @click="selected = null">×</button>
        </div>
        <div class="detail-meta">
          <div><span>{{ t("cms.formSubmissions.detailMeta.date") }}</span> {{ formatDate(selected.submitted_at) }}</div>
          <div v-if="selected.ip_address"><span>{{ t("cms.formSubmissions.detailMeta.ip") }}</span> {{ selected.ip_address }}</div>
          <div v-if="selected.user_agent">
            <span>{{ t("cms.formSubmissions.detailMeta.agent") }}</span> <code>{{ selected.user_agent }}</code>
          </div>
        </div>
        <h4>{{ t("cms.formSubmissions.fieldsHeading") }}</h4>
        <dl class="field-list">
          <template v-for="(val, k) in selected.data" :key="k">
            <dt>{{ fieldLabel(String(k)) }}</dt>
            <dd>{{ val }}</dd>
          </template>
        </dl>
      </aside>
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
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}
.back-btn {
  background: transparent;
  color: #A1A1AA;
  border: 1px solid rgba(255,255,255,0.1);
  padding: 8px 14px;
  border-radius: 6px;
  cursor: pointer;
}
.back-btn:hover { color: #F5F5F5; }
.head-title { flex: 1; }
.head-title h1 { font-size: 24px; color: #F5F5F5; margin: 0; }
.head-sub { color: #A1A1AA; font-size: 13px; }
.head-actions { display: flex; gap: 8px; }
.btn-secondary {
  background: transparent;
  color: #E5E5E5;
  border: 1px solid rgba(255,255,255,0.15);
  padding: 8px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
.btn-secondary:hover { border-color: #F5A623; color: #F5A623; }
.state-msg { padding: 48px 24px; text-align: center; color: #71717A; }

.submissions-layout {
  display: grid;
  grid-template-columns: 1fr 420px;
  gap: 20px;
}
.table-wrap {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  overflow: hidden;
}
.sub-table {
  width: 100%;
  border-collapse: collapse;
}
.sub-table th {
  background: rgba(0,0,0,0.3);
  color: #71717A;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
}
.sub-row {
  border-top: 1px solid rgba(255,255,255,0.06);
  cursor: pointer;
}
.sub-row:hover { background: rgba(255,255,255,0.03); }
.sub-row.selected { background: rgba(245,166,35,0.08); }
.sub-row td {
  padding: 14px 16px;
  color: #E5E5E5;
  font-size: 13px;
}
.sub-row.unread td { color: #F5F5F5; font-weight: 500; }
.preview-cell {
  color: #A1A1AA;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 400px;
}
.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.unread-dot { background: #F5A623; }
.read-dot { background: rgba(255,255,255,0.15); }

.mini-btn {
  background: transparent;
  color: #71717A;
  border: 1px solid rgba(255,255,255,0.08);
  width: 26px;
  height: 26px;
  border-radius: 4px;
  cursor: pointer;
}
.mini-btn.danger:hover { color: #ef4444; border-color: #ef4444; }

.detail-panel {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 20px;
  height: fit-content;
  position: sticky;
  top: 24px;
}
.detail-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.detail-head h3 { margin: 0; color: #F5F5F5; font-size: 16px; }
.close-btn {
  background: transparent;
  color: #71717A;
  border: none;
  font-size: 22px;
  cursor: pointer;
  line-height: 1;
}
.close-btn:hover { color: #ef4444; }
.detail-meta {
  font-size: 12px;
  color: #A1A1AA;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.detail-meta > div { margin-bottom: 4px; }
.detail-meta span {
  color: #71717A;
  display: inline-block;
  width: 60px;
  text-transform: uppercase;
  font-size: 10px;
  letter-spacing: 0.05em;
}
.detail-meta code {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
  word-break: break-all;
}
.detail-panel h4 {
  font-size: 11px;
  color: #71717A;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin: 0 0 12px;
}
.field-list dt {
  font-size: 11px;
  color: #71717A;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: 10px;
}
.field-list dd {
  margin: 4px 0 0;
  color: #F5F5F5;
  font-size: 14px;
  word-break: break-word;
}
</style>
