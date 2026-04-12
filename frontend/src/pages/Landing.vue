<script setup lang="ts">
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import { setLocale } from "../i18n";

const { t, locale } = useI18n();

// Sprint 10: language selector for unauthenticated landing visitors.
// Uses setLocale() which also persists to localStorage + sets html[lang].
function switchLandingLocale(lang: string) {
  setLocale(lang as "en" | "de" | "fr" | "es");
}

const currentYear = new Date().getFullYear();

interface Feature {
  icon: string;
  titleKey: string;
  descKey: string;
}

const features: Feature[] = [
  { icon: "signal", titleKey: "landing.features.universalTitle", descKey: "landing.features.universalDesc" },
  { icon: "chart", titleKey: "landing.features.streamsTitle", descKey: "landing.features.streamsDesc" },
  { icon: "bolt", titleKey: "landing.features.automationsTitle", descKey: "landing.features.automationsDesc" },
  { icon: "workflow", titleKey: "landing.features.n8nTitle", descKey: "landing.features.n8nDesc" },
  { icon: "shield", titleKey: "landing.features.securityTitle", descKey: "landing.features.securityDesc" },
  { icon: "rocket", titleKey: "landing.features.deployTitle", descKey: "landing.features.deployDesc" },
  // Sprint 10: additional feature tiles to showcase the full platform
  { icon: "puzzle", titleKey: "landing.features.pluginsTitle", descKey: "landing.features.pluginsDesc" },
  { icon: "flask", titleKey: "landing.features.sandboxTitle", descKey: "landing.features.sandboxDesc" },
  { icon: "api", titleKey: "landing.features.customApiTitle", descKey: "landing.features.customApiDesc" },
  { icon: "map", titleKey: "landing.features.systemMapTitle", descKey: "landing.features.systemMapDesc" },
  { icon: "mail", titleKey: "landing.features.emailTitle", descKey: "landing.features.emailDesc" },
  { icon: "robot", titleKey: "landing.features.mcpTitle", descKey: "landing.features.mcpDesc" },
];

interface Competitor {
  name: string;
  selfHosted: boolean | string;
  apiFirst: boolean;
  allDevices: boolean;
  automations: boolean | string;
  ota: boolean;
  multiTenant: boolean;
  openSource: boolean | string;
  pricingKey: string;
}

const competitors = computed<Competitor[]>(() => [
  {
    name: "HUBEX",
    selfHosted: true,
    apiFirst: true,
    allDevices: true,
    automations: true,
    ota: true,
    multiTenant: true,
    openSource: true,
    pricingKey: "landing.comparison.pricingHubex",
  },
  {
    name: "AWS IoT Core",
    selfHosted: false,
    apiFirst: false,
    allDevices: false,
    automations: "lambda",
    ota: false,
    multiTenant: true,
    openSource: false,
    pricingKey: "landing.comparison.valPayPerMsg",
  },
  {
    name: "ThingsBoard",
    selfHosted: "complex",
    apiFirst: false,
    allDevices: false,
    automations: true,
    ota: false,
    multiTenant: true,
    openSource: "ceOnly",
    pricingKey: "landing.comparison.pricingThingsboard",
  },
  {
    name: "Home Assistant",
    selfHosted: true,
    apiFirst: false,
    allDevices: false,
    automations: "yaml",
    ota: false,
    multiTenant: false,
    openSource: true,
    pricingKey: "landing.comparison.valFree",
  },
  {
    name: "Datacake",
    selfHosted: false,
    apiFirst: false,
    allDevices: false,
    automations: false,
    ota: false,
    multiTenant: true,
    openSource: false,
    pricingKey: "landing.comparison.pricingDatacake",
  },
]);

function compareLabel(value: boolean | string, trueKey = "landing.comparison.valYes"): string {
  if (value === true) return t(trueKey);
  if (value === false) return t("landing.comparison.valNo");
  // String literal: look up variant
  const variantKey: Record<string, string> = {
    lambda: "landing.comparison.valLambda",
    complex: "landing.comparison.valComplex",
    yaml: "landing.comparison.valYaml",
    ceOnly: "landing.comparison.valCeOnly",
  };
  const k = variantKey[value];
  return k ? t(k) : value;
}

