<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../lib/api";
import { downloadProjectZip, CodegenError } from "../lib/codegen";
import { useToastStore } from "../stores/toast";
import { useBoardLabels } from "../composables/useBoardLabels";
import { useComponentLabels } from "../composables/useComponentLabels";

const { t } = useI18n();
const { boardName, boardDescription } = useBoardLabels();
const { componentName, componentDescription } = useComponentLabels();

interface Board {
  id: number;
  name: string;
  chip: string;
  description: string | null;
  wifi_capable: boolean;
  bluetooth_capable: boolean;
}

interface ComponentDef {
  id: number;
  key: string;
  name: string;
  category: string; // sensor | actuator | display | module
  bus_type: string | null;
  pin_requirements: Array<{ type: string; count: number; label?: string }>;
  libraries_required: string[];
  variables: Array<{ key: string; unit?: string; direction?: string }>;
  description: string | null;
}

const router = useRouter();
const toast = useToastStore();

// ─── Wizard state ────────────────────────────────────────────────────────
const currentStep = ref(1);
const totalSteps = 5;

const boards = ref<Board[]>([]);
const components = ref<ComponentDef[]>([]);
const loading = ref(true);

const selectedBoardChip = ref<string | null>(null);
const selectedFramework = ref<"platformio" | "arduino" | "micropython" | null>(null);
const selectedComponentKeys = ref<Set<string>>(new Set());
const wifiSsid = ref("");
const wifiPass = ref("");
const serverUrl = ref("");
const deviceName = ref("");

const submitting = ref(false);
const lastResult = ref<{ device_id: number | null; device_uid: string | null; filename: string } | null>(null);

onMounted(async () => {
  serverUrl.value = window.location.origin;
  loading.value = true;
  try {
    const [boardsRes, componentsRes] = await Promise.all([
      apiFetch<Board[]>("/api/v1/hardware/boards"),
      apiFetch<ComponentDef[]>("/api/v1/components"),
    ]);
    // Dedupe by chip (the backend can have duplicate seed rows)
    const byChip = new Map<string, Board>();
    for (const b of boardsRes) {
      if (!byChip.has(b.chip)) byChip.set(b.chip, b);
    }
    boards.value = Array.from(byChip.values());
    components.value = componentsRes;
  } catch (e: any) {
    toast.addToast(e?.message || t("hardwareWizard.loadCatalogFailed"), "error");
  } finally {
    loading.value = false;
  }
});

// ─── Derived ─────────────────────────────────────────────────────────────
const progressPercent = computed(
  () => Math.round(((currentStep.value - 1) / (totalSteps - 1)) * 100)
);

const sensors = computed(() => components.value.filter((c) => c.category === "sensor"));
const actuators = computed(() =>
  components.value.filter((c) => c.category === "actuator" || c.category === "display")
);

const selectedComponents = computed(() =>
  components.value.filter((c) => selectedComponentKeys.value.has(c.key))
);

// Very rough client-side preview of component support in MicroPython
const MPY_SUPPORTED = new Set([
  "dht22", "ds18b20", "analog_input", "pir", "button", "relay", "led_pwm", "buzzer",
]);

function isMpySupported(key: string): boolean {
  return MPY_SUPPORTED.has(key);
}

const canAdvance = computed(() => {
  if (currentStep.value === 1) return selectedBoardChip.value !== null;
  if (currentStep.value === 2) return selectedFramework.value !== null;
  if (currentStep.value === 3) return selectedComponentKeys.value.size > 0;
  if (currentStep.value === 4) return true; // wifi optional
  if (currentStep.value === 5) return deviceName.value.trim().length > 0;
  return false;
});

const selectedBoard = computed(() =>
  boards.value.find((b) => b.chip === selectedBoardChip.value) || null
);

// ─── Navigation ──────────────────────────────────────────────────────────
function next() {
  if (canAdvance.value && currentStep.value < totalSteps) currentStep.value++;
}
function prev() {
  if (currentStep.value > 1) currentStep.value--;
}
function cancel() {
  router.push("/hardware");
}

