<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import DefaultLayout from "./layouts/DefaultLayout.vue";
import AuthLayout from "./layouts/AuthLayout.vue";

const route = useRoute();
const isPublic = computed(() => route.meta?.layout === "public");
const layout = computed(() => {
  if (route.meta?.layout === "auth") return AuthLayout;
  return DefaultLayout;
});
</script>

<template>
  <!-- Public pages (landing) render without any layout wrapper -->
  <router-view v-if="isPublic" />
  <component v-else :is="layout">
    <router-view />
  </component>
</template>
