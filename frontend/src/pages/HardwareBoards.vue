<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { apiFetch } from "../lib/api";
import { useBoardLabels } from "../composables/useBoardLabels";
import { useShieldLabels } from "../composables/useShieldLabels";
import UCard from "../components/ui/UCard.vue";
import UBadge from "../components/ui/UBadge.vue";

const { t } = useI18n();
const router = useRouter();
const { boardName, boardDescription } = useBoardLabels();
const { shieldName, shieldDescription } = useShieldLabels();

function openWizard() {
  router.push("/hardware/wizard");
}

type Pin = { number: number; label: string; capabilities: string[] };
type Board = {
  id: number; name: string; chip: string; pins: Pin[];
  flash_size_kb: number; ram_size_kb: number;
  wifi_capable: boolean; bluetooth_capable: boolean;
  is_builtin: boolean; description: string | null; image_url: string | null;
};
type Shield = {
  id: number; name: string; target_chip: string | null;
  occupied_pins: number[]; exposed_pins: number[];
  bus_type: string | null; components: Array<Record<string, unknown>> | null;
  description: string | null; is_builtin: boolean;
};

const boards = ref<Board[]>([]);
const shields = ref<Shield[]>([]);
const loading = ref(true);
const selectedBoard = ref<Board | null>(null);
const error = ref<string | null>(null);

const CHIP_COLORS: Record<string, string> = {
  esp32: "var(--primary)",
  esp32s3: "#10B981",
  esp32c3: "#6366F1",
  rp2040: "#EC4899",
  atmega328: "#3B82F6",
};

async function loadAll() {
  loading.value = true;
  error.value = null;
  try {
    const [b, s] = await Promise.allSettled([
      apiFetch<Board[]>("/api/v1/hardware/boards"),
      apiFetch<Shield[]>("/api/v1/hardware/shields"),
    ]);
    boards.value = b.status === "fulfilled" ? b.value : [];
    shields.value = s.status === "fulfilled" ? s.value : [];
    if (b.status === "rejected" && s.status === "rejected") error.value = t('hardware.loadError');
  } finally {
    loading.value = false;
  }
}

const pinCapColors: Record<string, string> = {
  digital_io: "var(--status-ok)", adc: "var(--primary)", pwm: "var(--accent)",
  i2c_sda: "#8B5CF6", i2c_scl: "#8B5CF6", spi: "#EC4899",
  uart_tx: "#F59E0B", uart_rx: "#F59E0B", dac: "#6366F1",
  touch: "#14B8A6",
};

