<script setup lang="ts">
import { refreshCapabilities } from "../lib/capabilities";
import RequireCap from "../components/RequireCap.vue";
import { useAbortHandle } from "../lib/abort";

const { signal } = useAbortHandle();

async function retryCaps() {
  await refreshCapabilities(signal);
}
</script>

<template>
  <RequireCap cap="effects.read">
    <div class="page">
      <h2>Effects Trace (read-only)</h2>
      <p class="muted">Capability required: effects.read</p>
      <button class="btn secondary" @click="retryCaps">Retry</button>
    </div>
  </RequireCap>
</template>
