<script setup lang="ts">
import { ref, computed, onMounted, reactive } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import UToggle from "../components/ui/UToggle.vue";
import { useFeaturesStore, type FeatureFlag } from "../stores/features";
import { useToastStore } from "../stores/toast";
import { apiFetch } from "../lib/api";

const router = useRouter();
const features = useFeaturesStore();
const toast = useToastStore();
const { t } = useI18n();
const adminEmail = ref<string>("administrator");

type UseCase =
  | "industrial"
  | "smart_home"
  | "saas_backend"
  | "showcase"
  | "enterprise"
  | "everything";

interface UseCaseDef {
  id: UseCase;
  icon: string;
  // Feature keys that should be ON for this preset (all others OFF)
  enabled: Set<string>;
}

// Sprint 3.8 — Preset definitions. Labels + descriptions used to live on
// this array as English strings; they now come from i18n via
// `setupWizard.useCases.<id>.{label,description}`. Icons + feature-flag
// sets stay here because they are not translation targets.
const USE_CASES: UseCaseDef[] = [
  {
    id: "industrial",
    icon: "M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z",
    enabled: new Set([
      "automations", "webhooks", "ota", "hardware", "mcp", "audit_log",
      "api_keys", "pairing", "notifications", "observability", "semantic_types",
      "email_templates", "flow_editor", "plugins", "modules",
    ]),
  },
  {
    id: "smart_home",
    icon: "M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25",
    enabled: new Set([
      "automations", "webhooks", "hardware", "pairing", "notifications",
      "kiosk", "mcp", "ai_coop", "tours", "email_templates",
    ]),
  },
  {
    id: "saas_backend",
    icon: "M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5",
    enabled: new Set([
      "custom_api", "webhooks", "api_keys", "audit_log", "mfa",
      "automations", "reports", "observability", "email_templates",
      "semantic_types", "plugins", "integrations",
    ]),
  },
  {
    id: "showcase",
    icon: "M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9zM9 12h6m-6 3h6m-6 3h6",
    enabled: new Set([
      "cms", "kiosk", "tours", "simulator", "hardware", "mcp", "ai_coop",
      "reports", "flow_editor", "integrations",
    ]),
  },
  {
    id: "enterprise",
    icon: "M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75",
    enabled: new Set([
      "mfa", "audit_log", "api_keys", "custom_api", "reports", "observability",
      "webhooks", "automations", "semantic_types", "hardware", "ota",
      "email_templates", "notifications", "plugins", "modules",
    ]),
  },
  {
    id: "everything",
    icon: "M4.5 12.75l6 6 9-13.5",
    enabled: new Set(), // special-cased below
  },
];

// i18n-aware lookup — returns the localised preset label for a given id
function useCaseLabel(id: UseCase): string {
  return t(`setupWizard.useCases.${id}.label`);
}

function useCaseDescription(id: UseCase): string {
  return t(`setupWizard.useCases.${id}.description`);
}

const currentStep = ref(1);
const totalSteps = 5;

// Selected preset (radio-style) from step 1
const selectedUseCase = ref<UseCase | null>(null);

// The edit-set for step 2, initialized from preset, user can toggle individual items
const featureSelection = reactive<Record<string, boolean>>({});

const saving = ref(false);

onMounted(async () => {
  await features.load(true);
  // Initialize selection to current state
  for (const f of Object.values(features.flags)) {
    featureSelection[f.key] = f.enabled;
  }
  // Fetch current user email for the summary card (fail-open on error)
  try {
    const me = await apiFetch<{ email?: string }>("/api/v1/users/me");
    if (me?.email) adminEmail.value = me.email;
  } catch {
    // silently ignore — show fallback label
  }
});

const progressPercent = computed(
  () => Math.round(((currentStep.value - 1) / (totalSteps - 1)) * 100)
);

const featuresByCategory = computed(() => {
  const groups: Record<string, FeatureFlag[]> = {};
  for (const f of Object.values(features.flags)) {
    if (!groups[f.category]) groups[f.category] = [];
    groups[f.category].push(f);
  }
  for (const cat of Object.keys(groups)) {
    groups[cat].sort((a, b) => a.name.localeCompare(b.name));
  }
  return groups;
});

