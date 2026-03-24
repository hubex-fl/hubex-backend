<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    name?: string;
    src?: string;
    size?: "xs" | "sm" | "md" | "lg";
    status?: "online" | "offline" | "away";
  }>(),
  { size: "md" }
);

const initials = computed(() => {
  if (!props.name) return "?";
  return props.name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
});

function colorFromName(name: string): string {
  const palette = [
    "bg-[#00d4ff]/20 text-[#00d4ff]",
    "bg-[#7b61ff]/20 text-[#7b61ff]",
    "bg-[#00e5a0]/20 text-[#00e5a0]",
    "bg-[#ff6b6b]/20 text-[#ff6b6b]",
    "bg-[#ffd93d]/20 text-[#ffd93d]",
  ];
  let hash = 0;
  for (const c of name) hash = (hash << 5) - hash + c.charCodeAt(0);
  return palette[Math.abs(hash) % palette.length];
}

const sizeClasses: Record<string, string> = {
  xs: "h-6 w-6 text-[10px]",
  sm: "h-8 w-8 text-xs",
  md: "h-9 w-9 text-sm",
  lg: "h-12 w-12 text-base",
};

const dotSizes: Record<string, string> = {
  xs: "h-1.5 w-1.5",
  sm: "h-2 w-2",
  md: "h-2.5 w-2.5",
  lg: "h-3 w-3",
};

const statusColor: Record<string, string> = {
  online:  "bg-[var(--status-ok)]",
  offline: "bg-[var(--text-muted)]",
  away:    "bg-[var(--status-warn)]",
};
</script>

<template>
  <span class="relative inline-flex shrink-0">
    <img
      v-if="src"
      :src="src"
      :alt="name"
      :class="['rounded-full object-cover', sizeClasses[size]]"
    />
    <span
      v-else
      :class="[
        'inline-flex items-center justify-center rounded-full font-semibold',
        sizeClasses[size],
        name ? colorFromName(name) : 'bg-[var(--bg-raised)] text-[var(--text-muted)]',
      ]"
    >
      {{ initials }}
    </span>
    <span
      v-if="status"
      :class="[
        'absolute bottom-0 right-0 block rounded-full ring-2 ring-[var(--bg-base)]',
        dotSizes[size],
        statusColor[status],
      ]"
    />
  </span>
</template>
