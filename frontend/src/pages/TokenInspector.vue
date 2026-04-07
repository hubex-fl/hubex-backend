<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { getToken } from "../lib/api";

const { t } = useI18n();

function decodePayload(token: string) {
  const parts = token.split(".");
  if (parts.length < 2) return null;
  const payload = parts[1];
  const b64 = payload.replace(/-/g, "+").replace(/_/g, "/");
  const pad = b64.length % 4 === 0 ? "" : "=".repeat(4 - (b64.length % 4));
  try {
    const json = atob(b64 + pad);
    return JSON.parse(json);
  } catch {
    return null;
  }
}

const token = getToken();
const payload = computed(() => (token ? decodePayload(token) : null));
const invalid = computed(() => token && !payload.value);

const sub = computed(() => payload.value?.sub ?? "-");
const iss = computed(() => payload.value?.iss ?? "-");
const jti = computed(() => payload.value?.jti ?? "-");
const expSec = computed(() => {
  const exp = payload.value?.exp;
  return typeof exp === "number" ? exp : null;
});
const expIso = computed(() => {
  if (!expSec.value) return "-";
  return new Date(expSec.value * 1000).toISOString();
});
const remaining = computed(() => {
  if (!expSec.value) return "-";
  const ms = expSec.value * 1000 - Date.now();
  if (ms <= 0) return "expired";
  const totalSec = Math.floor(ms / 1000);
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min}m ${sec}s`;
});
const caps = computed(() => {
  const list = payload.value?.caps || payload.value?.capabilities;
  if (!Array.isArray(list)) return [] as string[];
  return [...list].map(String).sort();
});
</script>

<template>
  <div class="card">
    <h2>{{ t('pages.tokenInspector.title') }}</h2>

    <div v-if="!token" class="muted">Token missing</div>
    <div v-else-if="invalid" class="error">Invalid token format</div>

    <div v-else class="info-grid">
      <div class="info-item">
        <div class="info-label">sub</div>
        <div class="info-value cell-mono">{{ sub }}</div>
      </div>
      <div class="info-item">
        <div class="info-label">iss</div>
        <div class="info-value cell-mono">{{ iss }}</div>
      </div>
      <div class="info-item">
        <div class="info-label">jti</div>
        <div class="info-value cell-mono">{{ jti }}</div>
      </div>
      <div class="info-item">
        <div class="info-label">exp (ISO)</div>
        <div class="info-value cell-mono">{{ expIso }}</div>
      </div>
      <div class="info-item">
        <div class="info-label">expires in</div>
        <div class="info-value cell-mono">{{ remaining }}</div>
      </div>
      <div class="info-item">
        <div class="info-label">caps</div>
        <div class="info-value">
          <span v-if="caps.length" class="cell-mono">{{ caps.join(", ") }}</span>
          <span v-else>caps: none</span>
        </div>
      </div>
    </div>
  </div>
</template>
