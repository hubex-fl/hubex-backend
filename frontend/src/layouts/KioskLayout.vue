<script setup lang="ts">
import { branding } from "../lib/branding";
</script>

<template>
  <div class="min-h-screen bg-[var(--bg-base)] flex flex-col">
    <!-- Minimal header with org logo -->
    <div class="flex items-center justify-between px-4 py-2 border-b border-[var(--border)] bg-[var(--bg-surface)]">
      <div class="flex items-center gap-2">
        <img v-if="branding.logoUrl" :src="branding.logoUrl" :alt="branding.productName" class="h-6" />
        <span v-else class="text-xs font-bold text-[var(--primary)] tracking-widest">{{ branding.productName }}</span>
      </div>
      <span class="text-[10px] text-[var(--text-muted)]">Kiosk Mode</span>
    </div>
    <!-- Full-width content -->
    <main class="flex-1 overflow-auto">
      <router-view />
    </main>
  </div>
</template>
