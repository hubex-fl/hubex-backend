<script setup lang="ts">
import MediaLibrary from "../components/cms/MediaLibrary.vue";
</script>

<template>
  <div class="page-wrap">
    <header class="page-head">
      <div>
        <h1 class="page-title">Media Library</h1>
        <p class="page-sub">
          Manage images, videos, audio, documents and archives used in your CMS pages.
        </p>
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