function selectPreset(useCase: UseCase) {
  selectedUseCase.value = useCase;
  const preset = USE_CASES.find((u) => u.id === useCase);
  if (!preset) return;
  for (const key of Object.keys(featureSelection)) {
    if (useCase === "everything") {
      featureSelection[key] = true;
    } else {
      featureSelection[key] = preset.enabled.has(key);
    }
  }
}

function enabledCountInSelection(): number {
  return Object.values(featureSelection).filter(Boolean).length;
}

async function applyAndFinish() {
  saving.value = true;
  try {
    // Apply diff: only call API for changed flags
    const changes: Array<{ key: string; enabled: boolean }> = [];
    for (const [key, wanted] of Object.entries(featureSelection)) {
      const current = features.flags[key]?.enabled ?? false;
      if (current !== wanted) changes.push({ key, enabled: wanted });
    }

    if (changes.length === 0) {
      toast.addToast(t("setupWizard.toasts.noChanges"), "info");
    } else {
      // Apply enables first (to satisfy deps), then disables
      const enables = changes.filter((c) => c.enabled);
      const disables = changes.filter((c) => !c.enabled);
      for (const { key, enabled } of [...enables, ...disables]) {
        try {
          await features.setEnabled(key, enabled);
        } catch (e: any) {
          const fallback = t("setupWizard.toasts.applyFailedFallback");
          toast.addToast(
            t("setupWizard.toasts.applyFailed", { key, message: e.message || fallback }),
            "error",
          );
        }
      }
      toast.addToast(t("setupWizard.toasts.applied", { count: changes.length }), "success");
    }
    router.push("/");
  } finally {
    saving.value = false;
  }
}

function skipWizard() {
  router.push("/");
}

function next() {
  if (currentStep.value < totalSteps) currentStep.value++;
}

function prev() {
  if (currentStep.value > 1) currentStep.value--;
}
</script>

