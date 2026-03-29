import { ref, computed } from "vue";

const STORAGE_KEY = "hubex_action_bar";

function loadState(): Record<string, string[]> {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveState(state: Record<string, string[]>) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function useActionBar(entityId: string) {
  const state = ref<Record<string, string[]>>(loadState());

  const dismissed = computed(() => state.value[entityId] || []);
  const barHidden = computed(() => dismissed.value.includes("__bar__"));

  function dismissAction(actionId: string) {
    const current = loadState();
    current[entityId] = [...(current[entityId] || []), actionId];
    saveState(current);
    state.value = current;
  }

  function dismissBar() {
    dismissAction("__bar__");
  }

  function resetAll() {
    const current = loadState();
    delete current[entityId];
    saveState(current);
    state.value = current;
  }

  function isDismissed(actionId: string) {
    return dismissed.value.includes(actionId);
  }

  return { barHidden, isDismissed, dismissAction, dismissBar, resetAll };
}

/** Global: reset all action bar state (for Settings page) */
export function resetAllActionBars() {
  localStorage.removeItem(STORAGE_KEY);
}
