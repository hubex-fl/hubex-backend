<script setup lang="ts">
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import UCard from "../components/ui/UCard.vue";
import UButton from "../components/ui/UButton.vue";
import UBadge from "../components/ui/UBadge.vue";
import UInfoTooltip from "../components/ui/UInfoTooltip.vue";

const { t, tm, rt } = useI18n();

const n8nUrl = import.meta.env.VITE_N8N_URL || "";
const n8nAvailable = computed(() => !!n8nUrl);

type WorkflowTemplate = {
  id: string;
  name: string;
  description: string;
  file: string;
  trigger: string;
  tags: string[];
};

const templates: WorkflowTemplate[] = [
  {
    id: "alert-to-email",
    name: t("integrations.templates.alertEmail.name"),
    description: t("integrations.templates.alertEmail.description"),
    file: "alert-to-email.json",
    trigger: "Webhook",
    tags: ["Alerts", "Email"],
  },
  {
    id: "device-offline-slack",
    name: t("integrations.templates.deviceSlack.name"),
    description: t("integrations.templates.deviceSlack.description"),
    file: "device-offline-slack.json",
    trigger: "Webhook",
    tags: ["Devices", "Slack"],
  },
  {
    id: "data-to-sheets",
    name: t("integrations.templates.dataSheets.name"),
    description: t("integrations.templates.dataSheets.description"),
    file: "data-to-google-sheets.json",
    trigger: "Schedule",
    tags: ["Data Export", "Google Sheets"],
  },
  {
    id: "bidirectional-control",
    name: t("integrations.templates.bidirectional.name"),
    description: t("integrations.templates.bidirectional.description"),
    file: "bidirectional-control.json",
    trigger: "Webhook",
    tags: ["Control", "Automation"],
  },
];

const downloading = ref<string | null>(null);

