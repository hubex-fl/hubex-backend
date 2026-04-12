<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import DefaultLayout from "./layouts/DefaultLayout.vue";
import AuthLayout from "./layouts/AuthLayout.vue";
import KioskLayout from "./layouts/KioskLayout.vue";
import PublicLayout from "./layouts/PublicLayout.vue";
import ConnectPanel from "./components/ConnectPanel.vue";
import FeedbackWidget from "./components/FeedbackWidget.vue";
import CookieBanner from "./components/CookieBanner.vue";

const route = useRoute();
// Embed: render without any wrapper (no header/footer). Public: use PublicLayout.
const isBare = computed(() => route.meta?.layout === "embed");
const isPublic = computed(() => route.meta?.layout === "public");
// CMS public pages use the PublicLayout; the landing page opts out via meta.noPublicShell
const isPublicCms = computed(() => isPublic.value && !route.meta?.noPublicShell);
const layout = computed(() => {
  if (route.meta?.layout === "auth") return AuthLayout;
  if (route.meta?.layout === "kiosk") return KioskLayout;
  return DefaultLayout;
});
</script>

<template>
  <!-- Embedded pages (iframe targets): no shell at all -->
  <router-view v-if="isBare" />
  <!-- CMS public pages: render inside PublicLayout (header + footer menus) -->
  <PublicLayout v-else-if="isPublicCms">
    <router-view />
  </PublicLayout>
  <!-- Landing and other public pages without shell -->
  <router-view v-else-if="isPublic" />
  <component v-else :is="layout">
    <router-view />
  </component>
  <!-- Global Connect Panel (slide-over) — mounted once at root -->
  <ConnectPanel />
  <!-- Feedback Widget (bottom-right) -->
  <FeedbackWidget />
  <!-- Cookie Banner (shown once, until accepted) -->
  <CookieBanner />
</template>
