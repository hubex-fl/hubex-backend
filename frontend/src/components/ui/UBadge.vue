<script setup lang="ts">
type Status = "ok" | "warn" | "bad" | "info" | "neutral";

const props = withDefaults(
  defineProps<{
    status?: Status;
    pulse?: boolean;
    label?: string;
  }>(),
  { status: "neutral", pulse: false }
);

const colorMap: Record<Status, string> = {
  ok:      "bg-[var(--status-ok-bg)] text-[var(--status-ok)] border-[var(--status-ok)]/30",
  warn:    "bg-[var(--status-warn-bg)] text-[var(--status-warn)] border-[var(--status-warn)]/30",
  bad:     "bg-[var(--status-bad-bg)] text-[var(--status-bad)] border-[var(--status-bad)]/30",
  info:    "bg-[var(--status-info-bg)] text-[var(--status-info)] border-[var(--status-info)]/30",
  neutral: "bg-[var(--bg-raised)] text-[var(--text-muted)] border-[var(--border)]",
};

const dotMap: Record<Status, string> = {
  ok:      "bg-[var(--status-ok)]",
  warn:    "bg-[var(--status-warn)]",
  bad:     "bg-[var(--status-bad)]",
  info:    "bg-[var(--status-info)]",
  neutral: "bg-[var(--text-muted)]",
};
</script>

<template>
  <span
    :class="[
      'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold border',
      colorMap[status],
    ]"
  >
    <span
      v-if="pulse"
      :class="['h-1.5 w-1.5 rounded-full', dotMap[status], pulse && 'animate-pulse-slow']"
    />
    <slot>{{ label }}</slot>
  </span>
</template>
