<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useServerHealthStore } from "../../stores/serverHealth";

const sh = useServerHealthStore();

const elapsed = ref(0);
let _ticker: ReturnType<typeof setInterval> | null = null;

function startTicker() {
  elapsed.value = 0;
  _ticker = setInterval(() => { elapsed.value++; }, 1000);
}

function stopTicker() {
  if (_ticker) { clearInterval(_ticker); _ticker = null; }
}

function elapsedText(): string {
  if (elapsed.value < 60) return `${elapsed.value}s`;
  return `${Math.floor(elapsed.value / 60)}m`;
}

// Watch serverOnline imperatively to start/stop ticker
import { watch } from "vue";
watch(() => sh.serverOnline, (online) => {
  if (!online) startTicker();
  else stopTicker();
}, { immediate: true });

onUnmounted(stopTicker);
</script>

<template>
  <Transition name="offline-banner">
    <div
      v-if="!sh.serverOnline"
      class="fixed top-0 inset-x-0 z-[200] flex items-center justify-center gap-3 px-4 py-2.5 bg-amber-900/90 backdrop-blur-sm text-amber-200 text-sm shadow-lg"
      role="alert"
    >
      <!-- Wifi-off icon -->
      <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M3 3l18 18M8.457 8.457A7.5 7.5 0 0021 12M16.72 16.72A7.5 7.5 0 013 12M12 19.5h.008v.008H12V19.5z" />
      </svg>
      <span class="font-medium">Server unreachable</span>
      <span class="text-amber-300/80">—</span>
      <!-- Spinning reconnect indicator -->
      <svg class="h-3.5 w-3.5 shrink-0 animate-spin text-amber-300" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
      <span class="text-amber-300/80">Retrying…</span>
      <span v-if="elapsed > 0" class="font-mono text-amber-400 text-xs">{{ elapsedText() }}</span>
    </div>
  </Transition>
</template>

<style scoped>
.offline-banner-enter-active,
.offline-banner-leave-active { transition: transform 0.25s ease, opacity 0.25s ease; }
.offline-banner-enter-from,
.offline-banner-leave-to    { transform: translateY(-100%); opacity: 0; }
</style>
