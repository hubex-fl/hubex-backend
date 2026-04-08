<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from "vue";
import { useI18n } from "vue-i18n";
import UCard from "../components/ui/UCard.vue";
import UButton from "../components/ui/UButton.vue";
import UBadge from "../components/ui/UBadge.vue";

const { t } = useI18n();

const copied = ref(false);
const activeTab = ref<"swagger" | "redoc" | "overview">("swagger");
const swaggerContainer = ref<HTMLElement | null>(null);
const redocContainer = ref<HTMLElement | null>(null);
const swaggerLoaded = ref(false);
const redocLoaded = ref(false);
const loadError = ref("");

// Use relative URL so it works behind any reverse proxy
const openapiUrl = "/openapi.json";
const openapiFullUrl = `${window.location.origin}/openapi.json`;

function copyUrl() {
  navigator.clipboard.writeText(openapiFullUrl);
  copied.value = true;
  setTimeout(() => (copied.value = false), 2000);
}

function openSwaggerNewTab() {
  window.open("/docs", "_blank");
}
function openRedocNewTab() {
  window.open("/redoc", "_blank");
}

// Dynamically load a script from CDN
function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = src;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
    document.head.appendChild(script);
  });
}

// Dynamically load a CSS file from CDN
function loadCSS(href: string): void {
  if (document.querySelector(`link[href="${href}"]`)) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = href;
  document.head.appendChild(link);
}

async function initSwagger() {
  if (swaggerLoaded.value || !swaggerContainer.value) return;
  loadError.value = "";
  try {
    loadCSS("https://unpkg.com/swagger-ui-dist@5/swagger-ui.css");
    await loadScript("https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js");

    const w = window as any;
    if (!w.SwaggerUIBundle) {
      throw new Error("SwaggerUIBundle not available after script load");
    }

    w.SwaggerUIBundle({
      url: openapiUrl,
      dom_id: "#swagger-ui-embed",
      presets: [w.SwaggerUIBundle.presets.apis],
      layout: "BaseLayout",
      deepLinking: true,
      defaultModelsExpandDepth: 0,
      docExpansion: "list",
    });
    swaggerLoaded.value = true;
  } catch (err: any) {
    loadError.value = `Could not load Swagger UI: ${err.message}. Try opening /docs in a new tab instead.`;
  }
}

async function initRedoc() {
  if (redocLoaded.value || !redocContainer.value) return;
  loadError.value = "";
  try {
    await loadScript("https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js");

    const w = window as any;
    if (!w.Redoc) {
      throw new Error("Redoc not available after script load");
    }

    w.Redoc.init(
      openapiUrl,
      {
        scrollYOffset: 60,
        hideDownloadButton: false,
        theme: {
          colors: {
            primary: { main: "#F5A623" },
          },
          typography: {
            fontFamily: "Inter, system-ui, sans-serif",
            headings: { fontFamily: "Inter, system-ui, sans-serif" },
          },
          rightPanel: { backgroundColor: "#1a1a19" },
          sidebar: { backgroundColor: "#151514" },
        },
      },
      redocContainer.value
    );
    redocLoaded.value = true;
  } catch (err: any) {
    loadError.value = `Could not load ReDoc: ${err.message}. Try opening /redoc in a new tab instead.`;
  }
}

watch(activeTab, async (tab) => {
  loadError.value = "";
  await nextTick();
  if (tab === "swagger") {
    initSwagger();
  } else if (tab === "redoc") {
    initRedoc();
  }
});

onMounted(() => {
  if (activeTab.value === "swagger") {
    initSwagger();
  }
});

interface ApiSection {
  name: string;
  path: string;
  description: string;
  endpoints: string[];
  badge: "ok" | "info" | "warn" | "neutral";
}