function selectBoard(chip: string) {
  selectedBoardChip.value = chip;
}
function selectFramework(fw: "platformio" | "arduino" | "micropython") {
  selectedFramework.value = fw;
}
function toggleComponent(key: string) {
  const next = new Set(selectedComponentKeys.value);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  selectedComponentKeys.value = next;
}

// ─── Final step: download ────────────────────────────────────────────────
async function downloadProject() {
  if (!selectedBoardChip.value || !selectedFramework.value) return;
  submitting.value = true;
  try {
    const result = await downloadProjectZip({
      device_name: deviceName.value.trim() || "HubEx Device",
      board_key: selectedBoardChip.value,
      framework: selectedFramework.value,
      component_keys: Array.from(selectedComponentKeys.value),
      wifi_ssid: wifiSsid.value,
      wifi_pass: wifiPass.value,
      server_url: serverUrl.value,
    });
    lastResult.value = result;
    toast.addToast(
      t("hardwareWizard.toast.created", {
        id: result.device_id ?? "",
        filename: result.filename,
      }),
      "success",
      6000
    );
  } catch (e: any) {
    if (e instanceof CodegenError) {
      toast.addToast(`${e.code}: ${e.message}`, "error", 8000);
    } else {
      toast.addToast(e?.message || t("hardwareWizard.toast.downloadFailed"), "error");
    }
  } finally {
    submitting.value = false;
  }
}

function goToDevices() {
  router.push("/devices");
}
function resetWizard() {
  currentStep.value = 1;
  selectedBoardChip.value = null;
  selectedFramework.value = null;
  selectedComponentKeys.value = new Set();
  deviceName.value = "";
  lastResult.value = null;
}
</script>

