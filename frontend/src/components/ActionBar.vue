<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useActionBar } from "../composables/useActionBar";

const props = defineProps<{
  deviceId: number | string;
  deviceUid?: string;
  hasVariables?: boolean;
  hasAlerts?: boolean;
  hasAutomations?: boolean;
  hasName?: boolean;
}>();

const router = useRouter();
const { t } = useI18n();
const { barHidden, isDismissed, dismissAction, dismissBar } = useActionBar(
  String(props.deviceId)
);

interface Action {
  id: string;
  label: string;
  description: string;
  icon: string;
  iconColor: string;
  done: boolean;
  onClick: () => void;
}

// Sprint 3.5 bugfix: labels + descriptions were hardcoded English. This
// was the biggest offender in the "english-in-german-locale" bug — the
// Suggested Next Steps panel is shown on every DeviceDetail page, so
// every new user saw English right after clicking their first device.
const actions = computed((): Action[] => {
  const list: Action[] = [];

  if (!isDismissed("name") && !props.hasName) {
    list.push({
      id: "name",
      label: t("actionBar.nameLabel"),
      description: t("actionBar.nameDesc"),
      icon: "M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10",
      iconColor: "var(--text-muted)",
      done: false,
      onClick: () => router.push({ hash: "#identity" }),
    });
  }

  if (!isDismissed("variables") && !props.hasVariables) {
    list.push({
      id: "variables",
      label: t("actionBar.variablesLabel"),
      description: t("actionBar.variablesDesc"),
      icon: "M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h1.5C5.496 19.5 6 18.996 6 18.375m-3.75.125v-1.5m0 0A1.125 1.125 0 013.375 16.5h1.5m0 0h9",
      iconColor: "var(--accent)",
      done: false,
      onClick: () => {
        dismissAction("variables");
        router.push({ path: "/variables", query: props.deviceUid ? { device: props.deviceUid } : undefined });
      },
    });
  }

  if (!isDismissed("alerts") && !props.hasAlerts) {
    list.push({
      id: "alerts",
      label: t("actionBar.alertsLabel"),
      description: t("actionBar.alertsDesc"),
      icon: "M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0",
      iconColor: "var(--status-warn)",
      done: false,
      onClick: () => {
        dismissAction("alerts");
        router.push({ path: "/alerts", query: { create: "true", ...(props.deviceUid ? { device_uid: props.deviceUid } : {}) } });
      },
    });
  }

  if (!isDismissed("automations") && !props.hasAutomations) {
    list.push({
      id: "automations",
      label: t("actionBar.automationsLabel"),
      description: t("actionBar.automationsDesc"),
      icon: "M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z",
      iconColor: "var(--primary)",
      done: false,
      onClick: () => {
        dismissAction("automations");
        router.push({ path: "/automations", query: { create: "true", ...(props.deviceUid ? { device_uid: props.deviceUid } : {}) } });
      },
    });
  }

  return list;
});

const visible = computed(() => !barHidden.value && actions.value.length > 0);
</script>

<template>
  <div v-if="visible" class="action-bar">
    <div class="action-bar-header">
      <svg class="h-3.5 w-3.5 text-[var(--primary)]" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
      </svg>
      <span>{{ t("actionBar.title") }}</span>
      <button class="action-bar-dismiss" @click="dismissBar" :title="t('actionBar.dismiss')">
        <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="action-bar-items">
      <button
        v-for="action in actions"
        :key="action.id"
        class="action-bar-item"
        @click="action.onClick"
      >
        <div class="action-icon" :style="{ color: action.iconColor }">
          <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" :d="action.icon" />
          </svg>
        </div>
        <div class="action-text">
          <span class="action-label">{{ action.label }}</span>
          <span class="action-desc">{{ action.description }}</span>
        </div>
        <svg class="h-3.5 w-3.5 text-[var(--text-muted)] shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.action-bar {
  border-radius: var(--radius-lg);
  border: 1px solid color-mix(in srgb, var(--primary) 20%, transparent);
  background: color-mix(in srgb, var(--primary) 5%, var(--bg-surface));
  overflow: hidden;
}

.action-bar-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-bottom: 1px solid color-mix(in srgb, var(--primary) 15%, transparent);
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.action-bar-dismiss {
  margin-left: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: var(--radius-sm);
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  transition: background 0.15s, color 0.15s;
}

.action-bar-dismiss:hover {
  background: var(--bg-raised);
  color: var(--text-primary);
}

.action-bar-items {
  display: flex;
  flex-wrap: wrap;
  gap: 1px;
  padding: 6px;
}

.action-bar-item {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 200px;
  padding: 8px 10px;
  border-radius: var(--radius-md);
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s;
}

.action-bar-item:hover {
  background: color-mix(in srgb, var(--primary) 8%, transparent);
}

.action-icon {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-md);
  background: var(--bg-raised);
  display: flex;
  align-items: center;
  justify-content: center;
  shrink: 0;
  flex-shrink: 0;
}

.action-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.action-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-primary);
  line-height: 1.3;
}

.action-desc {
  font-size: 0.6875rem;
  color: var(--text-muted);
  line-height: 1.3;
}
</style>
