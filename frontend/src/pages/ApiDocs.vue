<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import UCard from "../components/ui/UCard.vue";

const { t } = useI18n();
import UButton from "../components/ui/UButton.vue";
import UBadge from "../components/ui/UBadge.vue";

const copied = ref(false);
const openapiUrl = `${window.location.origin}/openapi.json`;

function copyUrl() {
  navigator.clipboard.writeText(openapiUrl);
  copied.value = true;
  setTimeout(() => (copied.value = false), 2000);
}

function openSwagger() {
  window.open("/docs", "_blank");
}
function openRedoc() {
  window.open("/redoc", "_blank");
}

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
  <div class="max-w-5xl mx-auto space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-bold text-[var(--text-primary)]">{{ t('pages.apiDocs.title') }}</h1>
      <p class="mt-1 text-sm text-[var(--text-muted)]">
        {{ t('pages.apiDocs.subtitle') }}
      </p>
    </div>

    <!-- Quick Links -->
    <div class="flex flex-wrap gap-3">
      <UButton variant="primary" @click="openSwagger">Swagger UI</UButton>
      <UButton variant="secondary" @click="openRedoc">ReDoc</UButton>
      <div class="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--bg-raised)]">
        <code class="text-xs text-[var(--text-muted)] font-mono truncate max-w-[260px]">{{ openapiUrl }}</code>
        <button
          class="text-xs text-[var(--primary)] hover:underline shrink-0"
          @click="copyUrl"
        >
          {{ copied ? "Copied!" : "Copy" }}
        </button>
      </div>
    </div>

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
</template>
