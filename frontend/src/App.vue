<script setup lang="ts">
import { onMounted } from "vue";
import { hasToken } from "./lib/api";
import { refreshCapabilities, useCapabilities, hasCap } from "./lib/capabilities";
import { useAbortHandle } from "./lib/abort";

const caps = useCapabilities();
const { signal } = useAbortHandle();

onMounted(() => {
  refreshCapabilities(signal);
});
</script>

<template>
  <div class="shell">
    <aside class="nav">
      <div class="nav-title">HUBEX</div>
      <router-link v-if="hasCap('entities.read')" to="/system-stage">System Stage</router-link>
      <router-link v-if="hasCap('events.read')" to="/events">Events</router-link>
      <router-link v-if="hasCap('effects.read')" to="/effects">Effects</router-link>
      <router-link v-if="hasCap('events.read') || hasCap('effects.read')" to="/trace-hub">Trace Hub</router-link>
      <router-link
        v-if="hasCap('devices.read') || hasCap('effects.read') || hasCap('events.read') || hasCap('vars.read')"
        to="/observability"
      >
        Observability
      </router-link>
      <router-link to="/settings/auth">Auth</router-link>
      <div class="spacer"></div>
      <div class="nav-status">Token: {{ hasToken() ? 'present' : 'missing' }}</div>
      <div class="nav-status">Caps: {{ caps.status }}</div>
    </aside>
    <main class="content">
      <router-view />
    </main>
  </div>
</template>
