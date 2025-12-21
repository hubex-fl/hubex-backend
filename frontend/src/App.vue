<script setup lang="ts">
import { clearToken, hasToken } from "./lib/api";
import { useRouter } from "vue-router";

const router = useRouter();

function logout() {
  clearToken();
  router.push("/login");
}
</script>

<template>
  <div>
    <nav class="nav">
      <router-link to="/devices">Devices</router-link>
      <router-link to="/pairing">Pairing</router-link>
      <router-link to="/variables">Variables</router-link>
      <div class="spacer"></div>
      <button v-if="hasToken()" class="btn secondary" @click="logout">Logout</button>
    </nav>
    <div class="container">
      <router-view />
    </div>
  </div>
</template>