<template>
  <div class="wizard-wrap">
    <div class="wizard-card">
      <!-- Header / progress -->
      <header class="wizard-head">
        <div class="wizard-title">
          <span class="brand">HUBEX</span> {{ t('setupWizard.title') }}
        </div>
        <div class="wizard-step">
          {{ t('setupWizard.stepXofY', { current: currentStep, total: totalSteps }) }}
        </div>
      </header>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: `${progressPercent}%` }" />
      </div>

      <!-- Step 1: Use case -->
      <section v-if="currentStep === 1" class="step">
        <h1 class="step-title">{{ t('setupWizard.step1.title') }}</h1>
        <p class="step-sub">{{ t('setupWizard.step1.subtitle') }}</p>

        <div class="use-case-grid">
          <button
            v-for="uc in USE_CASES"
            :key="uc.id"
            class="use-case-card"
            :class="{ selected: selectedUseCase === uc.id }"
            @click="selectPreset(uc.id)"
          >
            <svg viewBox="0 0 24 24" class="use-case-icon" fill="none" stroke="currentColor" stroke-width="1.5">
              <path :d="uc.icon" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <div class="use-case-name">{{ useCaseLabel(uc.id) }}</div>
            <div class="use-case-desc">{{ useCaseDescription(uc.id) }}</div>
          </button>
        </div>
      </section>

      <!-- Step 2: Feature fine-tuning -->
      <section v-else-if="currentStep === 2" class="step">
        <h1 class="step-title">{{ t('setupWizard.step2.title') }}</h1>
        <p class="step-sub">
          {{ t('setupWizard.step2.subtitle', {
            enabled: enabledCountInSelection(),
            total: Object.keys(featureSelection).length,
          }) }}
        </p>

        <div v-for="(list, cat) in featuresByCategory" :key="cat" class="feature-group">
          <div class="feature-group-head">{{ cat.toUpperCase() }}</div>
          <div class="feature-rows">
            <div v-for="f in list" :key="f.key" class="feature-row">
              <UToggle
                v-model="featureSelection[f.key]"
                size="md"
              />
              <div class="feature-row-body">
                <div class="feature-row-name">{{ f.name }}</div>
                <div class="feature-row-desc">{{ f.description }}</div>
                <div v-if="f.requires.length" class="feature-row-deps">
                  {{ t('setupWizard.step2.requiresPrefix') }} {{ f.requires.join(", ") }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Step 3: Plugins / Branding placeholder -->
      <section v-else-if="currentStep === 3" class="step">
        <h1 class="step-title">{{ t('setupWizard.step3.title') }}</h1>
        <p class="step-sub">{{ t('setupWizard.step3.subtitle') }}</p>

        <div class="info-card">
          <h3>{{ t('setupWizard.step3.pluginsTitle') }}</h3>
          <p>{{ t('setupWizard.step3.pluginsBody') }}</p>
          <div class="coming-soon">{{ t('setupWizard.step3.pluginsNow') }}</div>
        </div>

        <div class="info-card">
          <h3>{{ t('setupWizard.step3.brandingTitle') }}</h3>
          <p>{{ t('setupWizard.step3.brandingBody', { path: t('setupWizard.step3.brandingPath') }) }}</p>
          <a href="/cms/settings" class="info-link">{{ t('setupWizard.step3.brandingOpen') }}</a>
        </div>
      </section>

      <!-- Step 4: Admin check -->
      <section v-else-if="currentStep === 4" class="step">
        <h1 class="step-title">{{ t('setupWizard.step4.title') }}</h1>
        <p class="step-sub">{{ t('setupWizard.step4.subtitle') }}</p>

        <div class="info-card">
          <h3>{{ t('setupWizard.step4.adminTitle') }}</h3>
          <p>{{ t('setupWizard.step4.adminBody', { email: adminEmail }) }}</p>
          <p class="muted">{{ t('setupWizard.step4.adminMuted') }}</p>
        </div>

        <div class="summary-card">
          <div class="summary-row">
            <span>{{ t('setupWizard.step4.summaryUseCase') }}</span>
            <strong>{{ selectedUseCase ? useCaseLabel(selectedUseCase) : t('setupWizard.step4.summaryCustom') }}</strong>
          </div>
          <div class="summary-row">
            <span>{{ t('setupWizard.step4.summaryFeatures') }}</span>
            <strong>{{ enabledCountInSelection() }} / {{ Object.keys(featureSelection).length }}</strong>
          </div>
        </div>
      </section>

      <!-- Step 5: Apply -->
      <section v-else-if="currentStep === 5" class="step">
        <h1 class="step-title">{{ t('setupWizard.step5.title') }}</h1>
        <p class="step-sub">{{ t('setupWizard.step5.subtitle', { action: t('setupWizard.step5.actionRef') }) }}</p>
        <div class="launch-card">
          <div class="launch-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="64" height="64">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" />
            </svg>
          </div>
          <p class="muted">{{ t('setupWizard.step5.launchMuted') }}</p>
        </div>
      </section>

      <!-- Footer actions -->
      <footer class="wizard-foot">
        <button class="btn-ghost" @click="skipWizard">{{ t('setupWizard.footer.skip') }}</button>
        <div class="spacer" />
        <button v-if="currentStep > 1" class="btn-secondary" @click="prev" :disabled="saving">
          {{ t('setupWizard.footer.back') }}
        </button>
        <button
          v-if="currentStep < totalSteps"
          class="btn-primary"
          :disabled="currentStep === 1 && !selectedUseCase"
          @click="next"
        >
          {{ t('setupWizard.footer.next') }}
        </button>
        <button
          v-else
          class="btn-primary"
          :disabled="saving"
          @click="applyAndFinish"
        >
          {{ saving ? t('setupWizard.footer.applying') : t('setupWizard.footer.apply') }}
        </button>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.wizard-wrap {
  min-height: 100vh;
  background: #0c0c0b;
  padding: 32px 16px;
  display: flex;
  align-items: flex-start;
  justify-content: center;
}

.wizard-card {
  width: 100%;
  max-width: 860px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 40px;
  color: #e5e5e5;
}

.wizard-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.wizard-title {
  font-size: 14px;
  color: #a1a1aa;
  font-weight: 500;
  letter-spacing: 0.04em;
}

.wizard-title .brand {
  background: linear-gradient(135deg, #f5a623 0%, #2dd4bf 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  font-weight: 800;
  font-family: "Satoshi", "Inter", sans-serif;
}

.wizard-step {
  font-size: 13px;
  color: #71717a;
  font-family: "IBM Plex Mono", monospace;
}

.progress-track {
  height: 4px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 32px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #f5a623, #2dd4bf);
  border-radius: 2px;
  transition: width 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.step {
  min-height: 420px;
}

.step-title {
  font-size: 32px;
  font-weight: 800;
  margin: 0 0 8px;
  color: #f5f5f5;
  letter-spacing: -0.01em;
  font-family: "Satoshi", "Inter", sans-serif;
}

.step-sub {
  color: #a1a1aa;
  margin: 0 0 24px;
  font-size: 15px;
}

/* Step 1 — Use-case grid */
.use-case-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 16px;
}

.use-case-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px;
  text-align: left;
  cursor: pointer;
  color: inherit;
  font-family: inherit;
  transition: all 0.15s ease;
}

.use-case-card:hover {
  border-color: rgba(245, 166, 35, 0.4);
  transform: translateY(-2px);
}

.use-case-card.selected {
  border-color: #f5a623;
  background: rgba(245, 166, 35, 0.08);
}

.use-case-icon {
  width: 28px;
  height: 28px;
  color: #f5a623;
  margin-bottom: 12px;
}

.use-case-name {
  font-size: 16px;
  font-weight: 700;
  color: #f5f5f5;
  margin-bottom: 4px;
}

.use-case-desc {
  font-size: 13px;
  color: #a1a1aa;
  line-height: 1.5;
}

/* Step 2 — Feature list */
.feature-group {
  margin-bottom: 24px;
}

.feature-group-head {
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
  color: #f5a623;
  margin-bottom: 8px;
  letter-spacing: 0.1em;
}

.feature-rows {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.feature-row {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.feature-row-body {
  flex: 1;
  min-width: 0;
}

.feature-row-name {
  font-size: 14px;
  font-weight: 600;
  color: #f5f5f5;
}

.feature-row-desc {
  font-size: 12px;
  color: #a1a1aa;
  margin-top: 2px;
  line-height: 1.4;
}

.feature-row-deps {
  font-size: 11px;
  color: #71717a;
  margin-top: 4px;
  font-family: "IBM Plex Mono", monospace;
}

/* Info cards / summary */
.info-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 16px;
}

.info-card h3 {
  margin: 0 0 6px;
  font-size: 15px;
  color: #f5f5f5;
}

.info-card p {
  margin: 0 0 8px;
  color: #a1a1aa;
  font-size: 14px;
  line-height: 1.5;
}

.info-card .muted {
  color: #71717a;
  font-size: 12px;
}

.info-link {
  color: #2dd4bf;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
}

.coming-soon {
  display: inline-block;
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
  color: #f5a623;
  background: rgba(245, 166, 35, 0.1);
  padding: 3px 8px;
  border-radius: 4px;
  margin-top: 4px;
}

.summary-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(45, 212, 191, 0.2);
  border-radius: 10px;
  padding: 20px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  font-size: 14px;
}

.summary-row strong {
  color: #2dd4bf;
}

.launch-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48px 24px;
  text-align: center;
}

.launch-icon {
  color: #f5a623;
  margin-bottom: 16px;
}

/* Footer */
.wizard-foot {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.spacer {
  flex: 1;
}

.btn-primary,
.btn-secondary,
.btn-ghost {
  padding: 10px 24px;
  border-radius: 8px;
  border: none;
  font-weight: 600;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.15s ease;
}

.btn-primary {
  background: #f5a623;
  color: #111110;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(245, 166, 35, 0.3);
}

.btn-primary:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-secondary {
  background: transparent;
  color: #e5e5e5;
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.btn-secondary:hover:not(:disabled) {
  border-color: rgba(255, 255, 255, 0.3);
}

.btn-ghost {
  background: transparent;
  color: #71717a;
  padding: 10px 12px;
}

.btn-ghost:hover {
  color: #a1a1aa;
}
</style>
