<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useRoute } from "vue-router";
import { apiFetch } from "../lib/api";
import BlockRenderer from "../components/cms/BlockRenderer.vue";

const route = useRoute();

type SiteSettingsPublic = {
  site_title: string;
  site_tagline: string | null;
  logo_url: string | null;
  favicon_url: string | null;
  primary_color: string;
  accent_color: string;
  bg_color: string;
  text_color: string;
  default_meta_title: string | null;
  default_meta_description: string | null;
  default_og_image: string | null;
  twitter_handle: string | null;
  footer_text: string | null;
  footer_links: { text: string; url: string }[] | null;
  custom_css: string | null;
  custom_head_html: string | null;
  custom_footer_html: string | null;
  google_analytics_id: string | null;
  plausible_domain: string | null;
};

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

type MenuItem = {
  id?: string;
  type: "page" | "link" | "section" | "divider";
  label?: string;
  url?: string;
  slug?: string;
  page_id?: number;
  target?: string;
  children?: MenuItem[];
};

type PublicMenu = {
  name: string;
  location: string;
  items: MenuItem[] | null;
};

const loading = ref(true);
const error = ref<string | null>(null);
const page = ref<CmsPagePublic | null>(null);
const headerMenu = ref<PublicMenu | null>(null);
const settings = ref<SiteSettingsPublic | null>(null);

// Track injected DOM elements for cleanup on unmount
const injectedTags: HTMLElement[] = [];

// PIN handling
const needsPin = ref(false);
const enteredPin = ref("");

const slug = computed(() => String(route.params.slug || ""));
const layoutClass = computed(() => `cms-layout-${page.value?.layout || 'default'}`);
const headerItems = computed<MenuItem[]>(() => headerMenu.value?.items || []);
const showMenu = computed(
  () => headerItems.value.length > 0 && page.value?.layout !== "fullscreen"
);

async function loadHeaderMenu() {
  try {
    const res = await fetch("/api/v1/cms/menus/location/header");
    if (res.ok) {
      headerMenu.value = await res.json();
    }
  } catch {
    // silent — menu is optional
  }
}

async function loadSiteSettings() {
  try {
    const res = await fetch("/api/v1/site/settings/public");
    if (res.ok) {
      settings.value = await res.json();
    }
  } catch {
    // silent — settings are optional
  }
}

function hrefFor(item: MenuItem): string {
  if (item.type === "page") return item.slug ? `/p/${item.slug}` : "#";
  if (item.type === "link") return item.url || "#";
  return "#";
}

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
    if (page.value) applySeoTags();
  } catch (e: any) {
    error.value = e.message || "Failed to load";
  } finally {
    loading.value = false;
  }
}

function applySeoTags() {
  if (!page.value) return;
  const p = page.value;
  const s = settings.value;
  const pageUrl = `${window.location.origin}/p/${p.slug}`;

  // <title>
  const siteTitle = s?.site_title || "";
  const baseTitle = p.meta_title || p.title;
  document.title = siteTitle ? `${baseTitle} — ${siteTitle}` : baseTitle;

  // meta description
  const desc = p.meta_description || s?.default_meta_description || p.description || "";
  if (desc) setMetaTag("description", desc);

  // Open Graph
  setMetaTag("og:title", baseTitle, true);
  if (desc) setMetaTag("og:description", desc, true);
  setMetaTag("og:url", pageUrl, true);
  setMetaTag("og:type", "website", true);
  const ogImg = p.og_image || s?.default_og_image || "";
  if (ogImg) setMetaTag("og:image", ogImg, true);
  if (s?.site_title) setMetaTag("og:site_name", s.site_title, true);

  // Twitter Card
  setMetaTag("twitter:card", "summary_large_image");
  setMetaTag("twitter:title", baseTitle);
  if (desc) setMetaTag("twitter:description", desc);
  if (ogImg) setMetaTag("twitter:image", ogImg);
  if (s?.twitter_handle) setMetaTag("twitter:site", s.twitter_handle);

  // Favicon
  if (s?.favicon_url) setLinkTag("icon", s.favicon_url);

  // JSON-LD structured data (schema.org WebPage)
  setJsonLd({
    "@context": "https://schema.org",
    "@type": "WebPage",
    "name": baseTitle,
    "description": desc,
    "url": pageUrl,
    ...(ogImg ? { image: ogImg } : {}),
    ...(p.published_at ? { datePublished: p.published_at } : {}),
  });

  // Custom CSS / analytics — from site settings
  if (s?.custom_css) injectStyle(s.custom_css);
  if (s?.google_analytics_id) injectGA(s.google_analytics_id);
  if (s?.plausible_domain) injectPlausible(s.plausible_domain);
}

