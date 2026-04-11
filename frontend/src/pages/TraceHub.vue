<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useCapabilities, hasCap } from "../lib/capabilities";

const { t, tm, rt } = useI18n();
import UInfoTooltip from "../components/ui/UInfoTooltip.vue";
import Events from "./Events.vue";
import Effects from "./Effects.vue";

const caps = useCapabilities();
const capsReady = computed(() => caps.status === "ready");
const canReadEvents = computed(() => hasCap("events.read"));
const canReadEffects = computed(() => hasCap("effects.read"));

const activeTab = ref<"events" | "effects">("events");

function capsStatusMessage(): string {
  if (caps.status === "loading") return t("caps.loading");
  if (caps.status === "error") return `${t("caps.error")}: ${caps.error ?? t("common.unknown")}`;
  return t("caps.unavailable");
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div class="flex items-center">
        <h2>{{ t('pages.traceHub.title') }}</h2>
        <UInfoTooltip :title="t('infoTooltips.traceHub.title')" :items="tm('infoTooltips.traceHub.items').map((i: any) => rt(i))" />
      </div>
    </div>

    <p v-if="caps.status === 'unavailable'" class="muted">{{ t('caps.unavailable') }}</p>
    <p v-else-if="caps.status === 'loading'" class="muted">{{ t('caps.loading') }}</p>
    <p v-else-if="caps.status === 'error'" class="error">{{ t('caps.error') }}: {{ caps.error }}</p>

    <div v-else class="card">
      <div class="form-row">
        <button class="btn secondary" :disabled="!capsReady" @click="activeTab = 'events'">{{ t('traceHub.tabEvents') }}</button>
        <button class="btn secondary" :disabled="!capsReady" @click="activeTab = 'effects'">{{ t('traceHub.tabEffects') }}</button>
      </div>

      <div v-if="activeTab === 'events'">
        <div v-if="!capsReady" class="muted">{{ capsStatusMessage() }}</div>
        <div v-else-if="!canReadEvents" class="muted">{{ t('traceHub.missingEvents') }}</div>
        <Events v-else />
      </div>

      <div v-else>
        <div v-if="!capsReady" class="muted">{{ capsStatusMessage() }}</div>
        <div v-else-if="!canReadEffects" class="muted">{{ t('traceHub.missingEffects') }}</div>
        <Effects v-else />
      </div>
    </div>
  </div>
</template>
