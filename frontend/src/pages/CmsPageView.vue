<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import { apiFetch } from "../lib/api";

const route = useRoute();

type CmsPagePublic = {
  slug: string;
  title: string;
  description: string | null;
  content_html: string;
  content_mode: string;
  layout: string;
  meta_title: string | null;
  meta_description: string | null;
  og_image: string | null;
  published_at: string | null;
};

const loading = ref(true);
const error = ref<string | null>(null);
const page = ref<CmsPagePublic | null>(null);

// PIN handling
const needsPin = ref(false);
const enteredPin = ref("");

const slug = computed(() => String(route.params.slug || ""));
const layoutClass = computed(() => `cms-layout-${page.value?.layout || 'default'}`);

async function loadPage(pinOverride?: string) {
  loading.value = true;
  error.value = null;
  needsPin.value = false;
  try {
    const url = pinOverride
      ? `/api/v1/cms/pages/slug/${encodeURIComponent(slug.value)}?pin=${encodeURIComponent(pinOverride)}`
      : `/api/v1/cms/pages/slug/${encodeURIComponent(slug.value)}`;
    const res = await fetch(url);
    if (res.status === 403) {
      needsPin.value = true;
      loading.value = false;
      return;
    }
    if (!res.ok) {
      error.value = `${res.status} ${res.statusText}`;
      loading.value = false;
      return;
    }
    page.value = await res.json();
    // Set page title + meta from page data
    if (page.value) {
      document.title = page.value.meta_title || page.value.title;
      if (page.value.meta_description) {
        setMetaTag("description", page.value.meta_description);
      }
      if (page.value.og_image) {
        setMetaTag("og:image", page.value.og_image, true);
      }
    }
  } catch (e: any) {
    error.value = e.message || "Failed to load";
  } finally {
    loading.value = false;
  }
}

function setMetaTag(name: string, content: string, isProperty = false) {
  const attr = isProperty ? "property" : "name";
  let el = document.querySelector(`meta[${attr}="${name}"]`) as HTMLMetaElement | null;
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, name);
    document.head.appendChild(el);
  }
  el.content = content;
}

function submitPin() {
  if (enteredPin.value.trim()) {
    loadPage(enteredPin.value.trim());
  }
}

onMounted(() => loadPage());
watch(() => route.params.slug, () => loadPage());
</script>

<template>
  <div v-if="loading" class="state">Loading…</div>

  <div v-else-if="needsPin" class="pin-wrap">
    <div class="pin-card">
      <h2>Protected Page</h2>
      <p>This page requires a PIN to view.</p>
      <input
        v-model="enteredPin"
        type="password"
        placeholder="PIN"
        @keyup.enter="submitPin"
        autofocus
      />
      <button @click="submitPin" class="pin-btn">Unlock</button>
    </div>
  </div>

  <div v-else-if="error" class="state error">{{ error }}</div>

  <article v-else-if="page" class="cms-page" :class="layoutClass">
    <div class="cms-content" v-html="page.content_html"></div>
  </article>
</template>

<style scoped>
.state {
  padding: 80px 24px;
  text-align: center;
  color: #71717A;
  background: #111110;
  min-height: 100vh;
}
.state.error { color: #ef4444; }

.cms-page {
  background: #111110;
  color: #E5E5E5;
  min-height: 100vh;
}
/* Default: centered article max-width */
.cms-layout-default .cms-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 64px 24px;
  line-height: 1.7;
  font-size: 17px;
}
/* Landing: full width, no padding */
.cms-layout-landing .cms-content,
.cms-layout-fullscreen .cms-content {
  max-width: 100%;
  padding: 0;
  margin: 0;
}
/* Minimal: narrow, lots of whitespace */
.cms-layout-minimal .cms-content {
  max-width: 640px;
  margin: 0 auto;
  padding: 96px 24px;
  line-height: 1.8;
}

.cms-content :deep(h1) {
  font-size: 36px;
  font-weight: 700;
  color: #F5F5F5;
  margin: 0 0 20px;
}
.cms-content :deep(h2) {
  font-size: 26px;
  color: #F5F5F5;
  margin: 32px 0 16px;
}
.cms-content :deep(h3) {
  font-size: 20px;
  color: #F5F5F5;
  margin: 24px 0 12px;
}
.cms-content :deep(p) {
  color: #A1A1AA;
  margin: 0 0 16px;
}
.cms-content :deep(a) {
  color: #2DD4BF;
  text-decoration: none;
}
.cms-content :deep(a:hover) { text-decoration: underline; }
.cms-content :deep(code) {
  background: rgba(255,255,255,0.06);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.9em;
}
.cms-content :deep(pre) {
  background: rgba(0,0,0,0.4);
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  border: 1px solid rgba(255,255,255,0.06);
}
.cms-content :deep(ul), .cms-content :deep(ol) {
  color: #A1A1AA;
  padding-left: 24px;
}
.cms-content :deep(img) { max-width: 100%; border-radius: 8px; }

.pin-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #111110;
}
.pin-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px;
  padding: 32px;
  max-width: 360px;
  width: 100%;
  text-align: center;
}
.pin-card h2 { color: #F5F5F5; margin: 0 0 8px; }
.pin-card p { color: #A1A1AA; margin: 0 0 20px; }
.pin-card input {
  width: 100%;
  background: #0c0c0b;
  border: 1px solid rgba(255,255,255,0.1);
  color: #F5F5F5;
  padding: 12px 14px;
  border-radius: 8px;
  font-size: 16px;
  margin-bottom: 12px;
}
.pin-card input:focus { outline: none; border-color: #F5A623; }
.pin-btn {
  width: 100%;
  background: #F5A623;
  color: #111110;
  border: none;
  padding: 12px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
}
</style>