const sections: ApiSection[] = [
  {
    name: "Auth",
    path: "/api/v1/auth",
    description: "JWT authentication, login, refresh, logout",
    endpoints: ["POST /login", "POST /refresh", "POST /logout", "GET /me"],
    badge: "ok",
  },
  {
    name: "Devices",
    path: "/api/v1/devices",
    description: "Device CRUD, health, pairing, variables",
    endpoints: ["GET /", "GET /{uid}", "PATCH /{uid}", "DELETE /{uid}", "GET /{uid}/variables"],
    badge: "info",
  },
  {
    name: "Telemetry",
    path: "/api/v1/telemetry",
    description: "Ingest and query device telemetry data",
    endpoints: ["POST /", "GET /", "GET /latest/{uid}"],
    badge: "info",
  },
  {
    name: "Variables",
    path: "/api/v1/variables",
    description: "Variable definitions, values, history, snapshots, bulk-set",
    endpoints: ["GET /definitions", "POST /definitions", "PATCH /definitions/{key}", "GET /history", "GET /snapshot", "POST /bulk-set"],
    badge: "neutral",
  },
  {
    name: "Alerts",
    path: "/api/v1/alerts",
    description: "Alert rules and events, acknowledge/resolve",
    endpoints: ["GET /rules", "POST /rules", "GET /events", "POST /events/{id}/ack"],
    badge: "warn",
  },
  {
    name: "Webhooks",
    path: "/api/v1/webhooks",
    description: "Webhook subscriptions for real-time event delivery",
    endpoints: ["GET /", "POST /", "DELETE /{id}", "GET /deliveries"],
    badge: "ok",
  },
  {
    name: "Entities",
    path: "/api/v1/entities",
    description: "Logical entities with device bindings",
    endpoints: ["GET /", "POST /", "PATCH /{id}", "POST /{id}/bind", "POST /{id}/unbind"],
    badge: "info",
  },
  {
    name: "OTA",
    path: "/api/v1/ota",
    description: "Firmware versions, rollouts, device OTA check",
    endpoints: ["GET /versions", "POST /versions", "POST /rollouts", "GET /check"],
    badge: "warn",
  },
  {
    name: "Automations",
    path: "/api/v1/automations",
    description: "Native if-then automation rules",
    endpoints: ["GET /", "POST /", "PATCH /{id}", "DELETE /{id}", "POST /{id}/test"],
    badge: "neutral",
  },
  {
    name: "Edge",
    path: "/api/v1/edge",
    description: "Edge device config sync",
    endpoints: ["GET /config"],
    badge: "ok",
  },
];
</script>

