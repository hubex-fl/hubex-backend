<script setup lang="ts">
import { ref } from "vue";

const currentYear = new Date().getFullYear();

interface Feature {
  icon: string;
  title: string;
  description: string;
}

const features: Feature[] = [
  {
    icon: "signal",
    title: "Universal Devices",
    description:
      "ESP32, Raspberry Pi, Linux agents, Windows services, REST APIs, MQTT bridges — all through one unified protocol.",
  },
  {
    icon: "chart",
    title: "Real-time Variable Streams",
    description:
      "Grafana-style monitoring with sparklines, gauges, line charts. Auto-bridges telemetry into typed variables.",
  },
  {
    icon: "bolt",
    title: "Native Automations",
    description:
      "If-Then rules with variable thresholds, geofence triggers, device offline detection. No Lambda required.",
  },
  {
    icon: "workflow",
    title: "n8n Integration",
    description:
      "Custom n8n nodes connect HUBEX to 1000+ services. Alert fires, variable changes, device events — all trigger workflows.",
  },
  {
    icon: "shield",
    title: "Enterprise Security",
    description:
      "Multi-tenant organizations, 69 granular capabilities, JWT + HMAC device tokens, rate limiting, audit trails.",
  },
  {
    icon: "rocket",
    title: "One-Click Deploy",
    description:
      "Docker Compose with Traefik, SSL, PostgreSQL, Redis. Production-ready in under 1 hour on any Linux server.",
  },
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
  pricing: string;
}

const competitors: Competitor[] = [
  {
    name: "HUBEX",
    selfHosted: true,
    apiFirst: true,
    allDevices: true,
    automations: true,
    ota: true,
    multiTenant: true,
    openSource: true,
    pricing: "Free / $29/mo",
  },
  {
    name: "AWS IoT Core",
    selfHosted: false,
    apiFirst: false,
    allDevices: false,
    automations: "Lambda",
    ota: false,
    multiTenant: true,
    openSource: false,
    pricing: "Pay-per-msg",
  },
  {
    name: "ThingsBoard",
    selfHosted: "Complex",
    apiFirst: false,
    allDevices: false,
    automations: true,
    ota: false,
    multiTenant: true,
    openSource: "CE only",
    pricing: "Free / $3K+",
  },
  {
    name: "Home Assistant",
    selfHosted: true,
    apiFirst: false,
    allDevices: false,
    automations: "YAML",
    ota: false,
    multiTenant: false,
    openSource: true,
    pricing: "Free",
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
    pricing: "$2-5/device",
  },
];

interface PricingTier {
  name: string;
  price: string;
  period: string;
  description: string;
  features: string[];
  highlight: boolean;
  cta: string;
}

