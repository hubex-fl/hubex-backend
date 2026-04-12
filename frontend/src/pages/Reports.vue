<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";
import UModal from "../components/ui/UModal.vue";
import UBadge from "../components/ui/UBadge.vue";
import UEmpty from "../components/ui/UEmpty.vue";
import UCard from "../components/ui/UCard.vue";
import UInfoTooltip from "../components/ui/UInfoTooltip.vue";

const toast = useToastStore();
const { t, tm, rt } = useI18n();

type Template = {
  id: number; name: string; description: string | null;
  layout: Record<string, unknown>; data_sources: Record<string, unknown>;
  schedule_cron: string | null; email_recipients: string[] | null;
  enabled: boolean; created_at: string;
};
type Report = {
  id: number; template_id: number; title: string;
  format: string; generated_at: string;
};

const templates = ref<Template[]>([]);
const reports = ref<Report[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const generating = ref<number | null>(null);
const filterType = ref<"all" | "scheduled" | "manual">("all");

const filteredTemplates = computed(() => {
  if (filterType.value === "all") return templates.value;
  if (filterType.value === "scheduled") return templates.value.filter(tp => tp.schedule_cron);
  return templates.value.filter(tp => !tp.schedule_cron);
});

// Create modal
const createOpen = ref(false);
const formName = ref("");
const formDesc = ref("");
const formCron = ref("");
const formEmails = ref("");
const saving = ref(false);

async function loadAll() {
  loading.value = true;
  error.value = null;
  try {
    const [tplRes, histRes] = await Promise.allSettled([
      apiFetch<Template[]>("/api/v1/reports/templates"),
      apiFetch<Report[]>("/api/v1/reports/history?limit=10"),
    ]);
    templates.value = tplRes.status === "fulfilled" ? tplRes.value : [];
    reports.value = histRes.status === "fulfilled" ? histRes.value : [];
    if (tplRes.status === "rejected" && histRes.status === "rejected") {
      error.value = t('pages.reports.loadError');
    }
  } finally {
    loading.value = false;
  }
}

async function handleCreate() {
  saving.value = true;
  try {
    const emails = formEmails.value.split(",").map(s => s.trim()).filter(Boolean);
    await apiFetch("/api/v1/reports/templates", {
      method: "POST",
      body: JSON.stringify({
        name: formName.value.trim(),
        description: formDesc.value || null,
        schedule_cron: formCron.value || null,
        email_recipients: emails.length ? emails : null,
      }),
    });
    toast.addToast(t('toast.created', { item: t('pages.reports.title') }), "success");
    createOpen.value = false;
    formName.value = ""; formDesc.value = ""; formCron.value = ""; formEmails.value = "";
    await loadAll();
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : t('pages.reports.createFailed'), "error");
  } finally {
    saving.value = false;
  }
}

async function handleGenerate(templateId: number) {
  generating.value = templateId;
  try {
    const result = await apiFetch<Report>(`/api/v1/reports/generate/${templateId}`, { method: "POST" });
    toast.addToast(t('pages.reports.reportGenerated', { title: result.title }), "success");
    await loadAll();
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : t('pages.reports.generationFailed'), "error");
  } finally {
    generating.value = null;
  }
}

async function handleDelete(id: number) {
  if (!confirm(t('pages.reports.deleteConfirm'))) return;
  try {
    await apiFetch(`/api/v1/reports/templates/${id}`, { method: "DELETE" });
    toast.addToast(t('pages.reports.deleted'), "success");
    await loadAll();
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : t('pages.reports.deleteFailed'), "error");
  }
}