interface PricingTier {
  key: "free" | "pro" | "ent";
  nameKey: string;
  priceKey: string;
  periodKey: string;
  descKey: string;
  ctaKey: string;
  featureKeys: string[];
  highlight: boolean;
}

const pricingTiers: PricingTier[] = [
  {
    key: "free",
    nameKey: "landing.pricing.freeName",
    priceKey: "landing.pricing.freePrice",
    periodKey: "landing.pricing.freePeriod",
    descKey: "landing.pricing.freeDesc",
    ctaKey: "landing.pricing.freeCta",
    featureKeys: [
      "landing.pricing.freeFeature1",
      "landing.pricing.freeFeature2",
      "landing.pricing.freeFeature3",
      "landing.pricing.freeFeature4",
      "landing.pricing.freeFeature5",
      "landing.pricing.freeFeature6",
    ],
    highlight: false,
  },
  {
    key: "pro",
    nameKey: "landing.pricing.proName",
    priceKey: "landing.pricing.proPrice",
    periodKey: "landing.pricing.proPeriod",
    descKey: "landing.pricing.proDesc",
    ctaKey: "landing.pricing.proCta",
    featureKeys: [
      "landing.pricing.proFeature1",
      "landing.pricing.proFeature2",
      "landing.pricing.proFeature3",
      "landing.pricing.proFeature4",
      "landing.pricing.proFeature5",
      "landing.pricing.proFeature6",
      "landing.pricing.proFeature7",
    ],
    highlight: true,
  },
  {
    key: "ent",
    nameKey: "landing.pricing.entName",
    priceKey: "landing.pricing.entPrice",
    periodKey: "landing.pricing.entPeriod",
    descKey: "landing.pricing.entDesc",
    ctaKey: "landing.pricing.entCta",
    featureKeys: [
      "landing.pricing.entFeature1",
      "landing.pricing.entFeature2",
      "landing.pricing.entFeature3",
      "landing.pricing.entFeature4",
      "landing.pricing.entFeature5",
      "landing.pricing.entFeature6",
      "landing.pricing.entFeature7",
    ],
    highlight: false,
  },
];

const mobileMenuOpen = ref(false);
</script>

