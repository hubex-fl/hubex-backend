<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from "vue";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";
import UModal from "../components/ui/UModal.vue";
import UInfoTooltip from "../components/ui/UInfoTooltip.vue";
// Sprint 8 R4 Bucket C F13: TipTap-based visual editor for email body.
// Reuses the CMS RichTextEditor component.
import RichTextEditor from "../components/cms/RichTextEditor.vue";

const toast = useToastStore();
const { t, te, tm, rt } = useI18n();

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

/**
 * Sprint 8 R1-F15 — client-side i18n lookup for backend-seeded
 * built-in email template names. Custom user templates fall back
 * to the raw backend string.
 */
function localizedTemplateName(tpl: Template): string {
  if (!tpl.is_builtin) return tpl.name;
  const key = `pages.emailTemplates.seedNames.${tpl.name}`;
  return te(key) ? t(key) : tpl.name;
}

const templates = ref<Template[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const categoryFilter = ref<string>("all");

const filteredTemplates = computed(() => {
  if (categoryFilter.value === "all") return templates.value;
  return templates.value.filter(tp => tp.category === categoryFilter.value);
});

const categories = computed(() => {
  const cats = new Set(templates.value.map(tp => tp.category));
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

// Inline editor preview (live WYSIWYG)
// Sprint 8 R4 Bucket C F13: added "visual" (TipTap WYSIWYG) mode as the new
// default. Authors can still drop down to code/split/preview if they need
// raw HTML, but the first impression is now a proper rich editor.
const editorView = ref<"visual" | "code" | "preview" | "split" | "simple">("visual");
const debouncedHtml = ref("");
let debounceTimer: ReturnType<typeof setTimeout> | null = null;

// Template variable reference
const TEMPLATE_VARIABLES = computed(() => [
  { token: "{{alert.name}}", desc: t('pages.emailTemplates.varDescAlertName') },
  { token: "{{alert.severity}}", desc: t('pages.emailTemplates.varDescAlertSeverity') },
  { token: "{{device.name}}", desc: t('pages.emailTemplates.varDescDeviceName') },
  { token: "{{device.uid}}", desc: t('pages.emailTemplates.varDescDeviceUid') },
  { token: "{{variable.key}}", desc: t('pages.emailTemplates.varDescVariableKey') },
  { token: "{{variable.value}}", desc: t('pages.emailTemplates.varDescVariableValue') },
  { token: "{{timestamp}}", desc: t('pages.emailTemplates.varDescTimestamp') },
  { token: "{{user.name}}", desc: t('pages.emailTemplates.varDescUserName') },
  { token: "{{org.name}}", desc: t('pages.emailTemplates.varDescOrgName') },
]);

// Simple editor fields
const simpleHeader = ref("");
const simpleBody = ref("");
const simpleFooter = ref("");

// Reference for the HTML textarea
const htmlTextareaRef = ref<HTMLTextAreaElement | null>(null);

function insertVariable(token: string) {
  if (editorView.value === "simple") {
    // Insert at end of body in simple mode
    simpleBody.value += token;
    buildHtmlFromSimple();
    return;
  }
  // Insert at cursor position in textarea
  const ta = htmlTextareaRef.value;
  if (ta) {
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const before = editBodyHtml.value.substring(0, start);
    const after = editBodyHtml.value.substring(end);
    editBodyHtml.value = before + token + after;
    nextTick(() => {
      ta.focus();
      ta.selectionStart = ta.selectionEnd = start + token.length;
    });
  } else {
    editBodyHtml.value += token;
  }
}

function buildHtmlFromSimple() {
  const header = simpleHeader.value.trim();
  const body = simpleBody.value.trim();
  const footer = simpleFooter.value.trim();
  editBodyHtml.value = [
    header ? `<h2 style="color:#F5A623;margin:0 0 16px 0">${header}</h2>` : '',
    body ? `<p style="font-size:14px;line-height:1.6;color:#333;margin:0 0 16px 0">${body.replace(/\n/g, '<br/>')}</p>` : '',
    footer ? `<p style="font-size:12px;color:#888;margin-top:24px;padding-top:12px;border-top:1px solid #eee">${footer}</p>` : '',
  ].filter(Boolean).join('\n');
}

function parseHtmlToSimple() {
  // Best-effort extraction from HTML
  const html = editBodyHtml.value;
  const h2Match = html.match(/<h2[^>]*>([\s\S]*?)<\/h2>/i);
  simpleHeader.value = h2Match ? h2Match[1].replace(/<[^>]+>/g, '') : '';
  const pMatches = html.match(/<p[^>]*>([\s\S]*?)<\/p>/gi) || [];
  if (pMatches.length >= 2) {
    simpleBody.value = pMatches[0].replace(/<\/?p[^>]*>/gi, '').replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '');
    simpleFooter.value = pMatches[pMatches.length - 1].replace(/<\/?p[^>]*>/gi, '').replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '');
  } else if (pMatches.length === 1) {
    simpleBody.value = pMatches[0].replace(/<\/?p[^>]*>/gi, '').replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '');
    simpleFooter.value = '';
  } else {
    simpleBody.value = html.replace(/<[^>]+>/g, '');
    simpleFooter.value = '';
  }
}