function setMetaTag(name: string, content: string, isProperty = false) {
  const attr = isProperty ? "property" : "name";
  let el = document.querySelector(`meta[${attr}="${name}"]`) as HTMLMetaElement | null;
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, name);
    document.head.appendChild(el);
    injectedTags.push(el);
  }
  el.content = content;
}

function setLinkTag(rel: string, href: string) {
  let el = document.querySelector(`link[rel="${rel}"]`) as HTMLLinkElement | null;
  if (!el) {
    el = document.createElement("link");
    el.setAttribute("rel", rel);
    document.head.appendChild(el);
    injectedTags.push(el);
  }
  el.href = href;
}

function setJsonLd(data: Record<string, any>) {
  let el = document.getElementById("cms-jsonld") as HTMLScriptElement | null;
  if (!el) {
    el = document.createElement("script");
    el.id = "cms-jsonld";
    el.type = "application/ld+json";
    document.head.appendChild(el);
    injectedTags.push(el);
  }
  el.textContent = JSON.stringify(data);
}

function injectStyle(css: string) {
  let el = document.getElementById("cms-custom-css") as HTMLStyleElement | null;
  if (!el) {
    el = document.createElement("style");
    el.id = "cms-custom-css";
    document.head.appendChild(el);
    injectedTags.push(el);
  }
  el.textContent = css;
}

function injectGA(gaId: string) {
  if (document.getElementById("cms-ga-script")) return;
  const s1 = document.createElement("script");
  s1.id = "cms-ga-script";
  s1.async = true;
  s1.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(gaId)}`;
  document.head.appendChild(s1);
  injectedTags.push(s1);

  const s2 = document.createElement("script");
  s2.id = "cms-ga-init";
  s2.textContent = `window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','${gaId}');`;
  document.head.appendChild(s2);
  injectedTags.push(s2);
}

function injectPlausible(domain: string) {
  if (document.getElementById("cms-plausible")) return;
  const s = document.createElement("script");
  s.id = "cms-plausible";
  s.defer = true;
  s.setAttribute("data-domain", domain);
  s.src = "https://plausible.io/js/script.js";
  document.head.appendChild(s);
  injectedTags.push(s);
}

function submitPin() {
  if (enteredPin.value.trim()) {
    loadPage(enteredPin.value.trim());
  }
}

onMounted(async () => {
  await loadSiteSettings();
  await Promise.all([loadPage(), loadHeaderMenu()]);
});
onUnmounted(() => {
  for (const el of injectedTags) {
    try { el.remove(); } catch { /* ignore */ }
  }
});
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
    <nav v-if="showMenu" class="cms-nav">
      <div class="cms-nav-inner">
        <template v-for="(item, i) in headerItems" :key="item.id || i">
          <span v-if="item.type === 'divider'" class="cms-nav-divider" aria-hidden="true">·</span>
          <span v-else-if="item.type === 'section'" class="cms-nav-section">
            {{ item.label }}
          </span>
          <a
            v-else
            class="cms-nav-link"
            :href="hrefFor(item)"
            :target="item.target || undefined"
            :rel="item.target === '_blank' ? 'noopener' : undefined"
          >
            {{ item.label }}
          </a>
        </template>
      </div>
    </nav>
    <BlockRenderer
      class="cms-content"
      mode="hydrate"
      :html="page.content_html"
    />
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
.cms-nav {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(17, 17, 16, 0.92);
  border-bottom: 1px solid rgba(255,255,255,0.08);
  backdrop-filter: blur(8px);
}
.cms-nav-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 14px 24px;
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
}
.cms-nav-link {
  color: #A1A1AA;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: color 0.15s;
}
.cms-nav-link:hover {
  color: #F5A623;
}
.cms-nav-divider {
  color: rgba(255,255,255,0.15);
  user-select: none;
}
.cms-nav-section {
  color: #F5F5F5;
  font-weight: 600;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
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