<template>
  <div class="hw-wizard-wrap">
    <div class="wizard-card">
      <!-- Header -->
      <header class="wiz-head">
        <div class="wiz-title"><span class="brand">HUBEX</span> · {{ t('hardwareWizard.brandTitle') }}</div>
        <div class="wiz-step">{{ t('hardwareWizard.stepOfTotal', { current: currentStep, total: totalSteps }) }}</div>
      </header>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: `${progressPercent}%` }" />
      </div>

      <!-- Loading -->
      <div v-if="loading" class="loading-block">{{ t('hardwareWizard.loadingCatalog') }}</div>

      <!-- Step 1: Board -->
      <section v-else-if="currentStep === 1" class="step">
        <h1 class="step-title">{{ t('hardwareWizard.step1.title') }}</h1>
        <p class="step-sub">{{ t('hardwareWizard.step1.subtitle') }}</p>

        <div class="board-grid">
          <button
            v-for="b in boards"
            :key="b.chip"
            class="board-card"
            :class="{ selected: selectedBoardChip === b.chip }"
            @click="selectBoard(b.chip)"
          >
            <div class="board-chip-badge">{{ b.chip }}</div>
            <div class="board-name">{{ boardName(b) }}</div>
            <div v-if="boardDescription(b)" class="board-desc">{{ boardDescription(b) }}</div>
            <div class="board-tags">
              <span v-if="b.wifi_capable" class="tag">{{ t('hardwareWizard.step1.tagWifi') }}</span>
              <span v-if="b.bluetooth_capable" class="tag">{{ t('hardwareWizard.step1.tagBle') }}</span>
            </div>
          </button>
        </div>
      </section>

      <!-- Step 2: Framework -->
      <section v-else-if="currentStep === 2" class="step">
        <h1 class="step-title">{{ t('hardwareWizard.step2.title') }}</h1>
        <p class="step-sub">{{ t('hardwareWizard.step2.subtitle') }}</p>

        <div class="fw-grid">
          <button
            class="fw-card"
            :class="{ selected: selectedFramework === 'platformio' }"
            @click="selectFramework('platformio')"
          >
            <div class="fw-name">
              {{ t('hardwareWizard.step2.platformioName') }}
              <span class="recommended">{{ t('hardwareWizard.step2.recommended') }}</span>
            </div>
            <div class="fw-desc">
              <i18n-t keypath="hardwareWizard.step2.platformioDesc" scope="global">
                <template #iniFile><strong>platformio.ini</strong></template>
                <template #mainFile><code>src/main.cpp</code></template>
                <template #runCmd><code>pio run -t upload</code></template>
              </i18n-t>
            </div>
          </button>

          <button
            class="fw-card"
            :class="{ selected: selectedFramework === 'arduino' }"
            @click="selectFramework('arduino')"
          >
            <div class="fw-name">{{ t('hardwareWizard.step2.arduinoName') }}</div>
            <div class="fw-desc">
              <i18n-t keypath="hardwareWizard.step2.arduinoDesc" scope="global">
                <template #sketchFile><code>.ino</code></template>
              </i18n-t>
            </div>
          </button>

          <button
            class="fw-card"
            :class="{ selected: selectedFramework === 'micropython' }"
            @click="selectFramework('micropython')"
          >
            <div class="fw-name">{{ t('hardwareWizard.step2.micropythonName') }}</div>
            <div class="fw-desc">
              <i18n-t keypath="hardwareWizard.step2.micropythonDesc" scope="global">
                <template #bootFile><code>boot.py</code></template>
                <template #mainFile><code>main.py</code></template>
              </i18n-t>
            </div>
          </button>
        </div>
      </section>

      <!-- Step 3: Components -->
      <section v-else-if="currentStep === 3" class="step">
        <h1 class="step-title">{{ t('hardwareWizard.step3.title') }}</h1>
        <p class="step-sub">
          {{ t('hardwareWizard.step3.subtitle', { count: selectedComponentKeys.size }) }}
        </p>

        <div class="comp-section-head">{{ t('hardwareWizard.step3.sectionSensors') }}</div>
        <div class="comp-grid">
          <button
            v-for="c in sensors"
            :key="c.key"
            class="comp-card"
            :class="{ selected: selectedComponentKeys.has(c.key) }"
            @click="toggleComponent(c.key)"
          >
            <div class="comp-check" :class="{ checked: selectedComponentKeys.has(c.key) }">
              <svg v-if="selectedComponentKeys.has(c.key)" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="5,12 10,17 19,8" />
              </svg>
            </div>
            <div class="comp-body">
              <div class="comp-name">
                {{ componentName(c) }}
                <span v-if="c.bus_type" class="bus-tag">{{ c.bus_type }}</span>
                <span
                  v-if="selectedFramework === 'micropython' && !isMpySupported(c.key)"
                  class="warn-tag"
                  :title="t('hardwareWizard.step3.warnMpyTodoTooltip')"
                >{{ t('hardwareWizard.step3.warnMpyTodo') }}</span>
              </div>
              <div class="comp-desc">{{ componentDescription(c) }}</div>
              <div v-if="c.variables.length" class="comp-vars">
                {{ t('hardwareWizard.step3.variablesLabel') }} {{ c.variables.map(v => v.key + (v.unit ? ` (${v.unit})` : '')).join(", ") }}
              </div>
            </div>
          </button>
        </div>

        <div class="comp-section-head">{{ t('hardwareWizard.step3.sectionActuators') }}</div>
        <div class="comp-grid">
          <button
            v-for="c in actuators"
            :key="c.key"
            class="comp-card"
            :class="{ selected: selectedComponentKeys.has(c.key) }"
            @click="toggleComponent(c.key)"
          >
            <div class="comp-check" :class="{ checked: selectedComponentKeys.has(c.key) }">
              <svg v-if="selectedComponentKeys.has(c.key)" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="5,12 10,17 19,8" />
              </svg>
            </div>
            <div class="comp-body">
              <div class="comp-name">
                {{ componentName(c) }}
                <span v-if="c.bus_type" class="bus-tag">{{ c.bus_type }}</span>
                <span
                  v-if="selectedFramework === 'micropython' && !isMpySupported(c.key)"
                  class="warn-tag"
                  :title="t('hardwareWizard.step3.warnMpyTodoTooltip')"
                >{{ t('hardwareWizard.step3.warnMpyTodo') }}</span>
              </div>
              <div class="comp-desc">{{ componentDescription(c) }}</div>
            </div>
          </button>
        </div>
      </section>

      <!-- Step 4: Transport -->
      <section v-else-if="currentStep === 4" class="step">
        <h1 class="step-title">{{ t('hardwareWizard.step4.title') }}</h1>
        <p class="step-sub">{{ t('hardwareWizard.step4.subtitle') }}</p>

        <div class="form-grid">
          <label class="form-field">
            <span class="label-text">{{ t('hardwareWizard.step4.wifiSsid') }}</span>
            <input v-model="wifiSsid" type="text" :placeholder="t('hardwareWizard.step4.wifiSsidPlaceholder')" class="form-input" />
          </label>
          <label class="form-field">
            <span class="label-text">{{ t('hardwareWizard.step4.wifiPassword') }}</span>
            <input v-model="wifiPass" type="password" placeholder="••••••••" class="form-input" />
          </label>
          <label class="form-field full">
            <span class="label-text">{{ t('hardwareWizard.step4.serverUrl') }}</span>
            <input v-model="serverUrl" type="text" placeholder="http://192.168.1.100:8000" class="form-input" />
            <span class="field-hint">{{ t('hardwareWizard.step4.serverUrlHint') }}</span>
          </label>
        </div>
      </section>

      <!-- Step 5: Name + Download -->
      <section v-else-if="currentStep === 5 && !lastResult" class="step">
        <h1 class="step-title">{{ t('hardwareWizard.step5.title') }}</h1>
        <p class="step-sub">
          {{ t('hardwareWizard.step5.subtitleBefore') }}<strong>{{ t('hardwareWizard.step5.subtitleDevicesLink') }}</strong>{{ t('hardwareWizard.step5.subtitleAfter') }}
        </p>

        <div class="form-grid">
          <label class="form-field full">
            <span class="label-text">{{ t('hardwareWizard.step5.deviceName') }}</span>
            <input v-model="deviceName" type="text" :placeholder="t('hardwareWizard.step5.deviceNamePlaceholder')" class="form-input" />
          </label>
        </div>

        <div class="summary-card">
          <div class="summary-row"><span>{{ t('hardwareWizard.step5.summaryBoard') }}</span><strong>{{ selectedBoard ? boardName(selectedBoard) : t('hardwareWizard.step5.summaryBoardEmpty') }}</strong></div>
          <div class="summary-row"><span>{{ t('hardwareWizard.step5.summaryFramework') }}</span><strong>{{ selectedFramework }}</strong></div>
          <div class="summary-row"><span>{{ t('hardwareWizard.step5.summaryComponents') }}</span><strong>{{ selectedComponentKeys.size }}</strong></div>
          <div class="summary-row"><span>{{ t('hardwareWizard.step5.summaryWifiSsid') }}</span><strong>{{ wifiSsid || t('hardwareWizard.step5.summaryWifiEmpty') }}</strong></div>
          <div class="summary-row"><span>{{ t('hardwareWizard.step5.summaryServerUrl') }}</span><strong>{{ serverUrl }}</strong></div>
        </div>

        <div class="comp-list-summary">
          <div v-for="c in selectedComponents" :key="c.key" class="comp-chip">
            {{ componentName(c) }}
          </div>
        </div>
      </section>

      <!-- Step 5b: Success screen (after download) -->
      <section v-else-if="currentStep === 5 && lastResult" class="step">
        <div class="success-block">
          <div class="success-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="64" height="64">
              <circle cx="12" cy="12" r="10" />
              <polyline points="8,12 11,15 16,9" />
            </svg>
          </div>
          <h1 class="step-title">{{ t('hardwareWizard.success.title') }}</h1>
          <p class="step-sub">{{ t('hardwareWizard.success.subtitle') }}</p>

          <div class="summary-card">
            <div class="summary-row"><span>{{ t('hardwareWizard.success.summaryZip') }}</span><strong>{{ lastResult.filename }}</strong></div>
            <div class="summary-row"><span>{{ t('hardwareWizard.success.summaryDeviceId') }}</span><strong>#{{ lastResult.device_id }}</strong></div>
            <div class="summary-row"><span>{{ t('hardwareWizard.success.summaryDeviceUid') }}</span><strong>{{ lastResult.device_uid }}</strong></div>
          </div>

          <p class="hint">
            {{ t('hardwareWizard.success.hintBefore') }}<strong>{{ t('hardwareWizard.success.hintDevicesLink') }}</strong>{{ t('hardwareWizard.success.hintAfter') }}
          </p>

          <div class="success-actions">
            <button class="btn-primary" @click="goToDevices">{{ t('hardwareWizard.success.ctaGoToDevices') }}</button>
            <button class="btn-secondary" @click="resetWizard">{{ t('hardwareWizard.success.ctaNewProject') }}</button>
          </div>
        </div>
      </section>

      <!-- Footer -->
      <footer v-if="!lastResult" class="wiz-foot">
        <button class="btn-ghost" @click="cancel">{{ t('hardwareWizard.footer.cancel') }}</button>
        <div class="spacer" />
        <button v-if="currentStep > 1" class="btn-secondary" :disabled="submitting" @click="prev">
          {{ t('hardwareWizard.footer.back') }}
        </button>
        <button
          v-if="currentStep < totalSteps"
          class="btn-primary"
          :disabled="!canAdvance || submitting"
          @click="next"
        >
          {{ t('hardwareWizard.footer.next') }}
        </button>
        <button
          v-else
          class="btn-primary download-btn"
          :disabled="!canAdvance || submitting"
          @click="downloadProject"
        >
          {{ submitting ? t('hardwareWizard.footer.generating') : t('hardwareWizard.footer.downloadProject') }}
        </button>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.hw-wizard-wrap {
  min-height: 100vh;
  padding: 32px 16px;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.wizard-card {
  width: 100%;
  max-width: 900px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 40px;
  color: #e5e5e5;
}

.wiz-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.wiz-title {
  font-size: 14px;
  color: #a1a1aa;
  font-weight: 500;
}

.brand {
  background: linear-gradient(135deg, #F5A623 0%, #2DD4BF 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  font-weight: 800;
  font-family: "Satoshi", "Inter", sans-serif;
}

.wiz-step {
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
  background: linear-gradient(90deg, #F5A623, #2DD4BF);
  transition: width 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.step {
  min-height: 420px;
}

.step-title {
  font-size: 30px;
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

.loading-block {
  min-height: 420px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a1a1aa;
}

/* --- Step 1: board grid --- */
.board-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 16px;
}

.board-card {
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

.board-card:hover {
  border-color: rgba(245, 166, 35, 0.4);
  transform: translateY(-2px);
}

.board-card.selected {
  border-color: #F5A623;
  background: rgba(245, 166, 35, 0.08);
}

.board-chip-badge {
  display: inline-block;
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
  color: #F5A623;
  background: rgba(245, 166, 35, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
  margin-bottom: 8px;
}

.board-name {
  font-size: 16px;
  font-weight: 700;
  color: #f5f5f5;
  margin-bottom: 6px;
}

.board-desc {
  font-size: 13px;
  color: #a1a1aa;
  line-height: 1.4;
  margin-bottom: 8px;
}

.board-tags {
  display: flex;
  gap: 6px;
}

.tag {
  display: inline-block;
  font-size: 10px;
  padding: 2px 6px;
  background: rgba(45, 212, 191, 0.1);
  color: #2DD4BF;
  border-radius: 3px;
  font-family: "IBM Plex Mono", monospace;
}

/* --- Step 2: framework grid --- */
.fw-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.fw-card {
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

.fw-card:hover {
  border-color: rgba(245, 166, 35, 0.4);
}

.fw-card.selected {
  border-color: #F5A623;
  background: rgba(245, 166, 35, 0.08);
}

.fw-name {
  font-size: 17px;
  font-weight: 700;
  color: #f5f5f5;
  margin-bottom: 6px;
}

.recommended {
  display: inline-block;
  font-size: 10px;
  padding: 2px 6px;
  background: rgba(45, 212, 191, 0.15);
  color: #2DD4BF;
  border-radius: 3px;
  margin-left: 8px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.fw-desc {
  font-size: 13px;
  color: #a1a1aa;
  line-height: 1.5;
}

.fw-desc code {
  background: rgba(255, 255, 255, 0.06);
  padding: 1px 5px;
  border-radius: 3px;
  font-family: "IBM Plex Mono", monospace;
  font-size: 12px;
  color: #F5A623;
}

/* --- Step 3: components --- */
.comp-section-head {
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
  color: #F5A623;
  margin: 16px 0 10px;
  letter-spacing: 0.1em;
}

.comp-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 10px;
  margin-bottom: 8px;
}

.comp-card {
  display: flex;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  text-align: left;
  cursor: pointer;
  color: inherit;
  font-family: inherit;
  transition: all 0.12s ease;
}

.comp-card:hover {
  border-color: rgba(255, 255, 255, 0.15);
}

.comp-card.selected {
  border-color: #F5A623;
  background: rgba(245, 166, 35, 0.06);
}

.comp-check {
  width: 20px;
  height: 20px;
  min-width: 20px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #111110;
}

.comp-check.checked {
  background: #F5A623;
  border-color: #F5A623;
}

.comp-body {
  flex: 1;
  min-width: 0;
}

.comp-name {
  font-size: 14px;
  font-weight: 600;
  color: #f5f5f5;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.bus-tag,
.warn-tag {
  font-family: "IBM Plex Mono", monospace;
  font-size: 9px;
  padding: 1px 5px;
  border-radius: 2px;
}

.bus-tag {
  background: rgba(45, 212, 191, 0.12);
  color: #2DD4BF;
}

.warn-tag {
  background: rgba(239, 68, 68, 0.12);
  color: #f87171;
}

.comp-desc {
  font-size: 12px;
  color: #a1a1aa;
  line-height: 1.4;
  margin-top: 3px;
}

.comp-vars {
  font-size: 11px;
  color: #71717a;
  margin-top: 4px;
  font-family: "IBM Plex Mono", monospace;
}

/* --- Step 4: form --- */
.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.form-field {
  display: flex;
  flex-direction: column;
}

.form-field.full {
  grid-column: 1 / -1;
}

.label-text {
  font-size: 12px;
  color: #a1a1aa;
  margin-bottom: 6px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.form-input {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 10px 12px;
  color: #f5f5f5;
  font-size: 14px;
  font-family: inherit;
}

.form-input:focus {
  outline: none;
  border-color: #F5A623;
}

.field-hint {
  font-size: 12px;
  color: #71717a;
  margin-top: 6px;
  line-height: 1.4;
}

/* --- Summary + success --- */
.summary-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(45, 212, 191, 0.2);
  border-radius: 10px;
  padding: 16px 20px;
  margin: 24px 0 12px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 13px;
}

.summary-row strong {
  color: #2DD4BF;
  font-family: "IBM Plex Mono", monospace;
  font-size: 12px;
}

.comp-list-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.comp-chip {
  font-size: 12px;
  padding: 4px 10px;
  background: rgba(245, 166, 35, 0.08);
  color: #F5A623;
  border-radius: 12px;
  border: 1px solid rgba(245, 166, 35, 0.2);
}

.success-block {
  text-align: center;
}

.success-icon {
  color: #2DD4BF;
  display: inline-block;
  padding: 16px;
  border-radius: 50%;
  background: rgba(45, 212, 191, 0.08);
  margin-bottom: 16px;
}

.hint {
  color: #a1a1aa;
  font-size: 14px;
  line-height: 1.5;
  margin: 24px 0;
}

.hint strong {
  color: #f5f5f5;
}

.success-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 16px;
}

/* --- Footer --- */
.wiz-foot {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.spacer { flex: 1; }

.btn-primary,
.btn-secondary,
.btn-ghost {
  padding: 10px 22px;
  border-radius: 8px;
  border: none;
  font-weight: 600;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-primary {
  background: #F5A623;
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

.download-btn {
  background: linear-gradient(135deg, #F5A623 0%, #2DD4BF 100%);
  color: #111110;
  padding: 12px 28px;
  font-size: 15px;
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
}

.btn-ghost:hover {
  color: #a1a1aa;
}
</style>