onMounted(loadAll);
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div>
        <h1 class="text-xl font-semibold text-[var(--text-primary)]">{{ t('hardware.title') }}</h1>
        <p class="text-xs text-[var(--text-muted)] mt-0.5">{{ t('hardware.subtitle') }}</p>
      </div>
      <button class="wizard-cta-btn" @click="openWizard">
        <span class="cta-plus">+</span>
        {{ t('hardware.newProjectCta') }}
      </button>
    </div>
    <div class="wizard-hint">
      <strong>{{ t('hardware.wizardHintLabel') }}</strong> {{ t('hardware.wizardHintBody') }}
    </div>

    <div v-if="loading" class="text-xs text-[var(--text-muted)]">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-400">
      <p>{{ error }}</p>
      <button class="mt-2 px-2.5 py-1 rounded text-xs border border-red-500/30" @click="loadAll">{{ t('hardware.retry') }}</button>
    </div>

    <template v-else>
      <!-- Board Cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="board in boards" :key="board.id"
          :class="['border rounded-xl bg-[var(--bg-surface)] p-4 cursor-pointer transition-all hover:shadow-lg', selectedBoard?.id === board.id ? 'border-[var(--primary)] ring-1 ring-[var(--primary)]/30' : 'border-[var(--border)]']"
          @click="selectedBoard = selectedBoard?.id === board.id ? null : board"
        >
          <div class="flex items-center gap-2 mb-2">
            <div class="h-3 w-3 rounded-full" :style="{ background: CHIP_COLORS[board.chip] || 'var(--text-muted)' }" />
            <span class="text-sm font-medium text-[var(--text-primary)]">{{ boardName(board) }}</span>
          </div>
          <div class="flex flex-wrap gap-1.5 mb-2">
            <UBadge status="info" size="sm">{{ board.chip }}</UBadge>
            <UBadge v-if="board.wifi_capable" status="ok" size="sm">WiFi</UBadge>
            <UBadge v-if="board.bluetooth_capable" status="neutral" size="sm">BLE</UBadge>
          </div>
          <p v-if="boardDescription(board)" class="text-[10px] text-[var(--text-muted)] line-clamp-2">{{ boardDescription(board) }}</p>
          <div class="flex items-center gap-3 mt-2 text-[10px] text-[var(--text-muted)]">
            <span>{{ board.pins.length }} {{ t('hardware.pins') }}</span>
            <span>{{ board.flash_size_kb }}KB {{ t('hardware.flash') }}</span>
            <span>{{ board.ram_size_kb }}KB {{ t('hardware.ram') }}</span>
          </div>
        </div>
      </div>

      <!-- Selected Board Pin-Map -->
      <UCard v-if="selectedBoard">
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ boardName(selectedBoard) }} — {{ t('hardware.pinMap') }}</h3>
            <button class="text-xs text-[var(--text-muted)]" @click="selectedBoard = null">{{ t('common.close') }}</button>
          </div>
        </template>
        <div class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2">
          <div
            v-for="pin in selectedBoard.pins" :key="pin.number"
            class="border border-[var(--border)] rounded-lg p-2 bg-[var(--bg-raised)] hover:border-[var(--primary)]/40 transition-colors"
          >
            <div class="flex items-center justify-between mb-1">
              <span class="text-xs font-mono font-bold text-[var(--text-primary)]">{{ pin.label }}</span>
              <span class="text-[9px] text-[var(--text-muted)]">#{{ pin.number }}</span>
            </div>
            <div class="flex flex-wrap gap-0.5">
              <span
                v-for="cap in pin.capabilities" :key="cap"
                :style="{ background: (pinCapColors[cap] || 'var(--text-muted)') + '20', color: pinCapColors[cap] || 'var(--text-muted)' }"
                class="text-[8px] px-1 py-0.5 rounded font-mono"
              >{{ cap.replace('_', '') }}</span>
            </div>
          </div>
        </div>
      </UCard>

      <!-- Shields -->
      <UCard>
        <template #header>
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('hardware.shieldsModules') }}</h3>
          <span class="text-xs text-[var(--text-muted)]">{{ t('hardware.shieldsDesc') }}</span>
        </template>
        <div v-if="!shields.length" class="text-xs text-[var(--text-muted)] py-2">{{ t('hardware.noShields') }}</div>
        <div v-else class="space-y-2">
          <div v-for="s in shields" :key="s.id" class="flex items-start gap-3 px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-raised)]">
            <div class="flex-1">
              <div class="flex items-center gap-2">
                <span class="text-xs font-medium text-[var(--text-primary)]">{{ shieldName(s) }}</span>
                <UBadge v-if="s.bus_type" status="info" size="sm">{{ s.bus_type }}</UBadge>
                <UBadge v-if="s.target_chip" status="neutral" size="sm">{{ s.target_chip }}</UBadge>
                <UBadge v-else status="neutral" size="sm">{{ t('hardware.shieldBadgeUniversal') }}</UBadge>
              </div>
              <p v-if="shieldDescription(s)" class="text-[10px] text-[var(--text-muted)] mt-0.5">{{ shieldDescription(s) }}</p>
              <div v-if="s.components?.length" class="flex gap-1 mt-1">
                <span v-for="(c, i) in s.components" :key="i" class="text-[9px] px-1 py-0.5 rounded bg-[var(--bg-base)] border border-[var(--border)] font-mono text-[var(--text-muted)]">
                  {{ (c as Record<string, unknown>).model || (c as Record<string, unknown>).type }}
                </span>
              </div>
            </div>
            <div class="text-[10px] text-[var(--text-muted)] shrink-0">{{ s.occupied_pins.length }} {{ t('hardware.pins') }}</div>
          </div>
        </div>
      </UCard>
    </template>
  </div>
</template>

<style scoped>
.wizard-cta-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: linear-gradient(135deg, #F5A623 0%, #E09318 100%);
  color: #111110;
  border: none;
  border-radius: 10px;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  font-family: inherit;
  box-shadow: 0 4px 12px rgba(245, 166, 35, 0.25);
}

.wizard-cta-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(245, 166, 35, 0.35);
}

.cta-plus {
  font-size: 18px;
  font-weight: 800;
  line-height: 1;
}

.wizard-hint {
  font-size: 12px;
  color: var(--text-muted);
  background: rgba(245, 166, 35, 0.05);
  border: 1px solid rgba(245, 166, 35, 0.15);
  border-radius: 8px;
  padding: 10px 14px;
  line-height: 1.5;
}

.wizard-hint strong {
  color: var(--primary);
}
</style>
