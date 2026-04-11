<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from "vue";
import { useI18n } from "vue-i18n";
import UCard from "../components/ui/UCard.vue";
import UButton from "../components/ui/UButton.vue";
import UBadge from "../components/ui/UBadge.vue";
import UInfoTooltip from "../components/ui/UInfoTooltip.vue";

const { t, tm, rt } = useI18n();

const copied = ref(false);
const activeTab = ref<"swagger" | "redoc" | "overview">("swagger");
const swaggerContainer = ref<HTMLElement | null>(null);
const redocContainer = ref<HTMLElement | null>(null);
const swaggerLoaded = ref(false);
const redocLoaded = ref(false);
const loadError = ref("");
// Sprint 8 R3-F21 fix: track in-flight script loads so the UI can
// show a proper loading spinner instead of briefly flashing the
// error banner ("Could not load ReDoc") before the CDN script
// finishes fetching.
const swaggerLoading = ref(false);
const redocLoading = ref(false);

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
  if (swaggerLoaded.value) return;
  // Sprint 8 R3-F21 fix: same container-race guard as Redoc below.
  if (!swaggerContainer.value) {
    await nextTick();
    if (!swaggerContainer.value) return;
  }
  loadError.value = "";
  swaggerLoading.value = true;
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

    // Inject dark mode styles for Swagger UI to match HUBEX theme
    injectSwaggerDarkMode();
  } catch (err: any) {
    loadError.value = `Could not load Swagger UI: ${err.message}. Try opening /docs in a new tab instead.`;
  } finally {
    swaggerLoading.value = false;
  }
}

async function initRedoc() {
  if (redocLoaded.value) return;
  // Sprint 8 R3-F21 fix: container may not be in the DOM on first
  // click because the parent <div v-show="activeTab === 'redoc'">
  // flips at the same tick as initRedoc() runs. Wait one more tick
  // so the container ref resolves before we try to mount Redoc into it.
  if (!redocContainer.value) {
    await nextTick();
    if (!redocContainer.value) return;
  }
  loadError.value = "";
  redocLoading.value = true;
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
  } finally {
    redocLoading.value = false;
  }
}

