<script setup lang="ts">
import { ref, onMounted } from "vue";

type MenuItem = {
  label: string;
  url?: string;
  page_slug?: string | null;
  page_id?: number | null;
  target?: string | null;
  children?: MenuItem[];
};

type PublicMenu = {
  name: string;
  location: string;
  items: MenuItem[];
};

type PublicSettings = {
  site_title: string;
  site_tagline: string | null;
  logo_url: string | null;
  favicon_url: string | null;
  primary_color: string;
  accent_color: string;
  bg_color: string;
  text_color: string;
  footer_text: string | null;
  footer_links: any[] | null;
  custom_css: string | null;
  custom_head_html: string | null;
  custom_footer_html: string | null;
};

const settings = ref<PublicSettings | null>(null);
const headerMenu = ref<PublicMenu | null>(null);
const footerMenu = ref<PublicMenu | null>(null);

async function safeFetch<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

function hrefForItem(item: MenuItem): string {
  if (item.url) return item.url;
  if (item.page_slug) return `/p/${item.page_slug}`;
  return "#";
}

onMounted(async () => {
  // Load site settings, header + footer menus in parallel (all public endpoints)
  const [s, h, f] = await Promise.all([
    safeFetch<PublicSettings>("/api/v1/site/settings/public"),
    safeFetch<PublicMenu>("/api/v1/cms/menus/location/header"),
    safeFetch<PublicMenu>("/api/v1/cms/menus/location/footer"),
  ]);
  settings.value = s;
  headerMenu.value = h;
  footerMenu.value = f;

  if (s?.favicon_url) {
    let link = document.querySelector<HTMLLinkElement>("link[rel~='icon']");
    if (!link) {
      link = document.createElement("link");
      link.rel = "icon";
      document.head.appendChild(link);
    }
    link.href = s.favicon_url;
  }
});
</script>

<template>
  <div class="public-shell"
       :style="{
         '--p-bg': settings?.bg_color || '#111110',
         '--p-text': settings?.text_color || '#E5E5E5',
         '--p-primary': settings?.primary_color || '#F5A623',
         '--p-accent': settings?.accent_color || '#2DD4BF',
       }">
    <!-- Header -->
    <header class="public-header">
      <div class="public-header-inner">
        <router-link to="/" class="public-brand">
          <img v-if="settings?.logo_url" :src="settings.logo_url" :alt="settings?.site_title || 'Logo'" class="public-logo" />
          <span v-else class="public-brand-text">{{ settings?.site_title || "HUBEX" }}</span>
        </router-link>
        <nav class="public-nav" v-if="headerMenu && headerMenu.items?.length">
          <a
            v-for="(item, idx) in headerMenu.items"
            :key="idx"
            :href="hrefForItem(item)"
            :target="item.target || undefined"
            class="public-nav-link"
          >{{ item.label }}</a>
        </nav>
      </div>
    </header>

    <!-- Content slot -->
    <main class="public-main">
      <slot />
    </main>

    <!-- Footer -->
    <footer class="public-footer">
      <div class="public-footer-inner">
        <div v-if="settings?.footer_text" class="public-footer-text">
          {{ settings.footer_text }}
        </div>
        <nav v-if="footerMenu && footerMenu.items?.length" class="public-footer-nav">
          <a
            v-for="(item, idx) in footerMenu.items"
            :key="idx"
            :href="hrefForItem(item)"
            :target="item.target || undefined"
            class="public-footer-link"
          >{{ item.label }}</a>
        </nav>
        <div class="public-footer-copy">
          © {{ new Date().getFullYear() }} {{ settings?.site_title || "HUBEX" }}
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.public-shell {
  min-height: 100vh;
  background: var(--p-bg);
  color: var(--p-text);
  display: flex;
  flex-direction: column;
}
.public-header {
  position: sticky;
  top: 0;
  z-index: 20;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.public-header-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 14px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}
.public-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: inherit;
}
.public-logo {
  max-height: 32px;
  max-width: 180px;
  object-fit: contain;
}
.public-brand-text {
  font-family: "IBM Plex Mono", monospace;
  font-weight: 700;
  font-size: 18px;
  letter-spacing: 0.1em;
}
.public-nav {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}
.public-nav-link {
  color: var(--p-text);
  opacity: 0.8;
  text-decoration: none;
  font-size: 14px;
  transition: opacity 0.15s, color 0.15s;
}
.public-nav-link:hover {
  opacity: 1;
  color: var(--p-primary);
}
.public-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.public-footer {
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.3);
  padding: 32px 0 24px;
  margin-top: auto;
}
.public-footer-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  align-items: center;
  text-align: center;
}
.public-footer-text {
  color: var(--p-text);
  opacity: 0.7;
  font-size: 13px;
}
.public-footer-nav {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  justify-content: center;
}
.public-footer-link {
  color: var(--p-text);
  opacity: 0.6;
  text-decoration: none;
  font-size: 13px;
  transition: opacity 0.15s;
}
.public-footer-link:hover { opacity: 1; }
.public-footer-copy {
  color: var(--p-text);
  opacity: 0.4;
  font-size: 12px;
}
</style>