<template>
  <div class="min-h-screen bg-gray-950 text-white antialiased">
    <!-- Navigation -->
    <nav
      class="fixed top-0 left-0 right-0 z-50 bg-gray-950/80 backdrop-blur-xl border-b border-white/5"
    >
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <div class="flex items-center gap-2">
            <svg
              class="h-7 w-7 text-[#2DD4BF]"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-13.5 0v-1.5m13.5 1.5v-1.5m0 0a3 3 0 00-3-3H7.5a3 3 0 00-3 3m13.5 0v-6.75a3 3 0 00-3-3H7.5a3 3 0 00-3 3v6.75"
              />
            </svg>
            <span class="text-xl font-bold font-mono tracking-widest"
              >{{ t('landing.nav.brand') }}</span
            >
          </div>
          <div class="hidden md:flex items-center gap-8">
            <a
              href="#features"
              class="text-sm text-gray-400 hover:text-white transition-colors"
              >{{ t('landing.nav.features') }}</a
            >
            <a
              href="#architecture"
              class="text-sm text-gray-400 hover:text-white transition-colors"
              >{{ t('landing.nav.architecture') }}</a
            >
            <a
              href="#comparison"
              class="text-sm text-gray-400 hover:text-white transition-colors"
              >{{ t('landing.nav.compare') }}</a
            >
            <!-- pricing nav hidden (Sprint 9 #8) -->
            <!-- Sprint 10: language selector for unauthenticated visitors -->
            <select
              :value="locale"
              class="text-sm bg-transparent text-gray-400 hover:text-white border border-gray-700 rounded-lg px-2 py-1.5 focus:outline-none focus:border-[#F5A623]/60 cursor-pointer"
              @change="switchLandingLocale(($event.target as HTMLSelectElement).value)"
            >
              <option value="en" class="bg-gray-900">English</option>
              <option value="de" class="bg-gray-900">Deutsch</option>
              <option value="fr" class="bg-gray-900">Français</option>
              <option value="es" class="bg-gray-900">Español</option>
            </select>
            <router-link
              to="/login"
              class="text-sm font-medium px-4 py-2 rounded-lg bg-[#F5A623] hover:bg-[#E09510] text-gray-950 transition-colors"
              >{{ t('landing.nav.signIn') }}</router-link
            >
          </div>
          <button
            class="md:hidden text-gray-400 hover:text-white"
            @click="mobileMenuOpen = !mobileMenuOpen"
          >
            <svg
              class="h-6 w-6"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              viewBox="0 0 24 24"
            >
              <path
                v-if="!mobileMenuOpen"
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M4 6h16M4 12h16M4 18h16"
              />
              <path
                v-else
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
        <!-- Mobile menu -->
        <div
          v-if="mobileMenuOpen"
          class="md:hidden pb-4 flex flex-col gap-3"
        >
          <a
            href="#features"
            class="text-sm text-gray-400 hover:text-white"
            @click="mobileMenuOpen = false"
            >{{ t('landing.nav.features') }}</a
          >
          <a
            href="#architecture"
            class="text-sm text-gray-400 hover:text-white"
            @click="mobileMenuOpen = false"
            >{{ t('landing.nav.architecture') }}</a
          >
          <a
            href="#comparison"
            class="text-sm text-gray-400 hover:text-white"
            @click="mobileMenuOpen = false"
            >{{ t('landing.nav.compare') }}</a
          >
          <!-- pricing nav hidden (Sprint 9 #8) -->
          <router-link
            to="/login"
            class="text-sm font-medium px-4 py-2 rounded-lg bg-[#F5A623] text-gray-950 text-center"
            >{{ t('landing.nav.signIn') }}</router-link
          >
        </div>
      </div>
    </nav>

    <!-- Hero Section -->
    <section
      class="relative pt-32 pb-20 sm:pt-40 sm:pb-28 overflow-hidden"
    >
      <!-- Background gradient -->
      <div
        class="absolute inset-0 bg-gradient-to-b from-[#F5A623]/5 via-transparent to-transparent pointer-events-none"
      />
      <div
        class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-[#F5A623]/5 rounded-full blur-3xl pointer-events-none"
      />

      <div class="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <div
          class="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[#F5A623]/20 bg-[#F5A623]/5 text-[#2DD4BF] text-xs font-medium mb-8"
        >
          <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
          {{ t('landing.hero.badge') }}
        </div>

        <h1
          class="text-4xl sm:text-5xl lg:text-7xl font-extrabold tracking-tight leading-tight"
        >
          {{ t('landing.hero.titleLine1') }}
          <br />
          <span
            class="bg-gradient-to-r from-[#F5A623] to-[#2DD4BF] bg-clip-text text-transparent"
            >{{ t('landing.hero.titleLine2') }}</span
          >
        </h1>

        <p
          class="mt-6 text-lg sm:text-xl text-gray-400 max-w-2xl mx-auto leading-relaxed"
        >
          {{ t('landing.hero.subtitle') }}
        </p>

        <div
          class="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <a
            href="https://github.com/hubex-iot/hubex"
            target="_blank"
            rel="noopener"
            class="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-[#F5A623] hover:bg-[#E09510] text-gray-950 font-semibold text-lg transition-colors"
          >
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path
                d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.385-1.335-1.755-1.335-1.755-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.605-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12c0-6.63-5.37-12-12-12"
              />
            </svg>
            {{ t('landing.hero.ctaGetStarted') }}
          </a>
          <router-link
            to="/login"
            class="inline-flex items-center gap-2 px-8 py-3 rounded-lg border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white font-semibold text-lg transition-colors"
          >
            {{ t('landing.hero.ctaViewDemo') }}
            <svg
              class="w-4 h-4"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"
              />
            </svg>
          </router-link>
        </div>

        <!-- Stats -->
        <div
          class="mt-16 grid grid-cols-2 sm:grid-cols-4 gap-6 max-w-3xl mx-auto"
        >
          <div>
            <div class="text-2xl sm:text-3xl font-bold text-[#2DD4BF]">150+</div>
            <div class="text-sm text-gray-500 mt-1">{{ t('landing.hero.statApiEndpoints') }}</div>
          </div>
          <div>
            <div class="text-2xl sm:text-3xl font-bold text-[#2DD4BF]">17</div>
            <div class="text-sm text-gray-500 mt-1">{{ t('landing.hero.statUiComponents') }}</div>
          </div>
          <div>
            <div class="text-2xl sm:text-3xl font-bold text-[#2DD4BF]">69</div>
            <div class="text-sm text-gray-500 mt-1">{{ t('landing.hero.statCapabilities') }}</div>
          </div>
          <div>
            <div class="text-2xl sm:text-3xl font-bold text-[#2DD4BF]">
              &lt;1h
            </div>
            <div class="text-sm text-gray-500 mt-1">{{ t('landing.hero.statToDeploy') }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- Features Grid -->
    <section id="features" class="py-20 sm:py-28">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-16">
          <h2 class="text-3xl sm:text-4xl font-bold">
            {{ t('landing.features.heading') }}
          </h2>
          <p class="mt-4 text-gray-400 text-lg max-w-2xl mx-auto">
            {{ t('landing.features.subheading') }}
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div
            v-for="feature in features"
            :key="feature.titleKey"
            class="group p-6 rounded-xl bg-gray-900/50 border border-gray-800 hover:border-[#F5A623]/30 transition-all duration-300"
          >
            <!-- Icons -->
            <div
              class="w-12 h-12 rounded-lg bg-[#F5A623]/10 flex items-center justify-center mb-4"
            >
              <!-- Signal icon -->
              <svg
                v-if="feature.icon === 'signal'"
                class="w-6 h-6 text-[#2DD4BF]"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M9.348 14.652a3.75 3.75 0 010-5.304m5.304 0a3.75 3.75 0 010 5.304m-7.425 2.121a6.75 6.75 0 010-9.546m9.546 0a6.75 6.75 0 010 9.546M5.106 18.894c-3.808-3.808-3.808-9.98 0-13.788m13.788 0c3.808 3.808 3.808 9.98 0 13.788M12 12h.008v.008H12V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
                />
              </svg>
              <!-- Chart icon -->
              <svg
                v-if="feature.icon === 'chart'"
                class="w-6 h-6 text-[#2DD4BF]"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
                />
              </svg>
              <!-- Bolt icon -->
              <svg
                v-if="feature.icon === 'bolt'"
                class="w-6 h-6 text-[#2DD4BF]"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"
                />
              </svg>
              <!-- Workflow icon -->
              <svg
                v-if="feature.icon === 'workflow'"
                class="w-6 h-6 text-[#2DD4BF]"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5"
                />
              </svg>
              <!-- Shield icon -->
              <svg
                v-if="feature.icon === 'shield'"
                class="w-6 h-6 text-[#2DD4BF]"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
                />
              </svg>
              <!-- Rocket icon -->
              <svg
                v-if="feature.icon === 'rocket'"
                class="w-6 h-6 text-[#2DD4BF]"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z"
                />
              </svg>
              <!-- Sprint 10: icons for new feature tiles -->
              <svg v-if="feature.icon === 'puzzle'" class="w-6 h-6 text-[#2DD4BF]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M14.25 6.087c0-.355.186-.676.401-.959.221-.29.349-.634.349-1.003 0-1.036-1.007-1.875-2.25-1.875s-2.25.84-2.25 1.875c0 .369.128.713.349 1.003.215.283.401.604.401.959v0a.64.64 0 01-.657.643 48.421 48.421 0 01-4.185-.07c-.96-.044-1.808-.676-1.808-1.637v-.84c0-.355-.186-.676-.401-.959A1.647 1.647 0 014 2.25c0-1.036 1.007-1.875 2.25-1.875S8.5 1.214 8.5 2.25c0 .369-.128.713-.349 1.003-.215.283-.401.604-.401.959" />
              </svg>
              <svg v-if="feature.icon === 'flask'" class="w-6 h-6 text-[#2DD4BF]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-2.47 7.411A1.125 1.125 0 0115.46 23H8.54a1.125 1.125 0 01-1.07-1.089L5 14.5m14 0H5" />
              </svg>
              <svg v-if="feature.icon === 'api'" class="w-6 h-6 text-[#2DD4BF]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
              </svg>
              <svg v-if="feature.icon === 'map'" class="w-6 h-6 text-[#2DD4BF]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 6.75V15m0-8.25a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm0 8.25a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm6.75-12.75a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm0 8.25a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0z" />
              </svg>
              <svg v-if="feature.icon === 'mail'" class="w-6 h-6 text-[#2DD4BF]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
              </svg>
              <svg v-if="feature.icon === 'robot'" class="w-6 h-6 text-[#2DD4BF]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z" />
              </svg>
            </div>
            <h3 class="text-lg font-semibold mb-2">{{ t(feature.titleKey) }}</h3>
            <p class="text-sm text-gray-400 leading-relaxed">
              {{ t(feature.descKey) }}
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- Architecture -->
    <!-- Sprint 10: CE vs EE subtle banner -->
    <div class="py-8 text-center border-t border-white/5">
      <div class="max-w-3xl mx-auto px-4 flex flex-wrap items-center justify-center gap-3">
        <span class="px-3 py-1 rounded-full text-xs font-bold bg-[#F5A623]/10 text-[#F5A623] border border-[#F5A623]/20">{{ t('landing.ceVsEe.ceBadge') }}</span>
        <p class="text-sm text-gray-400">{{ t('landing.ceVsEe.text') }}</p>
        <span class="px-3 py-1 rounded-full text-xs font-bold bg-[#2DD4BF]/10 text-[#2DD4BF] border border-[#2DD4BF]/20">{{ t('landing.ceVsEe.eeBadge') }}</span>
      </div>
    </div>

    <section id="architecture" class="py-20 sm:py-28 bg-gray-900/30">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-16">
          <h2 class="text-3xl sm:text-4xl font-bold">
            {{ t('landing.architecture.heading') }}
          </h2>
          <p class="mt-4 text-gray-400 text-lg max-w-2xl mx-auto">
            {{ t('landing.architecture.subheading') }}
          </p>
        </div>

        <!-- Architecture flow -->
        <div
          class="max-w-4xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
        >
          <div
            class="p-5 rounded-xl bg-gray-900 border border-gray-800 text-center"
          >
            <div
              class="w-10 h-10 rounded-full bg-blue-500/10 text-blue-400 flex items-center justify-center mx-auto mb-3 text-lg font-bold"
            >
              1
            </div>
            <h4 class="font-semibold text-sm mb-1">{{ t('landing.architecture.step1Title') }}</h4>
            <p class="text-xs text-gray-500">
              {{ t('landing.architecture.step1Desc') }}
            </p>
          </div>
          <div
            class="p-5 rounded-xl bg-gray-900 border border-[#F5A623]/20 text-center ring-1 ring-[#F5A623]/10"
          >
            <div
              class="w-10 h-10 rounded-full bg-[#F5A623]/10 text-[#2DD4BF] flex items-center justify-center mx-auto mb-3 text-lg font-bold"
            >
              2
            </div>
            <h4 class="font-semibold text-sm mb-1">{{ t('landing.architecture.step2Title') }}</h4>
            <p class="text-xs text-gray-500">
              {{ t('landing.architecture.step2Desc') }}
            </p>
          </div>
          <div
            class="p-5 rounded-xl bg-gray-900 border border-gray-800 text-center"
          >
            <div
              class="w-10 h-10 rounded-full bg-purple-500/10 text-purple-400 flex items-center justify-center mx-auto mb-3 text-lg font-bold"
            >
              3
            </div>
            <h4 class="font-semibold text-sm mb-1">{{ t('landing.architecture.step3Title') }}</h4>
            <p class="text-xs text-gray-500">
              {{ t('landing.architecture.step3Desc') }}
            </p>
          </div>
          <div
            class="p-5 rounded-xl bg-gray-900 border border-gray-800 text-center"
          >
            <div
              class="w-10 h-10 rounded-full bg-green-500/10 text-green-400 flex items-center justify-center mx-auto mb-3 text-lg font-bold"
            >
              4
            </div>
            <h4 class="font-semibold text-sm mb-1">{{ t('landing.architecture.step4Title') }}</h4>
            <p class="text-xs text-gray-500">
              {{ t('landing.architecture.step4Desc') }}
            </p>
          </div>
        </div>

        <!-- Arrow connectors (visible on lg) -->
        <div
          class="hidden lg:flex max-w-4xl mx-auto justify-between px-20 -mt-2"
        >
          <svg
            v-for="i in 3"
            :key="i"
            class="w-8 h-6 text-gray-700"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"
            />
          </svg>
        </div>

        <!-- Tech stack badges -->
        <div class="flex flex-wrap justify-center gap-3 mt-12">
          <span
            v-for="tech in [
              'Python 3.11+',
              'FastAPI',
              'SQLAlchemy',
              'PostgreSQL',
              'Redis',
              'Vue 3',
              'TypeScript',
              'Tailwind CSS',
              'Docker',
              'Traefik',
            ]"
            :key="tech"
            class="px-3 py-1 rounded-full text-xs font-medium bg-gray-800 text-gray-400 border border-gray-700"
          >
            {{ tech }}
          </span>
        </div>
      </div>
    </section>

    <!-- Comparison Table -->
    <section id="comparison" class="py-20 sm:py-28">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-16">
          <h2 class="text-3xl sm:text-4xl font-bold">
            {{ t('landing.comparison.heading') }}
          </h2>
          <p class="mt-4 text-gray-400 text-lg max-w-2xl mx-auto">
            {{ t('landing.comparison.subheading') }}
          </p>
        </div>

        <div class="overflow-x-auto -mx-4 px-4">
          <table
            class="w-full min-w-[700px] text-sm border-collapse"
          >
            <thead>
              <tr class="border-b border-gray-800">
                <th class="text-left py-3 px-3 text-gray-500 font-medium">
                  {{ t('landing.comparison.colFeature') }}
                </th>
                <th
                  v-for="c in competitors"
                  :key="c.name"
                  class="py-3 px-3 font-semibold text-center"
                  :class="c.name === 'HUBEX' ? 'text-[#2DD4BF]' : 'text-gray-300'"
                >
                  {{ c.name }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr class="border-b border-gray-800/50">
                <td class="py-3 px-3 text-gray-400">{{ t('landing.comparison.rowSelfHosted') }}</td>
                <td
                  v-for="c in competitors"
                  :key="c.name"
                  class="py-3 px-3 text-center"
                >
                  <span
                    v-if="c.selfHosted === true"
                    class="text-green-400"
                    >{{ t('landing.comparison.valYes') }}</span
                  >
                  <span
                    v-else-if="c.selfHosted === false"
                    class="text-red-400"
                    >{{ t('landing.comparison.valNo') }}</span
                  >
                  <span v-else class="text-yellow-400">{{ compareLabel(c.selfHosted) }}</span>
                </td>
              </tr>
              <tr class="border-b border-gray-800/50">
                <td class="py-3 px-3 text-gray-400">{{ t('landing.comparison.rowApiFirst') }}</td>
                <td
                  v-for="c in competitors"
                  :key="c.name"
                  class="py-3 px-3 text-center"
                >
                  <span v-if="c.apiFirst" class="text-green-400">{{ t('landing.comparison.valYes') }}</span>
                  <span v-else class="text-red-400">{{ t('landing.comparison.valNo') }}</span>
                </td>
              </tr>
              <tr class="border-b border-gray-800/50">
                <td class="py-3 px-3 text-gray-400">{{ t('landing.comparison.rowAllDevices') }}</td>
                <td
                  v-for="c in competitors"
                  :key="c.name"
                  class="py-3 px-3 text-center"
                >
                  <span v-if="c.allDevices" class="text-green-400">{{ t('landing.comparison.valYes') }}</span>
                  <span v-else class="text-red-400">{{ t('landing.comparison.valNo') }}</span>
                </td>
              </tr>
              <tr class="border-b border-gray-800/50">
                <td class="py-3 px-3 text-gray-400">{{ t('landing.comparison.rowAutomations') }}</td>
                <td
                  v-for="c in competitors"
                  :key="c.name"
                  class="py-3 px-3 text-center"
                >
                  <span
                    v-if="c.automations === true"
                    class="text-green-400"
                    >{{ t('landing.comparison.valNative') }}</span
                  >
                  <span
                    v-else-if="c.automations === false"
                    class="text-red-400"
                    >{{ t('landing.comparison.valNo') }}</span
                  >
                  <span v-else class="text-yellow-400">{{ compareLabel(c.automations) }}</span>
                </td>
              </tr>
              <tr class="border-b border-gray-800/50">
                <td class="py-3 px-3 text-gray-400">{{ t('landing.comparison.rowOta') }}</td>
                <td
                  v-for="c in competitors"
                  :key="c.name"
                  class="py-3 px-3 text-center"
                >
                  <span v-if="c.ota" class="text-green-400">{{ t('landing.comparison.valYes') }}</span>
                  <span v-else class="text-red-400">{{ t('landing.comparison.valNo') }}</span>
                </td>
              </tr>
              <tr class="border-b border-gray-800/50">
                <td class="py-3 px-3 text-gray-400">{{ t('landing.comparison.rowMultiTenant') }}</td>
                <td
                  v-for="c in competitors"
                  :key="c.name"
                  class="py-3 px-3 text-center"
                >
                  <span v-if="c.multiTenant" class="text-green-400">{{ t('landing.comparison.valYes') }}</span>
                  <span v-else class="text-red-400">{{ t('landing.comparison.valNo') }}</span>
                </td>
              </tr>
              <tr class="border-b border-gray-800/50">
                <td class="py-3 px-3 text-gray-400">{{ t('landing.comparison.rowOpenSource') }}</td>
                <td
                  v-for="c in competitors"
                  :key="c.name"
                  class="py-3 px-3 text-center"
                >
                  <span
                    v-if="c.openSource === true"
                    class="text-green-400"
                    >{{ t('landing.comparison.valYes') }}</span
                  >
                  <span
                    v-else-if="c.openSource === false"
                    class="text-red-400"
                    >{{ t('landing.comparison.valNo') }}</span
                  >
                  <span v-else class="text-yellow-400">{{ compareLabel(c.openSource) }}</span>
                </td>
              </tr>
              <tr>
                <td class="py-3 px-3 text-gray-400">{{ t('landing.comparison.rowPricing') }}</td>
                <td
                  v-for="c in competitors"
                  :key="c.name"
                  class="py-3 px-3 text-center text-gray-300 text-xs"
                >
                  {{ t(c.pricingKey) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Pricing — hidden until pricing model is finalized (Sprint 9 #8) -->
    <section v-if="false" id="pricing" class="py-20 sm:py-28 bg-gray-900/30">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-16">
          <h2 class="text-3xl sm:text-4xl font-bold">{{ t('landing.pricing.heading') }}</h2>
          <p class="mt-4 text-gray-400 text-lg max-w-2xl mx-auto">
            {{ t('landing.pricing.subheading') }}
          </p>
        </div>

        <div
          class="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto"
        >
          <div
            v-for="tier in pricingTiers"
            :key="tier.key"
            class="rounded-xl p-6 sm:p-8 flex flex-col"
            :class="
              tier.highlight
                ? 'bg-gray-900 border-2 border-[#F5A623]/40 ring-1 ring-[#F5A623]/20 relative'
                : 'bg-gray-900/50 border border-gray-800'
            "
          >
            <div
              v-if="tier.highlight"
              class="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full bg-[#F5A623] text-gray-950 text-xs font-bold"
            >
              {{ t('landing.pricing.mostPopular') }}
            </div>
            <div class="mb-6">
              <h3 class="text-lg font-semibold">{{ t(tier.nameKey) }}</h3>
              <div class="mt-2 flex items-baseline gap-1">
                <span class="text-3xl sm:text-4xl font-extrabold">{{
                  t(tier.priceKey)
                }}</span>
                <span class="text-sm text-gray-500">{{ t(tier.periodKey) }}</span>
              </div>
              <p class="mt-2 text-sm text-gray-400">
                {{ t(tier.descKey) }}
              </p>
            </div>
            <ul class="flex-1 space-y-3 mb-8">
              <li
                v-for="fKey in tier.featureKeys"
                :key="fKey"
                class="flex items-start gap-2 text-sm"
              >
                <svg
                  class="w-4 h-4 mt-0.5 text-[#2DD4BF] flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M4.5 12.75l6 6 9-13.5"
                  />
                </svg>
                <span class="text-gray-300">{{ t(fKey) }}</span>
              </li>
            </ul>
            <button
              class="w-full py-3 rounded-lg font-semibold text-sm transition-colors"
              :class="
                tier.highlight
                  ? 'bg-[#F5A623] hover:bg-[#E09510] text-gray-950'
                  : 'bg-gray-800 hover:bg-gray-700 text-gray-200'
              "
            >
              {{ t(tier.ctaKey) }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- Final CTA -->
    <section class="py-20 sm:py-28">
      <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h2 class="text-3xl sm:text-4xl font-bold">
          {{ t('landing.finalCta.heading') }}
        </h2>
        <p class="mt-4 text-gray-400 text-lg max-w-xl mx-auto">
          {{ t('landing.finalCta.subheading') }}
        </p>
        <div
          class="mt-8 p-4 rounded-lg bg-gray-900 border border-gray-800 max-w-lg mx-auto text-left"
        >
          <code class="text-sm text-[#2DD4BF] font-mono">
            <span class="text-gray-500">$</span> git clone
            https://github.com/hubex-iot/hubex.git<br />
            <span class="text-gray-500">$</span> cd hubex<br />
            <span class="text-gray-500">$</span> docker compose up -d<br />
            <span class="text-gray-500">{{ t('landing.finalCta.openComment') }}</span>
          </code>
        </div>
        <div class="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
          <a
            href="https://github.com/hubex-iot/hubex"
            target="_blank"
            rel="noopener"
            class="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-[#F5A623] hover:bg-[#E09510] text-gray-950 font-semibold transition-colors"
          >
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path
                d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.385-1.335-1.755-1.335-1.755-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.605-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12c0-6.63-5.37-12-12-12"
              />
            </svg>
            {{ t('landing.finalCta.ctaGithub') }}
          </a>
          <a
            href="https://github.com/hubex-iot/hubex/blob/main/docs/GETTING_STARTED.md"
            target="_blank"
            rel="noopener"
            class="inline-flex items-center gap-2 px-8 py-3 rounded-lg border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white font-semibold transition-colors"
          >
            {{ t('landing.finalCta.ctaReadDocs') }}
          </a>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="py-8 border-t border-gray-800/50">
      <div
        class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4"
      >
        <div class="flex items-center gap-2 text-gray-500 text-sm">
          <svg
            class="h-5 w-5 text-[#2DD4BF]/50"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-13.5 0v-1.5m13.5 1.5v-1.5m0 0a3 3 0 00-3-3H7.5a3 3 0 00-3 3m13.5 0v-6.75a3 3 0 00-3-3H7.5a3 3 0 00-3 3v6.75"
            />
          </svg>
          {{ t('landing.footer.copyright', { year: currentYear }) }}
        </div>
        <div class="flex items-center gap-6">
          <a
            href="https://github.com/hubex-iot/hubex"
            target="_blank"
            rel="noopener"
            class="text-gray-500 hover:text-gray-300 text-sm"
            >{{ t('landing.finalCta.ctaGithub') }}</a
          >
          <a href="#features" class="text-gray-500 hover:text-gray-300 text-sm"
            >{{ t('landing.nav.features') }}</a
          >
          <router-link to="/impressum" class="text-gray-500 hover:text-gray-300 text-sm">Impressum</router-link>
          <router-link to="/datenschutz" class="text-gray-500 hover:text-gray-300 text-sm">Datenschutz</router-link>
        </div>
      </div>
    </footer>
  </div>
</template>
