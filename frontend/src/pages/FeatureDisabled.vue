<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useFeaturesStore } from "../stores/features";

const route = useRoute();
const router = useRouter();
const features = useFeaturesStore();
const { t } = useI18n();

const featureKey = computed(() => (route.query.feature as string) || "");
const fromPath = computed(() => (route.query.from as string) || "/");

const featureName = computed(() => {
  const f = features.flags[featureKey.value];
  return f?.name || featureKey.value || t("featureDisabled.defaultFeatureName");
});

const featureDescription = computed(() => {
  const f = features.flags[featureKey.value];
  return f?.description || "";
});

function goHome() {
  router.push("/");
}

function goToSettings() {
  router.push("/settings");
}
</script>

<template>
  <div class="feature-disabled-wrap">
    <div class="feature-disabled-card">
      <div class="icon-wrap">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke-width="1.5"
          stroke="currentColor"
          class="icon"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M18.364 18.364A9 9 0 0 0 5.636 5.636m12.728 12.728A9 9 0 0 1 5.636 5.636m12.728 12.728L5.636 5.636"
          />
        </svg>
      </div>
      <h1 class="title">{{ t('featureDisabled.title') }}</h1>
      <p class="feature-name">{{ featureName }}</p>
      <p v-if="featureDescription" class="feature-desc">{{ featureDescription }}</p>
      <p class="hint">
        {{ t('featureDisabled.hint') }}
        <strong>{{ t('featureDisabled.hintSettings') }}</strong>.
      </p>
      <p v-if="fromPath !== '/'" class="from-path">
        {{ t('featureDisabled.triedToAccess') }} <code>{{ fromPath }}</code>
      </p>
      <div class="actions">
        <button class="btn-primary" @click="goToSettings">{{ t('featureDisabled.openSettings') }}</button>
        <button class="btn-secondary" @click="goHome">{{ t('featureDisabled.backToDashboard') }}</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.feature-disabled-wrap {
  min-height: 70vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
}

.feature-disabled-card {
  max-width: 520px;
  width: 100%;
  text-align: center;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 48px 32px;
}

.icon-wrap {
  display: inline-flex;
  padding: 16px;
  border-radius: 50%;
  background: rgba(245, 166, 35, 0.08);
  color: #f5a623;
  margin-bottom: 16px;
}

.icon {
  width: 48px;
  height: 48px;
}

.title {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 8px;
  color: #f5f5f5;
}

.feature-name {
  font-size: 18px;
  font-weight: 600;
  color: #2dd4bf;
  margin: 0 0 8px;
}

.feature-desc {
  color: #a1a1aa;
  margin: 0 0 16px;
  line-height: 1.5;
}

.hint {
  color: #a1a1aa;
  margin: 24px 0 16px;
}

.hint strong {
  color: #f5f5f5;
}

.from-path {
  color: #71717a;
  font-size: 13px;
  margin: 0 0 24px;
}

.from-path code {
  background: rgba(255, 255, 255, 0.06);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: "IBM Plex Mono", monospace;
}

.actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 16px;
  flex-wrap: wrap;
}

.btn-primary,
.btn-secondary {
  padding: 10px 20px;
  border-radius: 8px;
  border: none;
  font-weight: 600;
  cursor: pointer;
  font-size: 14px;
  transition: transform 0.1s ease;
}

.btn-primary {
  background: #f5a623;
  color: #111110;
}

.btn-primary:hover {
  transform: translateY(-1px);
}

.btn-secondary {
  background: transparent;
  color: #2dd4bf;
  border: 1px solid rgba(45, 212, 191, 0.4);
}

.btn-secondary:hover {
  background: rgba(45, 212, 191, 0.08);
}
</style>