const pricingTiers: PricingTier[] = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "All core features. Self-hosted. No credit card.",
    features: [
      "5 devices",
      "1 organization",
      "7-day history",
      "5 automation rules",
      "REST API access",
      "Community support",
    ],
    highlight: false,
    cta: "Get Started",
  },
  {
    name: "Pro",
    price: "$29",
    period: "/month per org",
    description: "Extended limits, pro features, priority support.",
    features: [
      "50 devices",
      "3 organizations",
      "90-day history",
      "Unlimited automations",
      "Geofence triggers",
      "n8n templates",
      "Priority support",
    ],
    highlight: true,
    cta: "Start Free Trial",
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "contact us",
    description: "Unlimited scale, SSO, SLA, white-label.",
    features: [
      "Unlimited devices",
      "Unlimited orgs",
      "1-year+ history",
      "SSO / SAML",
      "White-label option",
      "Dedicated support",
      "Custom deployment",
    ],
    highlight: false,
    cta: "Contact Sales",
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
              class="h-7 w-7 text-cyan-400"
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
              >HUBEX</span
            >
          </div>
          <div class="hidden md:flex items-center gap-8">
            <a
              href="#features"
              class="text-sm text-gray-400 hover:text-white transition-colors"
              >Features</a
            >
            <a
              href="#architecture"
              class="text-sm text-gray-400 hover:text-white transition-colors"
              >Architecture</a
            >
            <a
              href="#comparison"
              class="text-sm text-gray-400 hover:text-white transition-colors"
              >Compare</a
            >
            <a
              href="#pricing"
              class="text-sm text-gray-400 hover:text-white transition-colors"
              >Pricing</a
            >
            <router-link
              to="/login"
              class="text-sm font-medium px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-gray-950 transition-colors"
              >Sign In</router-link
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
            >Features</a
          >
          <a
            href="#architecture"
            class="text-sm text-gray-400 hover:text-white"
            @click="mobileMenuOpen = false"
            >Architecture</a
          >
          <a
            href="#comparison"
            class="text-sm text-gray-400 hover:text-white"
            @click="mobileMenuOpen = false"
            >Compare</a
          >
          <a
            href="#pricing"
            class="text-sm text-gray-400 hover:text-white"
            @click="mobileMenuOpen = false"
            >Pricing</a
          >
          <router-link
            to="/login"
            class="text-sm font-medium px-4 py-2 rounded-lg bg-cyan-500 text-gray-950 text-center"
            >Sign In</router-link
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
        class="absolute inset-0 bg-gradient-to-b from-cyan-500/5 via-transparent to-transparent pointer-events-none"
      />
      <div
        class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-cyan-500/5 rounded-full blur-3xl pointer-events-none"
      />

      <div class="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <div
          class="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-cyan-500/20 bg-cyan-500/5 text-cyan-400 text-xs font-medium mb-8"
        >
          <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
          Open Source &middot; Self-Hosted &middot; API-First
        </div>

        <h1
          class="text-4xl sm:text-5xl lg:text-7xl font-extrabold tracking-tight leading-tight"
        >
          The Universal
          <br />
          <span
            class="bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent"
            >IoT Device Hub</span
          >
        </h1>

        <p
          class="mt-6 text-lg sm:text-xl text-gray-400 max-w-2xl mx-auto leading-relaxed"
        >
          From ESP32 to enterprise server — one platform for device management,
          real-time telemetry, automations, and OTA updates. Deploy in under 1
          hour.
        </p>

        <div
          class="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <a
            href="https://github.com/hubex-iot/hubex"
            target="_blank"
            rel="noopener"
            class="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-gray-950 font-semibold text-lg transition-colors"
          >
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path
                d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.385-1.335-1.755-1.335-1.755-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.605-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12c0-6.63-5.37-12-12-12"
              />
            </svg>
            Get Started
          </a>
          <router-link
            to="/login"
            class="inline-flex items-center gap-2 px-8 py-3 rounded-lg border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white font-semibold text-lg transition-colors"
          >
            View Demo
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
            <div class="text-2xl sm:text-3xl font-bold text-cyan-400">150+</div>
            <div class="text-sm text-gray-500 mt-1">API Endpoints</div>
          </div>
          <div>
            <div class="text-2xl sm:text-3xl font-bold text-cyan-400">17</div>
            <div class="text-sm text-gray-500 mt-1">UI Components</div>
          </div>
          <div>
            <div class="text-2xl sm:text-3xl font-bold text-cyan-400">69</div>
            <div class="text-sm text-gray-500 mt-1">Capabilities</div>
          </div>
          <div>
            <div class="text-2xl sm:text-3xl font-bold text-cyan-400">
              &lt;1h
            </div>
            <div class="text-sm text-gray-500 mt-1">To Deploy</div>
          </div>
        </div>
      </div>
    </section>

    <!-- Features Grid -->
    <section id="features" class="py-20 sm:py-28">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-16">
          <h2 class="text-3xl sm:text-4xl font-bold">
            Everything You Need to Ship IoT
          </h2>
          <p class="mt-4 text-gray-400 text-lg max-w-2xl mx-auto">
            A complete device management platform — not a collection of separate
            tools stitched together.
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div
            v-for="feature in features"
            :key="feature.title"
            class="group p-6 rounded-xl bg-gray-900/50 border border-gray-800 hover:border-cyan-500/30 transition-all duration-300"
          >
            <!-- Icons -->
            <div
              class="w-12 h-12 rounded-lg bg-cyan-500/10 flex items-center justify-center mb-4"
            >
              <!-- Signal icon -->
              <svg
                v-if="feature.icon === 'signal'"
                class="w-6 h-6 text-cyan-400"
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
                class="w-6 h-6 text-cyan-400"
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
                class="w-6 h-6 text-cyan-400"
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
                class="w-6 h-6 text-cyan-400"
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
                class="w-6 h-6 text-cyan-400"
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
                class="w-6 h-6 text-cyan-400"
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
            </div>
            <h3 class="text-lg font-semibold mb-2">{{ feature.title }}</h3>
            <p class="text-sm text-gray-400 leading-relaxed">
              {{ feature.description }}
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- Architecture -->
    <section id="architecture" class="py-20 sm:py-28 bg-gray-900/30">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-16">
          <h2 class="text-3xl sm:text-4xl font-bold">
            How It All Connects
          </h2>
          <p class="mt-4 text-gray-400 text-lg max-w-2xl mx-auto">
            Devices send data, HUBEX processes it, automations react, integrations extend.
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
            <h4 class="font-semibold text-sm mb-1">Devices</h4>
            <p class="text-xs text-gray-500">
              ESP32, RPi, APIs, MQTT, Agents
            </p>
          </div>
          <div
            class="p-5 rounded-xl bg-gray-900 border border-cyan-500/20 text-center ring-1 ring-cyan-500/10"
          >
            <div
              class="w-10 h-10 rounded-full bg-cyan-500/10 text-cyan-400 flex items-center justify-center mx-auto mb-3 text-lg font-bold"
            >
              2
            </div>
            <h4 class="font-semibold text-sm mb-1">HUBEX Core</h4>
            <p class="text-xs text-gray-500">
              FastAPI + PostgreSQL + Redis
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
            <h4 class="font-semibold text-sm mb-1">Automations</h4>
            <p class="text-xs text-gray-500">
              If-Then rules, alerts, OTA rollouts
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
            <h4 class="font-semibold text-sm mb-1">Integrations</h4>
            <p class="text-xs text-gray-500">
              n8n, webhooks, MCP, email
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
            How HUBEX Compares
          </h2>
          <p class="mt-4 text-gray-400 text-lg max-w-2xl mx-auto">
            One platform to replace fragmented tools. See how we stack up.
          </p>
        </div>

        <div class="overflow-x-auto -mx-4 px-4">
          <table
            class="w-full min-w-[700px] text-sm border-collapse"
          >
            <thead>
              <tr class="border-b border-gray-800">
                <th class="text-left py-3 px-3 text-gray-500 font-medium">
                  Feature
                </th>
                <th
                  v-for="c in competitors"
                  :key="c.name"
                  class="py-3 px-3 font-semibold text-center"
                  :class="c.name === 'HUBEX' ? 'text-cyan-400' : 'text-gray-300'"
                >
                  {{ c.name }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr class="border-b border-gray-800/50">
                <td class="py-3 px-3 text-gray-400">Self-hosted</td>
                <td
                  v-for="c in competitors"
                  :key="c.name"
                  class="py-3 px-3 text-center"
                >
                  <span
                    v-if="c.selfHosted === true"
                    class="text-green-400"
                    >Yes</span
                  >
                  <span
                    v-else-if="c.selfHosted === false"
                    class="text-red-400"
                    >No</span
                  >
                  <span v-else class="text-yellow-400">{{ c.selfHosted }}</span>
                </td>
              </tr>
              <tr class="border-b border-gray-800/50">
                <td class="py-3 px-3 text-gray-400">API-first</td>
                <td
                  v-for="c in competitors"
                  :key="c.name"
                  class="py-3 px-3 text-center"
                >
                  <span v-if="c.apiFirst" class="text-green-400">Yes</span>
                  <span v-else class="text-red-400">No</span>
                </td>
              </tr>
              <tr class="border-b border-gray-800/50">
                <td class="py-3 px-3 text-gray-400">All device types</td>
                <td
                  v-for="c in competitors"
                  :key="c.name"
                  class="py-3 px-3 text-center"
                >
                  <span v-if="c.allDevices" class="text-green-400">Yes</span>
                  <span v-else class="text-red-400">No</span>
                </td>
              </tr>
              <tr class="border-b border-gray-800/50">
                <td class="py-3 px-3 text-gray-400">Automations</td>
                <td
                  v-for="c in competitors"
                  :key="c.name"
                  class="py-3 px-3 text-center"
                >
                  <span
                    v-if="c.automations === true"
                    class="text-green-400"
                    >Native</span
                  >
                  <span
                    v-else-if="c.automations === false"
                    class="text-red-400"
                    >No</span
                  >
                  <span v-else class="text-yellow-400">{{ c.automations }}</span>
                </td>
              </tr>
              <tr class="border-b border-gray-800/50">
                <td class="py-3 px-3 text-gray-400">OTA updates</td>
                <td
                  v-for="c in competitors"
                  :key="c.name"
                  class="py-3 px-3 text-center"
                >
                  <span v-if="c.ota" class="text-green-400">Yes</span>
                  <span v-else class="text-red-400">No</span>
                </td>
              </tr>
              <tr class="border-b border-gray-800/50">
                <td class="py-3 px-3 text-gray-400">Multi-tenant</td>
                <td
                  v-for="c in competitors"
                  :key="c.name"
                  class="py-3 px-3 text-center"
                >
                  <span v-if="c.multiTenant" class="text-green-400">Yes</span>
                  <span v-else class="text-red-400">No</span>
                </td>
              </tr>
              <tr class="border-b border-gray-800/50">
                <td class="py-3 px-3 text-gray-400">Open source</td>
                <td
                  v-for="c in competitors"
                  :key="c.name"
                  class="py-3 px-3 text-center"
                >
                  <span
                    v-if="c.openSource === true"
                    class="text-green-400"
                    >Yes</span
                  >
                  <span
                    v-else-if="c.openSource === false"
                    class="text-red-400"
                    >No</span
                  >
                  <span v-else class="text-yellow-400">{{ c.openSource }}</span>
                </td>
              </tr>
              <tr>
                <td class="py-3 px-3 text-gray-400">Pricing</td>
                <td
                  v-for="c in competitors"
                  :key="c.name"
                  class="py-3 px-3 text-center text-gray-300 text-xs"
                >
                  {{ c.pricing }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Pricing -->
    <section id="pricing" class="py-20 sm:py-28 bg-gray-900/30">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-16">
          <h2 class="text-3xl sm:text-4xl font-bold">Simple, Transparent Pricing</h2>
          <p class="mt-4 text-gray-400 text-lg max-w-2xl mx-auto">
            Start free. Scale when you need to. All tiers can be self-hosted.
          </p>
        </div>

        <div
          class="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto"
        >
          <div
            v-for="tier in pricingTiers"
            :key="tier.name"
            class="rounded-xl p-6 sm:p-8 flex flex-col"
            :class="
              tier.highlight
                ? 'bg-gray-900 border-2 border-cyan-500/40 ring-1 ring-cyan-500/20 relative'
                : 'bg-gray-900/50 border border-gray-800'
            "
          >
            <div
              v-if="tier.highlight"
              class="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full bg-cyan-500 text-gray-950 text-xs font-bold"
            >
              Most Popular
            </div>
            <div class="mb-6">
              <h3 class="text-lg font-semibold">{{ tier.name }}</h3>
              <div class="mt-2 flex items-baseline gap-1">
                <span class="text-3xl sm:text-4xl font-extrabold">{{
                  tier.price
                }}</span>
                <span class="text-sm text-gray-500">{{ tier.period }}</span>
              </div>
              <p class="mt-2 text-sm text-gray-400">
                {{ tier.description }}
              </p>
            </div>
            <ul class="flex-1 space-y-3 mb-8">
              <li
                v-for="f in tier.features"
                :key="f"
                class="flex items-start gap-2 text-sm"
              >
                <svg
                  class="w-4 h-4 mt-0.5 text-cyan-400 flex-shrink-0"
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
                <span class="text-gray-300">{{ f }}</span>
              </li>
            </ul>
            <button
              class="w-full py-3 rounded-lg font-semibold text-sm transition-colors"
              :class="
                tier.highlight
                  ? 'bg-cyan-500 hover:bg-cyan-400 text-gray-950'
                  : 'bg-gray-800 hover:bg-gray-700 text-gray-200'
              "
            >
              {{ tier.cta }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- Final CTA -->
    <section class="py-20 sm:py-28">
      <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h2 class="text-3xl sm:text-4xl font-bold">
          Start Building in 5 Minutes
        </h2>
        <p class="mt-4 text-gray-400 text-lg max-w-xl mx-auto">
          Clone the repo, run Docker Compose, pair your first device. It really
          is that simple.
        </p>
        <div
          class="mt-8 p-4 rounded-lg bg-gray-900 border border-gray-800 max-w-lg mx-auto text-left"
        >
          <code class="text-sm text-cyan-400 font-mono">
            <span class="text-gray-500">$</span> git clone
            https://github.com/hubex-iot/hubex.git<br />
            <span class="text-gray-500">$</span> cd hubex<br />
            <span class="text-gray-500">$</span> docker compose up -d<br />
            <span class="text-gray-500">#</span>
            <span class="text-gray-500"> Open http://localhost:5173</span>
          </code>
        </div>
        <div class="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
          <a
            href="https://github.com/hubex-iot/hubex"
            target="_blank"
            rel="noopener"
            class="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-gray-950 font-semibold transition-colors"
          >
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path
                d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.385-1.335-1.755-1.335-1.755-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.605-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12c0-6.63-5.37-12-12-12"
              />
            </svg>
            GitHub
          </a>
          <a
            href="https://github.com/hubex-iot/hubex/blob/main/docs/GETTING_STARTED.md"
            target="_blank"
            rel="noopener"
            class="inline-flex items-center gap-2 px-8 py-3 rounded-lg border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white font-semibold transition-colors"
          >
            Read the Docs
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
            class="h-5 w-5 text-cyan-400/50"
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
          HUBEX &copy; {{ currentYear }}. Open Source under MIT License.
        </div>
        <div class="flex items-center gap-6">
          <a
            href="https://github.com/hubex-iot/hubex"
            target="_blank"
            rel="noopener"
            class="text-gray-500 hover:text-gray-300 text-sm"
            >GitHub</a
          >
          <a href="#features" class="text-gray-500 hover:text-gray-300 text-sm"
            >Features</a
          >
          <a href="#pricing" class="text-gray-500 hover:text-gray-300 text-sm"
            >Pricing</a
          >
        </div>
      </div>
    </footer>
  </div>
</template>