onMounted(loadAll);
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <div class="flex items-center">
          <h1 class="text-xl font-semibold text-[var(--text-primary)]">{{ t('pages.reports.title') }}</h1>
          <UInfoTooltip
            :title="t('infoTooltips.reports.title')"
            :items="tm('infoTooltips.reports.items').map((i: any) => rt(i))"
            tourId="reports-overview"
          />
        </div>
        <p class="text-xs text-[var(--text-muted)] mt-0.5">
          {{ t('pages.reports.subtitle') }}.
          <router-link to="/email-templates" class="text-[var(--primary)] hover:underline ml-1">{{ t('pages.reports.linkEmailTemplates') }}</router-link> ·
          <router-link to="/automations" class="text-[var(--primary)] hover:underline">{{ t('pages.reports.linkAutomations') }}</router-link>
        </p>
      </div>
      <button class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black hover:bg-[var(--primary-hover)]" @click="createOpen = true">
        {{ t('pages.reports.newTemplate') }}
      </button>
    </div>

    <div v-if="loading" class="text-xs text-[var(--text-muted)]">{{ t('pages.reports.loading') }}</div>

    <div v-else-if="error" class="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-400">
      <p>{{ error }}</p>
      <button class="mt-2 px-2.5 py-1 rounded text-xs font-medium border border-red-500/30 hover:bg-red-500/10" @click="loadAll">{{ t('pages.reports.retry') }}</button>
    </div>

    <!-- Templates -->
    <UEmpty v-else-if="!templates.length"
      :title="t('pages.reports.emptyTitle')"
      :description="t('pages.reports.emptyDescription')"
      icon="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
    >
      <button class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black" @click="createOpen = true">{{ t('pages.reports.createTemplate') }}</button>
    </UEmpty>

    <div v-else class="space-y-3">
      <!-- Filter -->
      <div class="flex gap-1.5">
        <button v-for="ft in [['all', t('pages.reports.filterAll')],['scheduled', t('pages.reports.filterScheduled')],['manual', t('pages.reports.filterManual')]]" :key="ft[0]"
          :class="['px-2.5 py-1 rounded-lg text-[10px] font-medium transition-colors', filterType === ft[0] ? 'bg-[var(--primary)]/15 text-[var(--primary)] border border-[var(--primary)]/30' : 'text-[var(--text-muted)] border border-[var(--border)]']"
          @click="filterType = ft[0] as any"
        >{{ ft[1] }} ({{ ft[0] === 'all' ? templates.length : ft[0] === 'scheduled' ? templates.filter(tp=>tp.schedule_cron).length : templates.filter(tp=>!tp.schedule_cron).length }})</button>
      </div>
      <div v-for="tpl in filteredTemplates" :key="tpl.id" class="border border-[var(--border)] rounded-xl bg-[var(--bg-surface)] px-5 py-4">
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-sm font-medium text-[var(--text-primary)]">{{ tpl.name }}</span>
              <UBadge v-if="tpl.schedule_cron" status="info" size="sm">{{ t('pages.reports.badgeScheduled') }}</UBadge>
              <UBadge v-if="tpl.email_recipients?.length" status="ok" size="sm">{{ t('pages.reports.badgeEmail') }}</UBadge>
            </div>
            <p v-if="tpl.description" class="text-[10px] text-[var(--text-muted)]">{{ tpl.description }}</p>
            <div class="flex items-center gap-3 mt-2 text-[10px] text-[var(--text-muted)]">
              <span v-if="tpl.schedule_cron" class="font-mono">{{ tpl.schedule_cron }}</span>
              <span v-if="tpl.email_recipients?.length">{{ t('pages.reports.recipients', { count: tpl.email_recipients.length }) }}</span>
            </div>
          </div>
          <div class="flex items-center gap-1.5 shrink-0">
            <button
              :disabled="generating === tpl.id"
              class="px-2.5 py-1 rounded-lg text-xs font-medium bg-[var(--primary)]/10 text-[var(--primary)] hover:bg-[var(--primary)]/20 disabled:opacity-50"
              @click="handleGenerate(tpl.id)"
            >{{ generating === tpl.id ? t('pages.reports.generating') : t('pages.reports.generateNow') }}</button>
            <button class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-red-400 hover:bg-red-500/10" @click="handleDelete(tpl.id)">
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79" /></svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Recent Reports -->
    <UCard v-if="reports.length">
      <template #header>
        <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('pages.reports.recentReports') }}</h3>
      </template>
      <div class="space-y-1.5">
        <a
          v-for="r in reports"
          :key="r.id"
          :href="`/api/v1/reports/download/${r.id}`"
          target="_blank"
          class="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-[var(--bg-raised)] transition-colors"
        >
          <div>
            <span class="text-xs font-medium text-[var(--text-primary)]">{{ r.title }}</span>
            <span class="text-[10px] text-[var(--text-muted)] ml-2">{{ r.format.toUpperCase() }}</span>
          </div>
          <span class="text-[10px] text-[var(--text-muted)]">{{ new Date(r.generated_at).toLocaleString() }}</span>
        </a>
      </div>
    </UCard>

    <!-- Create Modal -->
    <UModal :open="createOpen" :title="t('pages.reports.modalTitle')" @close="createOpen = false">
      <div class="space-y-3">
        <div>
          <label class="text-[10px] font-medium text-[var(--text-muted)]">{{ t('pages.reports.fieldName') }}</label>
          <input v-model="formName" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)]" :placeholder="t('pages.reports.fieldNamePlaceholder')" />
        </div>
        <div>
          <label class="text-[10px] font-medium text-[var(--text-muted)]">{{ t('pages.reports.fieldDescription') }}</label>
          <input v-model="formDesc" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)]" :placeholder="t('pages.reports.fieldDescriptionPlaceholder')" />
        </div>
        <div>
          <label class="text-[10px] font-medium text-[var(--text-muted)]">{{ t('pages.reports.fieldSchedule') }}</label>
          <select v-model="formCron" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)]">
            <option value="">{{ t('pages.reports.scheduleManualOnly') }}</option>
            <option value="0 8 * * *">{{ t('pages.reports.scheduleDaily') }}</option>
            <option value="0 8 * * 1">{{ t('pages.reports.scheduleWeekly') }}</option>
            <option value="0 8 1 * *">{{ t('pages.reports.scheduleMonthly') }}</option>
            <option value="0 */6 * * *">{{ t('pages.reports.scheduleEvery6h') }}</option>
          </select>
        </div>
        <div>
          <label class="text-[10px] font-medium text-[var(--text-muted)]">{{ t('pages.reports.fieldEmailRecipients') }}</label>
          <input v-model="formEmails" class="mt-1 w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)]" :placeholder="t('pages.reports.fieldEmailPlaceholder')" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <button class="px-3 py-2 rounded-lg text-xs text-[var(--text-muted)]" @click="createOpen = false">{{ t('pages.reports.cancel') }}</button>
          <button :disabled="saving || !formName.trim()" class="px-3 py-2 rounded-lg text-xs font-medium bg-[var(--primary)] text-black disabled:opacity-50" @click="handleCreate">
            {{ saving ? t('pages.reports.creating') : t('pages.reports.create') }}
          </button>
        </div>
      </template>
    </UModal>
  </div>
</template>
