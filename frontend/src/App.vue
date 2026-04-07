<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import DefaultLayout from "./layouts/DefaultLayout.vue";
import AuthLayout from "./layouts/AuthLayout.vue";
import KioskLayout from "./layouts/KioskLayout.vue";
import ConnectPanel from "./components/ConnectPanel.vue";
import FeedbackWidget from "./components/FeedbackWidget.vue";

const route = useRoute();
const isPublic = computed(() => route.meta?.layout === "public");
const layout = computed(() => {
  if (route.meta?.layout === "auth") return AuthLayout;
  if (route.meta?.layout === "kiosk") return KioskLayout;
  return DefaultLayout;
});
</script>

<template>
  <!-- Public pages (landing) render without any layout wrapper -->
  <router-view v-if="isPublic" />
  <component v-else :is="layout">
    <router-view />
  </component>
  <!-- Global Connect Panel (slide-over) — mounted once at root -->
  <ConnectPanel />
  <!-- Feedback Widget (bottom-right) -->
  <FeedbackWidget />
</template>