function injectSwaggerDarkMode() {
  const existingStyle = document.getElementById("swagger-dark-mode");
  if (existingStyle) return;
  const style = document.createElement("style");
  style.id = "swagger-dark-mode";
  style.textContent = `
    .swagger-ui-wrapper {
      background: #1a1a19 !important;
    }
    .swagger-ui {
      color: #e0ddd8 !important;
    }
    .swagger-ui .topbar {
      display: none !important;
    }
    .swagger-ui .info .title,
    .swagger-ui .info h1,
    .swagger-ui .info h2,
    .swagger-ui .info h3,
    .swagger-ui .opblock-tag {
      color: #e0ddd8 !important;
    }
    .swagger-ui .info .base-url,
    .swagger-ui .info p,
    .swagger-ui .info li,
    .swagger-ui .info a,
    .swagger-ui .info .markdown p,
    .swagger-ui .info .markdown li {
      color: #a8a49c !important;
    }
    .swagger-ui .scheme-container {
      background: #222221 !important;
      box-shadow: none !important;
    }
    .swagger-ui .opblock-tag {
      border-bottom-color: #333 !important;
    }
    .swagger-ui .opblock {
      background: #1e1e1d !important;
      border-color: #333 !important;
    }
    .swagger-ui .opblock .opblock-summary {
      border-color: #333 !important;
    }
    .swagger-ui .opblock .opblock-summary-method {
      font-weight: 700;
    }
    .swagger-ui .opblock .opblock-summary-description,
    .swagger-ui .opblock .opblock-summary-path,
    .swagger-ui .opblock .opblock-summary-path span {
      color: #c8c4bc !important;
    }
    .swagger-ui .opblock-body,
    .swagger-ui .opblock .opblock-section-header {
      background: #222221 !important;
      border-color: #333 !important;
    }
    .swagger-ui .opblock .opblock-section-header h4,
    .swagger-ui .opblock .opblock-section-header label {
      color: #e0ddd8 !important;
    }
    .swagger-ui table thead tr th,
    .swagger-ui table thead tr td,
    .swagger-ui .parameter__name,
    .swagger-ui .parameter__type,
    .swagger-ui .parameter__in {
      color: #c8c4bc !important;
    }
    .swagger-ui .parameters-col_description p,
    .swagger-ui .parameters-col_description input,
    .swagger-ui .parameters-col_description textarea,
    .swagger-ui .parameters-col_description select {
      color: #e0ddd8 !important;
    }
    .swagger-ui input[type="text"],
    .swagger-ui textarea,
    .swagger-ui select {
      background: #2a2a29 !important;
      border-color: #444 !important;
      color: #e0ddd8 !important;
    }
    .swagger-ui .model-box,
    .swagger-ui .model {
      background: #222221 !important;
      color: #c8c4bc !important;
    }
    .swagger-ui .model-title {
      color: #e0ddd8 !important;
    }
    .swagger-ui .model .property,
    .swagger-ui .model .property.primitive {
      color: #c8c4bc !important;
    }
    .swagger-ui section.models {
      border-color: #333 !important;
    }
    .swagger-ui section.models h4,
    .swagger-ui section.models h4 span {
      color: #e0ddd8 !important;
    }
    .swagger-ui .response-col_status,
    .swagger-ui .response-col_description,
    .swagger-ui .response-col_description p,
    .swagger-ui .responses-inner h4,
    .swagger-ui .responses-inner h5 {
      color: #c8c4bc !important;
    }
    .swagger-ui .highlight-code,
    .swagger-ui .microlight,
    .swagger-ui .example {
      background: #1e1e1d !important;
      color: #c8c4bc !important;
    }
    .swagger-ui .btn {
      color: #e0ddd8 !important;
      border-color: #555 !important;
    }
    .swagger-ui .btn:hover {
      background: #333 !important;
    }
    .swagger-ui .opblock.opblock-get .opblock-summary {
      border-color: #2DD4BF40 !important;
    }
    .swagger-ui .opblock.opblock-post .opblock-summary {
      border-color: #3b82f640 !important;
    }
    .swagger-ui .opblock.opblock-put .opblock-summary {
      border-color: #F5A62340 !important;
    }
    .swagger-ui .opblock.opblock-delete .opblock-summary {
      border-color: #ef444440 !important;
    }
    .swagger-ui .authorization__btn {
      fill: #F5A623 !important;
    }
  `;
  document.head.appendChild(style);
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
      <div class="flex items-center gap-1.5">
        <h1 class="text-2xl font-bold text-[var(--text-primary)]">{{ t('pages.apiDocs.title') }}</h1>
        <UInfoTooltip :title="t('infoTooltips.apiDocs.title')" :items="tm('infoTooltips.apiDocs.items').map((i: any) => rt(i))" />
      </div>
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

    <!--
      Error message — Sprint 8 R3-F21 fix: only show when there's
      actually an error. Hidden while the script is still loading
      so users don't see a brief "Could not load ReDoc" flash
      between tab-click and script-ready.
    -->
    <div
      v-if="loadError && !swaggerLoading && !redocLoading"
      class="p-4 rounded-lg border border-amber-500/30 bg-amber-500/10 text-sm text-amber-300"
    >
      {{ loadError }}
    </div>

    <!-- Swagger UI Tab -->
    <div v-show="activeTab === 'swagger'">
      <!-- Loading state for Swagger UI -->
      <div
        v-if="swaggerLoading && !swaggerLoaded"
        class="flex items-center justify-center gap-3 py-12 rounded-xl border border-[var(--border)] bg-[var(--bg-raised)] text-sm text-[var(--text-muted)]"
      >
        <svg class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" stroke-dasharray="60" stroke-dashoffset="20" /></svg>
        {{ t('pages.apiDocs.loadingSwagger') }}
      </div>
      <div
        ref="swaggerContainer"
        id="swagger-ui-embed"
        class="swagger-ui-wrapper rounded-xl border border-[var(--border)] min-h-[400px]"
      />
    </div>

    <!-- ReDoc Tab -->
    <div v-show="activeTab === 'redoc'">
      <!-- Loading state for ReDoc -->
      <div
        v-if="redocLoading && !redocLoaded"
        class="flex items-center justify-center gap-3 py-12 rounded-xl border border-[var(--border)] bg-[var(--bg-raised)] text-sm text-[var(--text-muted)]"
      >
        <svg class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" stroke-dasharray="60" stroke-dashoffset="20" /></svg>
        {{ t('pages.apiDocs.loadingRedoc') }}
      </div>
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
  background: #1a1a19;
  border-color: #333;
}

/* ReDoc wrapper styling */
.redoc-wrapper {
  background: #1a1a19;
}
</style>
