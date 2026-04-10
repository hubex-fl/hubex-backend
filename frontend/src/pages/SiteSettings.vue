<script setup lang="ts">
import { ref, onMounted } from "vue";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";

const toast = useToastStore();

type Settings = {
  id: number;
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

  google_analytics_id: string | null;
  plausible_domain: string | null;

  footer_text: string | null;
  footer_links: { text: string; url: string }[] | null;

  custom_css: string | null;
  custom_head_html: string | null;
  custom_footer_html: string | null;
};

const settings = ref<Settings | null>(null);
const loading = ref(true);
const saving = ref(false);

// Accordion sections
const openSections = ref({
  branding: true,
  seo: false,
  analytics: false,
  footer: false,
  advanced: false,
});

function toggle(key: keyof typeof openSections.value) {
  openSections.value[key] = !openSections.value[key];
}

async function loadSettings() {
  loading.value = true;
  try {
    settings.value = await apiFetch<Settings>("/api/v1/site/settings");
    if (!settings.value.footer_links) settings.value.footer_links = [];
  } catch (e: any) {
    toast.show(e.message || "Failed to load settings", "error");
  } finally {
    loading.value = false;
  }
}

async function saveSettings() {
  if (!settings.value) return;
  saving.value = true;
  try {
    const body = {
      site_title: settings.value.site_title,
      site_tagline: settings.value.site_tagline,
      logo_url: settings.value.logo_url,
      favicon_url: settings.value.favicon_url,
      primary_color: settings.value.primary_color,
      accent_color: settings.value.accent_color,
      bg_color: settings.value.bg_color,
      text_color: settings.value.text_color,
      default_meta_title: settings.value.default_meta_title,
      default_meta_description: settings.value.default_meta_description,
      default_og_image: settings.value.default_og_image,
      twitter_handle: settings.value.twitter_handle,
      google_analytics_id: settings.value.google_analytics_id,
      plausible_domain: settings.value.plausible_domain,
      footer_text: settings.value.footer_text,
      footer_links: settings.value.footer_links,
      custom_css: settings.value.custom_css,
      custom_head_html: settings.value.custom_head_html,
      custom_footer_html: settings.value.custom_footer_html,
    };
    settings.value = await apiFetch<Settings>("/api/v1/site/settings", {
      method: "PUT",
      body: JSON.stringify(body),
    });
    if (!settings.value.footer_links) settings.value.footer_links = [];
    toast.show("Settings saved", "success");
  } catch (e: any) {
    toast.show(e.message || "Failed to save", "error");
  } finally {
    saving.value = false;
  }
}

function addFooterLink() {
  if (!settings.value) return;
  if (!settings.value.footer_links) settings.value.footer_links = [];
  settings.value.footer_links.push({ text: "Link", url: "/" });
}

function removeFooterLink(idx: number) {
  if (!settings.value?.footer_links) return;
  settings.value.footer_links.splice(idx, 1);
}

onMounted(loadSettings);
</script>

