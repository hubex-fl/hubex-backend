<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    message: string;
    showRetry?: boolean;
  }>(),
  { showRetry: true }
);

const emit = defineEmits<{
  retry: [];
}>();
</script>

<template>
  <div class="error-box">
    <div class="error">{{ props.message }}</div>
    <button v-if="props.showRetry" class="btn" @click="emit('retry')">
      Retry
    </button>
  </div>
</template>