async function downloadTemplate(template: WorkflowTemplate) {
  downloading.value = template.id;
  try {
    // Try serving from public assets or API
    const paths = [
      `/docs/n8n/${template.file}`,
      `/api/v1/static/n8n/${template.file}`,
    ];
    for (const path of paths) {
      try {
        const resp = await fetch(path);
        if (resp.ok) {
          triggerDownload(await resp.blob(), template.file);
          return;
        }
      } catch { /* try next path */ }
    }
    alert(`Could not download ${template.file}. The file is available in docs/n8n/ in the HUBEX repository.`);
  } finally {
    downloading.value = null;
  }
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function openN8n() {
  window.open(n8nUrl, "_blank", "noopener,noreferrer");
}

const setupSteps = computed(() => [
  {
    step: 1,
    title: t("integrations.setup.step1.title"),
    description: t("integrations.setup.step1.description"),
    link: "/webhooks",
    linkText: t("integrations.setup.step1.link"),
  },
  {
    step: 2,
    title: t("integrations.setup.step2.title"),
    description: t("integrations.setup.step2.description"),
  },
  {
    step: 3,
    title: t("integrations.setup.step3.title"),
    description: t("integrations.setup.step3.description"),
  },
]);
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-start justify-between gap-4">
      <div>
        <div class="flex items-center">
          <h1 class="text-xl font-semibold text-[var(--text-primary)]">{{ t('integrations.title') }}</h1>
          <UInfoTooltip
            :title="t('integrations.tooltip.title')"
            :items="tm('integrations.tooltip.items').map((i: any) => rt(i))"
          />
        </div>
        <p class="text-xs text-[var(--text-muted)] mt-0.5">{{ t('integrations.subtitle') }}</p>
      </div>
    </div>

    <!-- n8n Card -->
    <UCard>
      <div class="flex items-start gap-4 p-1">
        <!-- n8n Logo -->
        <div class="flex-shrink-0 w-14 h-14 rounded-xl bg-[#EA4B71]/10 flex items-center justify-center">
          <svg viewBox="0 0 24 24" class="w-8 h-8 text-[#EA4B71]" fill="currentColor">
            <path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm-1 15.5v-3.07l-3.5-2.02v3.07L4 13.48V10.4l3.5 2.02V9.36l3.5 2.02V8.31L7.5 6.29 11 4.27l3.5 2.02-3.5 2.02v3.07l3.5-2.02v3.07l3.5-2.02V13.48l-3.5 2.02v3.07L11 20.58l-3.5-2.02L11 16.54v.96z"/>
          </svg>
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <h2 class="text-base font-semibold text-[var(--text-primary)]">n8n Workflow Automation</h2>
            <UBadge v-if="n8nAvailable" variant="success">{{ t('integrations.connected') }}</UBadge>
            <UBadge v-else variant="neutral">{{ t('integrations.notConfigured') }}</UBadge>
          </div>
          <p class="text-sm text-[var(--text-secondary)] mt-1">
            {{ t('integrations.n8nDescription') }}
          </p>
          <div class="flex items-center gap-2 mt-3">
            <UButton
              v-if="n8nAvailable"
              size="sm"
              @click="openN8n"
            >
              {{ t('integrations.openDashboard') }}
              <svg class="w-3.5 h-3.5 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </UButton>
            <UButton v-else size="sm" variant="secondary" disabled>
              {{ t('integrations.configureFirst') }}
            </UButton>
            <router-link to="/webhooks">
              <UButton size="sm" variant="secondary">{{ t('integrations.manageWebhooks') }}</UButton>
            </router-link>
          </div>
          <p v-if="!n8nAvailable" class="text-xs text-[var(--text-muted)] mt-2">
            {{ t('integrations.configureHint') }}
          </p>
        </div>
      </div>
    </UCard>

    <!-- Quick Setup -->
    <UCard>
      <h3 class="text-sm font-semibold text-[var(--text-primary)] mb-3">{{ t('integrations.quickSetup') }}</h3>
      <div class="grid gap-3 sm:grid-cols-3">
        <div
          v-for="step in setupSteps"
          :key="step.step"
          class="flex gap-3 p-3 rounded-lg bg-[var(--bg-base)]"
        >
          <div
            class="flex-shrink-0 w-7 h-7 rounded-full bg-[var(--accent-primary)]/10 text-[var(--accent-primary)] flex items-center justify-center text-xs font-bold"
          >
            {{ step.step }}
          </div>
          <div class="min-w-0">
            <p class="text-sm font-medium text-[var(--text-primary)]">{{ step.title }}</p>
            <p class="text-xs text-[var(--text-muted)] mt-0.5">{{ step.description }}</p>
            <router-link v-if="step.link" :to="step.link" class="text-xs text-[var(--accent-primary)] hover:underline mt-1 inline-block">
              {{ step.linkText }}
            </router-link>
          </div>
        </div>
      </div>
    </UCard>

    <!-- Workflow Templates -->
    <div>
      <h3 class="text-sm font-semibold text-[var(--text-primary)] mb-3">{{ t('integrations.workflowTemplates') }}</h3>
      <div class="grid gap-3 sm:grid-cols-2">
        <UCard
          v-for="tpl in templates"
          :key="tpl.id"
          class="hover:border-[var(--accent-primary)]/30 transition-colors"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="flex-1 min-w-0">
              <h4 class="text-sm font-medium text-[var(--text-primary)]">{{ tpl.name }}</h4>
              <p class="text-xs text-[var(--text-muted)] mt-1">{{ tpl.description }}</p>
              <div class="flex flex-wrap gap-1.5 mt-2">
                <UBadge variant="neutral" v-for="tag in tpl.tags" :key="tag">{{ tag }}</UBadge>
                <UBadge variant="info">{{ tpl.trigger }}</UBadge>
              </div>
            </div>
            <UButton
              size="sm"
              variant="secondary"
              :disabled="downloading === tpl.id"
              @click="downloadTemplate(tpl)"
            >
              <svg class="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              {{ downloading === tpl.id ? '...' : t('integrations.download') }}
            </UButton>
          </div>
        </UCard>
      </div>
    </div>

    <!-- Webhook Payload Reference -->
    <UCard>
      <h3 class="text-sm font-semibold text-[var(--text-primary)] mb-3">{{ t('integrations.payloadReference') }}</h3>
      <div class="rounded-lg bg-[var(--bg-base)] p-3 font-mono text-xs text-[var(--text-secondary)] overflow-x-auto">
        <pre>{
  "event": "alert.fired",
  "timestamp": "2025-01-15T10:30:00+00:00",
  "stream": "system",
  "event_id": 42,
  "data": { "severity": "warning", "title": "Temperature High", ... },
  "hubex_signature": "sha256=..."
}</pre>
      </div>
      <div class="mt-3">
        <p class="text-xs text-[var(--text-muted)]">{{ t('integrations.signatureNote') }}</p>
      </div>
    </UCard>
  </div>
</template>
