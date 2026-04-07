<script setup lang="ts">
import { ref } from "vue";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";

const toast = useToastStore();
const open = ref(false);
const type = ref<"bug" | "feature" | "other">("bug");
const message = ref("");
const sending = ref(false);

async function submit() {
  if (!message.value.trim()) return;
  sending.value = true;
  try {
    await apiFetch("/api/v1/events/emit", {
      method: "POST",
      body: JSON.stringify({
        type: `feedback.${type.value}`,
        payload: {
          message: message.value.trim(),
          page: window.location.pathname,
          userAgent: navigator.userAgent,
          timestamp: new Date().toISOString(),
        },
      }),
    });
    toast.addToast("Feedback sent — thank you!", "success");
    message.value = "";
    open.value = false;
  } catch {
    // Fallback: open GitHub Issues
    const issueUrl = `https://github.com/hubex-fl/hubex-backend/issues/new?title=${encodeURIComponent(`[${type.value}] ${message.value.slice(0, 60)}`)}&body=${encodeURIComponent(message.value)}`;
    window.open(issueUrl, "_blank");
    toast.addToast("Opening GitHub Issues...", "info");
    open.value = false;
  } finally {
    sending.value = false;
  }
}
</script>

<template>
  <!-- Feedback Button (bottom-right) -->
  <button
    v-if="!open"
    class="fixed bottom-4 right-4 z-40 px-3 py-2 rounded-full bg-[var(--primary)] text-black text-xs font-medium shadow-lg hover:bg-[var(--primary-hover)] transition-all"
    @click="open = true"
  >
    💬 Feedback
  </button>

  <!-- Feedback Panel -->
  <Teleport to="body">
    <div v-if="open" class="fixed bottom-4 right-4 z-50 w-80 bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl shadow-2xl p-4 space-y-3">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-semibold text-[var(--text-primary)]">Send Feedback</h3>
        <button class="text-xs text-[var(--text-muted)]" @click="open = false">×</button>
      </div>

      <div class="flex gap-1.5">
        <button
          v-for="t in [['bug', '🐛 Bug'], ['feature', '💡 Feature'], ['other', '💬 Other']]"
          :key="t[0]"
          :class="['px-2.5 py-1 rounded-lg text-[10px] font-medium transition-colors', type === t[0] ? 'bg-[var(--primary)]/15 text-[var(--primary)] border border-[var(--primary)]/30' : 'text-[var(--text-muted)] border border-[var(--border)]']"
          @click="type = t[0] as any"
        >{{ t[1] }}</button>
      </div>

      <textarea
        v-model="message"
        rows="3"
        class="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs text-[var(--text-primary)] resize-none"
        placeholder="Describe the issue or idea..."
      />

      <div class="flex justify-end gap-2">
        <button class="text-xs text-[var(--text-muted)]" @click="open = false">Cancel</button>
        <button
          :disabled="sending || !message.trim()"
          class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black disabled:opacity-50"
          @click="submit"
        >{{ sending ? 'Sending...' : 'Send' }}</button>
      </div>

      <p class="text-[9px] text-[var(--text-muted)]">
        Or <a href="https://github.com/hubex-fl/hubex-backend/issues" target="_blank" class="text-[var(--primary)] hover:underline">open a GitHub Issue</a>
      </p>
    </div>
  </Teleport>
</template>