watch(editBodyHtml, (val) => {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    debouncedHtml.value = val;
  }, 300);
}, { immediate: true });

const CATEGORY_LABELS = computed<Record<string, string>>(() => ({
  alert: t('pages.emailTemplates.categoryAlert'),
  report: t('pages.emailTemplates.categoryReport'),
  system: t('pages.emailTemplates.categorySystem'),
  custom: t('pages.emailTemplates.categoryCustom'),
}));

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
    error.value = t('pages.emailTemplates.loadError');
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
      toast.addToast(t('toast.created', { item: t('nav.emailTemplates') }), "success");
    } else {
      await apiFetch(`/api/v1/email-templates/${editId.value}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: editName.value, subject: editSubject.value,
          body_html: editBodyHtml.value, body_text: editBodyText.value,
          variables: vars.length ? vars : null,
        }),
      });
      toast.addToast(t('pages.emailTemplates.updated'), "success");
    }
    editOpen.value = false;
    await loadTemplates();
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : t('pages.emailTemplates.saveFailed'), "error");
  } finally {
    editSaving.value = false;
  }
}

async function handleDelete(id: number) {
  if (!confirm(t('pages.emailTemplates.deleteConfirm'))) return;
  try {
    await apiFetch(`/api/v1/email-templates/${id}`, { method: "DELETE" });
    toast.addToast(t('pages.emailTemplates.deleted'), "success");
    await loadTemplates();
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : t('pages.emailTemplates.deleteFailed'), "error");
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
    toast.addToast(t('pages.emailTemplates.previewFailed'), "error");
  }
}

onMounted(loadTemplates);
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <div class="flex items-center">
          <h1 class="text-xl font-semibold text-[var(--text-primary)]">{{ t('pages.emailTemplates.title') }}</h1>
          <UInfoTooltip
            :title="t('infoTooltips.emailTemplates.title')"
            :items="tm('infoTooltips.emailTemplates.items').map((i: any) => rt(i))"
            tourId="email-templates-overview"
          />
        </div>
        <p class="text-xs text-[var(--text-muted)] mt-0.5">
          {{ t('pages.emailTemplates.subtitle') }}.
          <router-link to="/automations" class="text-[var(--primary)] hover:underline ml-1">{{ t('pages.emailTemplates.linkAutomations') }}</router-link> ·
          <router-link to="/reports" class="text-[var(--primary)] hover:underline">{{ t('pages.emailTemplates.linkReports') }}</router-link>
        </p>
      </div>
      <button
        class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black hover:bg-[var(--primary-hover)]"
        @click="openCreate"
      >
        {{ t('pages.emailTemplates.newTemplate') }}
      </button>
    </div>

    <div v-if="loading" class="text-xs text-[var(--text-muted)]">{{ t('pages.emailTemplates.loading') }}</div>

    <div v-else-if="error" class="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-400">
      <p>{{ error }}</p>
      <button class="mt-2 px-2.5 py-1 rounded text-xs font-medium border border-red-500/30 hover:bg-red-500/10" @click="loadTemplates">{{ t('pages.emailTemplates.retry') }}</button>
    </div>

    <template v-else-if="!templates.length">
      <div class="text-center py-8">
        <p class="text-sm text-[var(--text-muted)]">{{ t('pages.emailTemplates.emptyTitle') }}</p>
        <button class="mt-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black" @click="openCreate">{{ t('pages.emailTemplates.createFirst') }}</button>
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
        >{{ cat === 'all' ? t('pages.emailTemplates.filterAll') : (CATEGORY_LABELS[cat] || cat) }}</button>
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
              <span class="text-sm font-medium text-[var(--text-primary)]">{{ localizedTemplateName(tpl) }}</span>
              <span v-if="tpl.is_builtin" class="text-[10px] text-[var(--text-muted)]">{{ t('pages.emailTemplates.builtin') }}</span>
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
              :title="t('pages.emailTemplates.previewTooltip')"
              @click="handlePreview(tpl)"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
            </button>
            <button
              class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
              :title="t('pages.emailTemplates.editTooltip')"
              @click="openEdit(tpl)"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z" /></svg>
            </button>
            <button
              v-if="!tpl.is_builtin"
              class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-red-400 hover:bg-red-500/10 transition-colors"
              :title="t('pages.emailTemplates.deleteTooltip')"
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
    <UModal :open="editOpen" :title="editMode === 'create' ? t('pages.emailTemplates.modalCreateTitle') : t('pages.emailTemplates.modalEditTitle')" size="lg" @close="editOpen = false">
      <div class="space-y-3">
        <div>
          <label class="text-[10px] font-medium text-[var(--text-muted)]">{{ t('pages.emailTemplates.fieldName') }}</label>
          <input v-model="editName" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)]" :placeholder="t('pages.emailTemplates.fieldNamePlaceholder')" />
        </div>
        <div>
          <label class="text-[10px] font-medium text-[var(--text-muted)]">{{ t('pages.emailTemplates.fieldSubject') }}</label>
          <input v-model="editSubject" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)] font-mono" :placeholder="t('pages.emailTemplates.fieldSubjectPlaceholder')" />
        </div>
        <div>
          <div class="flex items-center justify-between mb-1">
            <label class="text-[10px] font-medium text-[var(--text-muted)]">{{ t('pages.emailTemplates.fieldHtmlBody') }}</label>
            <div class="flex rounded-lg border border-[var(--border)] overflow-hidden">
              <button
                v-for="view in (['visual', 'simple', 'code', 'split', 'preview'] as const)"
                :key="view"
                :class="[
                  'px-2 py-0.5 text-[10px] font-medium transition-colors',
                  editorView === view
                    ? 'bg-[var(--primary)]/15 text-[var(--primary)]'
                    : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]',
                ]"
                @click="editorView = view; if (view === 'simple') parseHtmlToSimple();"
              >{{ t(`pages.emailTemplates.editorView.${view}`) }}</button>
            </div>
          </div>

          <!-- Simple Editor Mode -->
          <div v-if="editorView === 'simple'" class="space-y-3">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div class="md:col-span-2 space-y-3">
                <div>
                  <label class="text-[10px] font-medium text-[var(--text-muted)]">{{ t('pages.emailTemplates.simpleHeader') }}</label>
                  <input v-model="simpleHeader" @input="buildHtmlFromSimple" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)]" :placeholder="t('pages.emailTemplates.simpleHeaderPlaceholder')" />
                </div>
                <div>
                  <label class="text-[10px] font-medium text-[var(--text-muted)]">{{ t('pages.emailTemplates.simpleBody') }}</label>
                  <textarea v-model="simpleBody" @input="buildHtmlFromSimple" rows="4" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)]" :placeholder="t('pages.emailTemplates.simpleBodyPlaceholder')" />
                </div>
                <div>
                  <label class="text-[10px] font-medium text-[var(--text-muted)]">{{ t('pages.emailTemplates.simpleFooter') }}</label>
                  <input v-model="simpleFooter" @input="buildHtmlFromSimple" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)]" :placeholder="t('pages.emailTemplates.simpleFooterPlaceholder')" />
                </div>
              </div>
              <!-- Variable panel in simple mode -->
              <div class="border border-[var(--border)] rounded-lg bg-[var(--bg-raised)] p-2">
                <p class="text-[10px] font-semibold text-[var(--text-muted)] mb-2">{{ t('pages.emailTemplates.insertVariable') }}</p>
                <div class="space-y-1">
                  <button
                    v-for="v in TEMPLATE_VARIABLES"
                    :key="v.token"
                    class="w-full text-left px-2 py-1 rounded text-[10px] font-mono text-[var(--text-primary)] hover:bg-[var(--primary)]/10 hover:text-[var(--primary)] transition-colors"
                    :title="v.desc"
                    @click="insertVariable(v.token)"
                  >{{ v.token }}</button>
                </div>
              </div>
            </div>
            <!-- Live preview below -->
            <div class="rounded-lg border border-[var(--border)] bg-white overflow-hidden">
              <div class="px-2 py-1 bg-[var(--bg-raised)] border-b border-[var(--border)] text-[10px] text-[var(--text-muted)]">
                {{ t('pages.emailTemplates.preview') }}
              </div>
              <iframe
                :srcdoc="debouncedHtml || `<p style='color:#999;font-family:sans-serif;font-size:13px;padding:12px;'>${t('pages.emailTemplates.previewEmpty')}</p>`"
                sandbox=""
                class="w-full border-0"
                style="min-height: 120px"
                :title="t('pages.emailTemplates.preview')"
              />
            </div>
          </div>

          <!-- Sprint 8 R4 F13: Visual WYSIWYG mode (TipTap). Drops users straight
               into a formatted editor with bold/italic/headings/lists/links/etc.
               Variables panel on the right still lets them insert {{token}}
               placeholders at the caret. -->
          <div v-else-if="editorView === 'visual'" class="grid grid-cols-1 md:grid-cols-[1fr_220px] gap-3">
            <div class="rounded-lg border border-[var(--border)] bg-[var(--bg-base)] overflow-hidden">
              <RichTextEditor v-model="editBodyHtml" min-height="260px" />
            </div>
            <div class="border border-[var(--border)] rounded-lg bg-[var(--bg-raised)] p-2 h-fit">
              <p class="text-[10px] font-semibold text-[var(--text-muted)] mb-2">{{ t('pages.emailTemplates.insertVariable') }}</p>
              <div class="space-y-1">
                <button
                  v-for="v in TEMPLATE_VARIABLES"
                  :key="v.token"
                  class="w-full text-left px-2 py-1 rounded text-[10px] font-mono text-[var(--text-primary)] hover:bg-[var(--primary)]/10 hover:text-[var(--primary)] transition-colors"
                  :title="v.desc"
                  @click="insertVariable(v.token)"
                >{{ v.token }}</button>
              </div>
              <p class="text-[10px] text-[var(--text-muted)] mt-3 leading-snug">
                {{ t('pages.emailTemplates.visualHint') }}
              </p>
            </div>
          </div>

          <!-- Code / Split / Preview modes -->
          <div v-else class="flex gap-3">
            <div class="flex-1" :class="editorView === 'split' ? 'grid grid-cols-1 md:grid-cols-2 gap-3' : ''">
              <textarea
                v-if="editorView !== 'preview'"
                ref="htmlTextareaRef"
                v-model="editBodyHtml"
                rows="8"
                class="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)] font-mono resize-y"
                :placeholder="t('pages.emailTemplates.fieldHtmlPlaceholder')"
              />
              <div
                v-if="editorView !== 'code'"
                class="rounded-lg border border-[var(--border)] bg-white overflow-hidden"
              >
                <div class="px-2 py-1 bg-[var(--bg-raised)] border-b border-[var(--border)] text-[10px] text-[var(--text-muted)]">
                  {{ t('pages.emailTemplates.preview') }}
                </div>
                <iframe
                  :srcdoc="debouncedHtml || `<p style='color:#999;font-family:sans-serif;font-size:13px;padding:12px;'>${t('pages.emailTemplates.previewEmpty')}</p>`"
                  sandbox=""
                  class="w-full border-0"
                  :style="{ minHeight: editorView === 'preview' ? '200px' : '180px' }"
                  :title="t('pages.emailTemplates.preview')"
                />
              </div>
            </div>
            <!-- Variable reference panel -->
            <div v-if="editorView !== 'preview'" class="w-40 shrink-0 border border-[var(--border)] rounded-lg bg-[var(--bg-raised)] p-2 hidden md:block">
              <p class="text-[10px] font-semibold text-[var(--text-muted)] mb-2">{{ t('pages.emailTemplates.variables') }}</p>
              <div class="space-y-1">
                <button
                  v-for="v in TEMPLATE_VARIABLES"
                  :key="v.token"
                  class="w-full text-left px-1.5 py-1 rounded text-[9px] font-mono text-[var(--text-primary)] hover:bg-[var(--primary)]/10 hover:text-[var(--primary)] transition-colors"
                  :title="v.desc"
                  @click="insertVariable(v.token)"
                >{{ v.token }}</button>
              </div>
            </div>
          </div>
        </div>
        <div>
          <label class="text-[10px] font-medium text-[var(--text-muted)]">{{ t('pages.emailTemplates.fieldTextBody') }}</label>
          <textarea v-model="editBodyText" rows="3" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)] font-mono" :placeholder="t('pages.emailTemplates.fieldTextBodyPlaceholder')" />
        </div>
        <div>
          <label class="text-[10px] font-medium text-[var(--text-muted)]">{{ t('pages.emailTemplates.fieldVariables') }}</label>
          <input v-model="editVariables" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)] font-mono" :placeholder="t('pages.emailTemplates.fieldVariablesPlaceholder')" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <button class="px-3 py-2 rounded-lg text-xs font-medium text-[var(--text-muted)]" @click="editOpen = false">{{ t('pages.emailTemplates.cancel') }}</button>
          <button
            :disabled="editSaving || !editName.trim() || !editSubject.trim()"
            class="px-3 py-2 rounded-lg text-xs font-medium bg-[var(--primary)] text-black disabled:opacity-50"
            @click="handleSave"
          >{{ editSaving ? t('pages.emailTemplates.saving') : editMode === 'create' ? t('pages.emailTemplates.create') : t('pages.emailTemplates.save') }}</button>
        </div>
      </template>
    </UModal>

    <!-- Preview Modal -->
    <UModal :open="previewOpen" :title="t('pages.emailTemplates.previewModalTitle')" size="lg" @close="previewOpen = false">
      <div class="space-y-3">
        <div class="text-xs">
          <span class="text-[var(--text-muted)]">{{ t('pages.emailTemplates.previewSubject') }}</span>
          <span class="font-medium text-[var(--text-primary)]">{{ previewSubject }}</span>
        </div>
        <div class="border border-[var(--border)] rounded-lg bg-white overflow-hidden">
          <iframe
            :srcdoc="previewHtml"
            sandbox=""
            class="w-full min-h-[200px] border-0"
            :title="t('pages.emailTemplates.previewIframeTitle')"
          />
        </div>
      </div>
    </UModal>
  </div>
</template>
