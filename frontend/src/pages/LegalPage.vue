<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";

const { t } = useI18n();

const props = defineProps<{ page: "impressum" | "datenschutz" }>();

const title = computed(() =>
  props.page === "impressum" ? t("legal.impressum.title") : t("legal.datenschutz.title")
);
</script>

<template>
  <div class="legal-page">
    <nav class="legal-nav">
      <router-link to="/landing" class="logo-link">
        <span class="logo-text">HubEx</span>
      </router-link>
      <div class="nav-links">
        <router-link to="/impressum" :class="{ active: page === 'impressum' }">Impressum</router-link>
        <router-link to="/datenschutz" :class="{ active: page === 'datenschutz' }">Datenschutz</router-link>
        <router-link to="/landing">{{ t('common.back') }}</router-link>
      </div>
    </nav>

    <main class="legal-content">
      <h1>{{ title }}</h1>

      <!-- Impressum -->
      <template v-if="page === 'impressum'">
        <section>
          <h2>{{ t('legal.impressum.operator') }}</h2>
          <p>
            <strong>[Name / Firma eintragen]</strong><br />
            [Straße und Hausnummer]<br />
            [PLZ Ort]<br />
            [Land]
          </p>
        </section>

        <section>
          <h2>{{ t('legal.impressum.contact') }}</h2>
          <p>
            E-Mail: <a href="mailto:kontakt@hubextest.tech">kontakt@hubextest.tech</a><br />
            Web: <a href="https://hubextest.tech">hubextest.tech</a>
          </p>
        </section>

        <section>
          <h2>{{ t('legal.impressum.responsibility') }}</h2>
          <p>{{ t('legal.impressum.responsibilityText') }}</p>
        </section>

        <section>
          <h2>{{ t('legal.impressum.disclaimer') }}</h2>
          <p>{{ t('legal.impressum.disclaimerText') }}</p>
        </section>
      </template>

      <!-- Datenschutz -->
      <template v-if="page === 'datenschutz'">
        <section>
          <h2>{{ t('legal.datenschutz.overview') }}</h2>
          <p>{{ t('legal.datenschutz.overviewText') }}</p>
        </section>

        <section>
          <h2>{{ t('legal.datenschutz.collection') }}</h2>
          <p>{{ t('legal.datenschutz.collectionText') }}</p>
          <ul>
            <li>{{ t('legal.datenschutz.collectionItem1') }}</li>
            <li>{{ t('legal.datenschutz.collectionItem2') }}</li>
            <li>{{ t('legal.datenschutz.collectionItem3') }}</li>
          </ul>
        </section>

        <section>
          <h2>{{ t('legal.datenschutz.cookies') }}</h2>
          <p>{{ t('legal.datenschutz.cookiesText') }}</p>
        </section>

        <section>
          <h2>{{ t('legal.datenschutz.hosting') }}</h2>
          <p>{{ t('legal.datenschutz.hostingText') }}</p>
        </section>

        <section>
          <h2>{{ t('legal.datenschutz.rights') }}</h2>
          <p>{{ t('legal.datenschutz.rightsText') }}</p>
        </section>

        <section>
          <h2>{{ t('legal.datenschutz.contactSection') }}</h2>
          <p>{{ t('legal.datenschutz.contactText') }}</p>
        </section>
      </template>
    </main>

    <footer class="legal-footer">
      <p>&copy; {{ new Date().getFullYear() }} HubEx</p>
    </footer>
  </div>
</template>

<style scoped>
.legal-page {
  min-height: 100vh;
  background: #111110;
  color: #e0e0e0;
}

.legal-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  border-bottom: 1px solid #2a2a2a;
}
.logo-link { text-decoration: none; }
.logo-text { font-size: 18px; font-weight: 700; color: #F5A623; }
.nav-links { display: flex; gap: 16px; }
.nav-links a {
  color: #999;
  text-decoration: none;
  font-size: 13px;
  transition: color 0.2s;
}
.nav-links a:hover, .nav-links a.active { color: #F5A623; }

.legal-content {
  max-width: 720px;
  margin: 0 auto;
  padding: 48px 24px;
}
.legal-content h1 {
  font-size: 28px;
  font-weight: 700;
  color: #F5A623;
  margin-bottom: 32px;
}
.legal-content h2 {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  margin-top: 32px;
  margin-bottom: 12px;
}
.legal-content p {
  font-size: 14px;
  line-height: 1.7;
  color: #bbb;
  margin-bottom: 12px;
}
.legal-content ul {
  list-style: disc;
  padding-left: 24px;
  margin-bottom: 12px;
}
.legal-content li {
  font-size: 14px;
  color: #bbb;
  margin-bottom: 6px;
}
.legal-content a {
  color: #F5A623;
  text-decoration: none;
}
.legal-content a:hover { text-decoration: underline; }
section { margin-bottom: 24px; }

.legal-footer {
  text-align: center;
  padding: 24px;
  border-top: 1px solid #2a2a2a;
  font-size: 12px;
  color: #666;
}
</style>
