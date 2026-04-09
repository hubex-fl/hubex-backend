<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useI18n } from "vue-i18n";
import { useAiCommands, type AiAction } from "../composables/useAiCommands";

const { t } = useI18n();
const { recentActions, lastCommandTs } = useAiCommands();
const expanded = ref(false);

// Show the indicator when a command was received in the last 10 seconds
const ACTIVE_WINDOW_MS = 10_000;
let _tick: ReturnType<typeof setInterval> | null = null;
const now = ref(Date.now());

onMounted(() => {
  _tick = setInterval(() => {
    now.value = Date.now();
  }, 1000);
});

onUnmounted(() => {
  if (_tick) clearInterval(_tick);
});

const isActive = computed(() => {
  if (lastCommandTs.value === 0) return false;
  return now.value - lastCommandTs.value < ACTIVE_WINDOW_MS;
});

const hasHistory = computed(() => recentActions.value.length > 0);

function toggle() {
  expanded.value = !expanded.value;
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

const commandLabels: Record<string, string> = {
  navigate: "Navigate",
  start_tour: "Tour",
  highlight: "Highlight",
  fly_to_node: "Fly to",
  notification: "Notify",
  refresh: "Refresh",
};
</script>

<template>
  <Teleport to="body">
    <Transition name="ai-coop">
      <div
        v-if="isActive || expanded"
        class="fixed bottom-4 left-4 z-[9990] select-none"
      >
        <!-- Badge -->
        <button
          class="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium
                 bg-[#1c1c1a]/90 border border-[#333] text-[#e5e5e3]
                 hover:border-amber-500/50 transition-colors backdrop-blur-sm shadow-lg"
          @click="toggle"
          :title="t('aiCoop.title')"
        >
          <!-- Pulsing dot -->
          <span class="relative flex h-2 w-2">
            <span
              v-if="isActive"
              class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"
            />
            <span
              :class="[
                'relative inline-flex rounded-full h-2 w-2',
                isActive ? 'bg-amber-400' : 'bg-gray-500',
              ]"
            />
          </span>
          <span>{{ t('aiCoop.badge') }}</span>
          <!-- Chevron -->
          <svg
            :class="['h-3 w-3 transition-transform', expanded ? 'rotate-180' : '']"
            fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 15.75l7.5-7.5 7.5 7.5" />
          </svg>
        </button>

        <!-- Expanded log panel -->
        <Transition name="panel-slide">
          <div
            v-if="expanded && hasHistory"
            class="absolute bottom-10 left-0 w-72 max-h-64 overflow-y-auto rounded-lg
                   bg-[#1c1c1a]/95 border border-[#333] backdrop-blur-sm shadow-xl"
          >
            <div class="px-3 py-2 border-b border-[#333] text-xs font-semibold text-[#999]">
              {{ t('aiCoop.logTitle') }}
            </div>
            <ul class="divide-y divide-[#222]">
              <li
                v-for="action in recentActions"
                :key="action.id"
                class="px-3 py-2 text-xs"
              >
                <div class="flex items-center justify-between">
                  <span class="inline-flex items-center gap-1.5">
                    <span class="px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 font-mono text-[10px]">
                      {{ commandLabels[action.command] || action.command }}
                    </span>
                    <span class="text-[#999] truncate max-w-[140px]">{{ action.summary }}</span>
                  </span>
                  <span class="text-[#666] text-[10px] font-mono shrink-0 ml-2">
                    {{ formatTime(action.ts) }}
                  </span>
                </div>
              </li>
            </ul>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.ai-coop-enter-active,
.ai-coop-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.ai-coop-enter-from,
.ai-coop-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

.panel-slide-enter-active,
.panel-slide-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.panel-slide-enter-from,
.panel-slide-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
