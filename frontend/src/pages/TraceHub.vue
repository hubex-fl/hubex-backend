<script setup lang="ts">
import { computed, ref } from "vue";
import { useCapabilities, hasCap } from "../lib/capabilities";
import GateBanner from "../components/GateBanner.vue";
import Events from "./Events.vue";
import Effects from "./Effects.vue";

const caps = useCapabilities();
const capsReady = computed(() => caps.status === "ready");
const canReadEvents = computed(() => hasCap("events.read"));
const canReadEffects = computed(() => hasCap("effects.read"));

const activeTab = ref<"events" | "effects">("events");

function capsStatusMessage(): string {
  if (caps.status === "loading") return "Capabilities loading.";
  if (caps.status === "error") return `Capabilities error: ${caps.error ?? "unknown"}`;
  return "Capabilities unavailable";
}

</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>Trace Hub (read-only)</h2>
    </div>

    <GateBanner
      v-if="caps.status !== 'ready'"
      :status="caps.status"
      :message="capsStatusMessage()"
    />

    <div v-else class="card">
      <div class="form-row">
        <button class="btn secondary" :disabled="!capsReady" @click="activeTab = 'events'">Events</button>
        <button class="btn secondary" :disabled="!capsReady" @click="activeTab = 'effects'">Effects</button>
      </div>

      <div v-if="activeTab === 'events'">
        <div v-if="!canReadEvents" class="muted">Missing capability: events.read</div>
        <Events v-else />
      </div>

      <div v-else>
        <div v-if="!canReadEffects" class="muted">Missing capability: effects.read</div>
        <Effects v-else />
      </div>
    </div>
  </div>
</template>
