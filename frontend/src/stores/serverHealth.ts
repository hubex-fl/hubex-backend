import { defineStore } from "pinia";
import { ref } from "vue";

export const useServerHealthStore = defineStore("serverHealth", () => {
  const serverOnline = ref(true);
  const lastOfflineAt = ref<Date | null>(null);

  let _pollHandle: ReturnType<typeof setInterval> | null = null;

  function markOffline() {
    if (serverOnline.value) {
      serverOnline.value = false;
      lastOfflineAt.value = new Date();
    }
    _startPoller();
  }

  function markOnline() {
    const wasOffline = !serverOnline.value;
    serverOnline.value = true;
    _stopPoller();
    return wasOffline;
  }

  function _startPoller() {
    if (_pollHandle) return;
    _pollHandle = setInterval(_check, 5000);
  }

  function _stopPoller() {
    if (_pollHandle) {
      clearInterval(_pollHandle);
      _pollHandle = null;
    }
  }

  async function _check() {
    try {
      const ctrl = new AbortController();
      const tid = setTimeout(() => ctrl.abort(), 3000);
      const res = await fetch("/health", { signal: ctrl.signal });
      clearTimeout(tid);
      if (res.ok) markOnline();
    } catch {
      // still offline — do nothing
    }
  }

  return { serverOnline, lastOfflineAt, markOffline, markOnline };
});