<template>
  <div class="page-wrap">
    <header class="page-head">
      <div>
        <h1 class="page-title">Site Settings</h1>
        <p class="page-sub">
          Branding, SEO, analytics, and footer for your public site and CMS pages.
        </p>
      </div>
      <button class="btn-primary" :disabled="saving" @click="saveSettings">
        {{ saving ? "Saving…" : "Save" }}
      </button>
    </header>

    <div v-if="loading" class="state-msg">Loading…</div>
    <div v-else-if="settings" class="settings-wrap">
      <!-- BRANDING -->
      <section class="accordion" :class="{ open: openSections.branding }">
        <button class="accordion-head" @click="toggle('branding')">
          <span>Branding</span>
          <span class="chev">{{ openSections.branding ? "▾" : "▸" }}</span>
        </button>
        <div v-if="openSections.branding" class="accordion-body">
          <div class="grid-2">
            <label class="field">
              <span>Site Title</span>
              <input v-model="settings.site_title" type="text" placeholder="HUBEX" />
            </label>
            <label class="field">
              <span>Tagline</span>
              <input v-model="settings.site_tagline" type="text" placeholder="Short catchphrase" />
            </label>
          </div>
          <div class="grid-2">
            <label class="field">
              <span>Logo URL</span>
              <input v-model="settings.logo_url" type="text" placeholder="https://…/logo.png" />
            </label>
            <label class="field">
              <span>Favicon URL</span>
              <input v-model="settings.favicon_url" type="text" placeholder="https://…/favicon.ico" />
            </label>
          </div>

          <h4 class="subsection">Colors</h4>
          <div class="grid-4">
            <label class="field">
              <span>Primary</span>
              <div class="color-input">
                <input type="color" v-model="settings.primary_color" />
                <input type="text" v-model="settings.primary_color" />
              </div>
            </label>
            <label class="field">
              <span>Accent</span>
              <div class="color-input">
                <input type="color" v-model="settings.accent_color" />
                <input type="text" v-model="settings.accent_color" />
              </div>
            </label>
            <label class="field">
              <span>Background</span>
              <div class="color-input">
                <input type="color" v-model="settings.bg_color" />
                <input type="text" v-model="settings.bg_color" />
              </div>
            </label>
            <label class="field">
              <span>Text</span>
              <div class="color-input">
                <input type="color" v-model="settings.text_color" />
                <input type="text" v-model="settings.text_color" />
              </div>
            </label>
          </div>

          <div class="preview-strip" :style="{ background: settings.bg_color, color: settings.text_color }">
            <strong :style="{ color: settings.primary_color }">{{ settings.site_title }}</strong>
            <span :style="{ color: settings.text_color }">{{ settings.site_tagline || "—" }}</span>
            <button :style="{ background: settings.primary_color, color: settings.bg_color }">
              Primary
            </button>
            <button :style="{ background: settings.accent_color, color: settings.bg_color }">
              Accent
            </button>
          </div>
        </div>
      </section>

      <!-- SEO -->
      <section class="accordion" :class="{ open: openSections.seo }">
        <button class="accordion-head" @click="toggle('seo')">
          <span>SEO Defaults</span>
          <span class="chev">{{ openSections.seo ? "▾" : "▸" }}</span>
        </button>
        <div v-if="openSections.seo" class="accordion-body">
          <label class="field">
            <span>Default Meta Title</span>
            <input
              v-model="settings.default_meta_title"
              type="text"
              placeholder="Used when a page doesn't set its own"
            />
          </label>
          <label class="field">
            <span>Default Meta Description</span>
            <textarea
              v-model="settings.default_meta_description"
              rows="3"
              placeholder="What your site is about"
            ></textarea>
          </label>
          <label class="field">
            <span>Default OG Image</span>
            <input
              v-model="settings.default_og_image"
              type="text"
              placeholder="https://…/og-image.png"
            />
          </label>
          <label class="field">
            <span>Twitter Handle</span>
            <input v-model="settings.twitter_handle" type="text" placeholder="@yourhandle" />
          </label>
        </div>
      </section>

      <!-- ANALYTICS -->
      <section class="accordion" :class="{ open: openSections.analytics }">
        <button class="accordion-head" @click="toggle('analytics')">
          <span>Analytics</span>
          <span class="chev">{{ openSections.analytics ? "▾" : "▸" }}</span>
        </button>
        <div v-if="openSections.analytics" class="accordion-body">
          <label class="field">
            <span>Google Analytics ID</span>
            <input v-model="settings.google_analytics_id" type="text" placeholder="G-XXXXXXXXXX" />
          </label>
          <label class="field">
            <span>Plausible Domain</span>
            <input v-model="settings.plausible_domain" type="text" placeholder="example.com" />
          </label>
        </div>
      </section>

      <!-- FOOTER -->
      <section class="accordion" :class="{ open: openSections.footer }">
        <button class="accordion-head" @click="toggle('footer')">
          <span>Footer</span>
          <span class="chev">{{ openSections.footer ? "▾" : "▸" }}</span>
        </button>
        <div v-if="openSections.footer" class="accordion-body">
          <label class="field">
            <span>Footer Text</span>
            <textarea
              v-model="settings.footer_text"
              rows="2"
              placeholder="© 2026 My Company"
            ></textarea>
          </label>
          <h4 class="subsection">Footer Links</h4>
          <div
            v-for="(link, idx) in settings.footer_links || []"
            :key="idx"
            class="link-row"
          >
            <input v-model="link.text" type="text" placeholder="Text" />
            <input v-model="link.url" type="text" placeholder="URL" />
            <button class="mini-btn danger" @click="removeFooterLink(idx)">×</button>
          </div>
          <button class="mini-btn" @click="addFooterLink">+ Add Link</button>
        </div>
      </section>

      <!-- ADVANCED -->
      <section class="accordion" :class="{ open: openSections.advanced }">
        <button class="accordion-head" @click="toggle('advanced')">
          <span>Advanced (Custom CSS/HTML)</span>
          <span class="chev">{{ openSections.advanced ? "▾" : "▸" }}</span>
        </button>
        <div v-if="openSections.advanced" class="accordion-body">
          <label class="field">
            <span>Custom CSS</span>
            <textarea
              v-model="settings.custom_css"
              rows="6"
              placeholder="/* Injected into every public CMS page */"
              class="mono"
            ></textarea>
          </label>
          <label class="field">
            <span>Custom &lt;head&gt; HTML</span>
            <textarea
              v-model="settings.custom_head_html"
              rows="6"
              placeholder="<script …>…</script>"
              class="mono"
            ></textarea>
          </label>
          <label class="field">
            <span>Custom Footer HTML</span>
            <textarea
              v-model="settings.custom_footer_html"
              rows="6"
              placeholder="<div>…</div>"
              class="mono"
            ></textarea>
          </label>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.page-wrap {
  padding: 24px 32px;
  max-width: 900px;
  margin: 0 auto;
}
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}
.page-title {
  font-size: 28px;
  font-weight: 700;
  color: #F5F5F5;
  margin: 0 0 4px;
}
.page-sub { color: #A1A1AA; margin: 0; font-size: 14px; max-width: 560px; }
.btn-primary {
  background: #F5A623;
  color: #111110;
  border: none;
  padding: 10px 18px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  font-size: 14px;
}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.state-msg { padding: 48px 24px; text-align: center; color: #71717A; }

.settings-wrap {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.accordion {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  overflow: hidden;
}
.accordion-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  background: transparent;
  color: #F5F5F5;
  border: none;
  padding: 18px 24px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  text-align: left;
}
.accordion-head:hover { color: #F5A623; }
.chev { color: #71717A; font-size: 12px; }
.accordion-body {
  padding: 8px 24px 24px;
  border-top: 1px solid rgba(255,255,255,0.06);
}
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.field { display: block; margin-bottom: 16px; }
.field span {
  display: block;
  font-size: 11px;
  color: #71717A;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 6px;
}
.field input,
.field textarea,
.field select {
  width: 100%;
  background: #0c0c0b;
  border: 1px solid rgba(255,255,255,0.1);
  color: #F5F5F5;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-family: inherit;
  box-sizing: border-box;
}
.field textarea.mono {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
}
.field input:focus,
.field textarea:focus,
.field select:focus { outline: none; border-color: #F5A623; }

.subsection {
  font-size: 11px;
  color: #71717A;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin: 16px 0 12px;
}
.color-input {
  display: flex;
  gap: 6px;
  align-items: center;
}
.color-input input[type="color"] {
  width: 36px;
  height: 36px;
  padding: 0;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 6px;
  cursor: pointer;
  background: transparent;
}
.color-input input[type="text"] {
  flex: 1;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
}
.preview-strip {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  border-radius: 8px;
  margin-top: 16px;
  border: 1px solid rgba(255,255,255,0.08);
}
.preview-strip strong { font-size: 18px; }
.preview-strip span { flex: 1; font-size: 13px; }
.preview-strip button {
  border: none;
  padding: 8px 14px;
  border-radius: 6px;
  font-weight: 600;
  font-size: 13px;
  cursor: default;
}
.link-row {
  display: grid;
  grid-template-columns: 1fr 2fr auto;
  gap: 8px;
  margin-bottom: 8px;
}
.link-row input {
  background: #0c0c0b;
  border: 1px solid rgba(255,255,255,0.1);
  color: #F5F5F5;
  padding: 8px 10px;
  border-radius: 4px;
  font-size: 13px;
}
.mini-btn {
  background: transparent;
  color: #A1A1AA;
  border: 1px solid rgba(255,255,255,0.1);
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}
.mini-btn:hover { color: #F5F5F5; }
.mini-btn.danger:hover { color: #ef4444; border-color: #ef4444; }
</style>