<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-bold text-[var(--text-primary)]">{{ t('pages.apiDocs.title') }}</h1>
      <p class="mt-1 text-sm text-[var(--text-muted)]">
        {{ t('pages.apiDocs.subtitle') }}
      </p>
    </div>

    <!-- Tab Bar -->
    <div class="flex items-center gap-1 border-b border-[var(--border)]">
      <button
        v-for="tab in (['swagger', 'redoc', 'overview'] as const)"
        :key="tab"
        :class="[
          'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
          activeTab === tab
            ? 'border-[var(--primary)] text-[var(--primary)]'
            : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)] hover:border-[var(--border-hover)]',
        ]"
        @click="activeTab = tab"
      >
        {{ tab === 'swagger' ? 'Swagger UI' : tab === 'redoc' ? 'ReDoc' : 'Overview' }}
      </button>

      <!-- Right-side actions -->
      <div class="ml-auto flex items-center gap-2 pb-1">
        <div class="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--bg-raised)]">
          <code class="text-xs text-[var(--text-muted)] font-mono truncate max-w-[200px]">{{ openapiFullUrl }}</code>
          <button
            class="text-xs text-[var(--primary)] hover:underline shrink-0"
            @click="copyUrl"
          >
            {{ copied ? "Copied!" : "Copy" }}
          </button>
        </div>
        <UButton variant="ghost" size="sm" @click="openSwaggerNewTab">Open /docs</UButton>
        <UButton variant="ghost" size="sm" @click="openRedocNewTab">Open /redoc</UButton>
      </div>
    </div>

    <!-- Error message -->
    <div
      v-if="loadError"
      class="p-4 rounded-lg border border-amber-500/30 bg-amber-500/10 text-sm text-amber-300"
    >
      {{ loadError }}
    </div>

    <!-- Swagger UI Tab -->
    <div v-show="activeTab === 'swagger'">
      <div
        ref="swaggerContainer"
        id="swagger-ui-embed"
        class="swagger-ui-wrapper rounded-xl border border-[var(--border)] bg-white min-h-[400px]"
      />
    </div>

    <!-- ReDoc Tab -->
    <div v-show="activeTab === 'redoc'">
      <div
        ref="redocContainer"
        class="redoc-wrapper rounded-xl border border-[var(--border)] overflow-hidden min-h-[400px]"
      />
    </div>

    <!-- Overview Tab -->
    <div v-if="activeTab === 'overview'" class="space-y-6">
      <!-- Authentication -->
      <UCard title="Authentication">
        <div class="space-y-3 text-sm text-[var(--text-secondary)]">
          <p>HUBEX uses <strong>JWT Bearer tokens</strong>. The typical flow is:</p>
          <ol class="list-decimal list-inside space-y-1 pl-2">
            <li>
              <code class="text-xs bg-[var(--bg-raised)] px-1 py-0.5 rounded">POST /api/v1/auth/login</code>
              with <code class="text-xs bg-[var(--bg-raised)] px-1 py-0.5 rounded">{ email, password }</code>
            </li>
            <li>
              Receive <code class="text-xs bg-[var(--bg-raised)] px-1 py-0.5 rounded">access_token</code> +
              <code class="text-xs bg-[var(--bg-raised)] px-1 py-0.5 rounded">refresh_token</code>
            </li>
            <li>
              Pass <code class="text-xs bg-[var(--bg-raised)] px-1 py-0.5 rounded">Authorization: Bearer &lt;token&gt;</code>
              on all subsequent requests
            </li>
            <li>
              Refresh via <code class="text-xs bg-[var(--bg-raised)] px-1 py-0.5 rounded">POST /api/v1/auth/refresh</code>
              when the access token expires
            </li>
          </ol>
          <p class="text-[var(--text-muted)]">
            Device endpoints use <code class="text-xs bg-[var(--bg-raised)] px-1 py-0.5 rounded">X-Device-Token</code>
            header instead of JWT.
          </p>
        </div>
      </UCard>

      <!-- Rate Limits -->
      <UCard title="Rate Limits">
        <div class="text-sm text-[var(--text-secondary)] space-y-2">
          <p>
            Requests are rate-limited per user via Redis sliding window.
            Default limits are generous for development but enforced in production.
          </p>
          <div class="flex gap-4 flex-wrap">
            <div class="flex items-center gap-2">
              <UBadge label="Auth" status="warn" />
              <span>10 req/min per IP</span>
            </div>
            <div class="flex items-center gap-2">
              <UBadge label="Telemetry" status="info" />
              <span>120 req/min per device</span>
            </div>
            <div class="flex items-center gap-2">
              <UBadge label="General" status="ok" />
              <span>60 req/min per user</span>
            </div>
          </div>
        </div>
      </UCard>

      <!-- API Sections Grid -->
      <div>
        <h2 class="text-lg font-semibold text-[var(--text-primary)] mb-3">API Sections</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <UCard
            v-for="section in sections"
            :key="section.name"
            :title="section.name"
          >
            <template #actions>
              <UBadge :label="section.path" :status="section.badge" />
            </template>
            <div class="space-y-2">
              <p class="text-sm text-[var(--text-muted)]">{{ section.description }}</p>
              <div class="flex flex-wrap gap-1.5">
                <code
                  v-for="ep in section.endpoints"
                  :key="ep"
                  class="text-[11px] font-mono px-1.5 py-0.5 rounded bg-[var(--bg-raised)] text-[var(--text-secondary)] border border-[var(--border)]"
                >
                  {{ ep }}
                </code>
              </div>
            </div>
          </UCard>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Override Swagger UI styles to fit the dark theme container */
.swagger-ui-wrapper {
  padding: 1rem;
}

/* ReDoc wrapper styling */
.redoc-wrapper {
  background: #fafafa;
}
</style>
