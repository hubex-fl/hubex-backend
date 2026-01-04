<script setup lang="ts">
type GateStatus = "loading" | "error" | "unavailable" | "idle" | "ready";

const props = defineProps<{
  status: GateStatus;
  message?: string;
}>();

const defaultMessage =
  props.status === "loading"
    ? "Capabilities loading."
    : props.status === "error"
      ? "Capabilities error."
      : "Capabilities unavailable.";
</script>

<template>
  <div class="error">
    {{ props.message ?? defaultMessage }}
  </div>
</template>
