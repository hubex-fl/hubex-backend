<script setup lang="ts">
import { useI18n } from "vue-i18n";
import MediaLibrary from "../components/cms/MediaLibrary.vue";

const { t } = useI18n();
</script>

<template>
  <div class="page-wrap">
    <header class="page-head">
      <div>
        <h1 class="page-title">{{ t('cms.media.title') }}</h1>
        <p class="page-sub">{{ t('cms.media.subtitle') }}</p>
      </div>
    </header>
    <MediaLibrary />
  </div>
</template>

<style scoped>
.page-wrap {
  padding: 24px 32px;
  max-width: 1400px;
  margin: 0 auto;
}
.page-head {
  margin-bottom: 24px;
}
.page-title {
  font-size: 28px;
  font-weight: 700;
  color: #F5F5F5;
  margin: 0 0 4px;
}
.page-sub {
  color: #A1A1AA;
  margin: 0;
  font-size: 14px;
}
</style>
