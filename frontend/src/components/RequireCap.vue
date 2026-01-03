<script setup lang="ts">
import { computed } from "vue";
import { hasCap, useCapabilities } from "../lib/capabilities";

const props = defineProps<{ cap: string }>();
const caps = useCapabilities();

const allowed = computed(() => hasCap(props.cap));
const status = computed(() => caps.status);
</script>

<template>
  <div v-if="allowed">
    <slot />
  </div>
  <div v-else class="no-access">
    <div>No access</div>
    <div class="no-access-sub">{{ status }}</div>
  </div>
</template>
