<script setup lang="ts">
</script>

<template>
  <div class="min-h-screen bg-[var(--bg-base)] flex items-center justify-center p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <div class="inline-flex items-center gap-2 mb-2">
          <svg class="h-7 w-7 text-[var(--primary)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-13.5 0v-1.5m13.5 1.5v-1.5m0 0a3 3 0 00-3-3H7.5a3 3 0 00-3 3m13.5 0v-6.75a3 3 0 00-3-3H7.5a3 3 0 00-3 3v6.75" />
          </svg>
          <span class="text-xl font-bold text-[var(--text-primary)] font-mono tracking-widest">HUBEX</span>
        </div>
        <p class="text-xs text-[var(--text-muted)] tracking-wide uppercase">Mission Control</p>
      </div>
      <slot />
    </div>
  </div>
</template>
