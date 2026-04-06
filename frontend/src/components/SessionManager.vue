<script setup lang="ts">
import { ref, onMounted } from "vue";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";

const toast = useToastStore();

type SessionOut = {
  id: number;
  user_agent: string | null;
  ip_address: string | null;
  created_at: string;
  expires_at: string;
  is_current: boolean;
};

const sessions = ref<SessionOut[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

async function loadSessions() {
  loading.value = true;
  error.value = null;
  try {
    sessions.value = await apiFetch<SessionOut[]>("/api/v1/auth/sessions");
  } catch {
    error.value = "Failed to load sessions";
  } finally {
    loading.value = false;
  }
}

async function revokeSession(id: number) {
  const session = sessions.value.find(s => s.id === id);
  const browser = session ? parseBrowser(session.user_agent) : "Unknown";
  const ip = session?.ip_address || "unknown IP";
  if (!confirm(`Sign out "${browser}" (${ip})? This device will need to log in again.`)) return;
  try {
    await apiFetch(`/api/v1/auth/sessions/${id}`, { method: "DELETE" });
    toast.addToast("Session revoked", "success");
    await loadSessions();
  } catch {
    toast.addToast("Failed to revoke session", "error");
  }
}

async function revokeAll() {
  const otherCount = sessions.value.filter(s => !s.is_current).length;
  if (!confirm(`Sign out ${otherCount} other session${otherCount !== 1 ? 's' : ''}? Only your current session stays active.`)) return;
  try {
    await apiFetch("/api/v1/auth/sessions", { method: "DELETE" });
    toast.addToast("All other sessions revoked", "success");
    await loadSessions();
  } catch {
    toast.addToast("Failed to revoke sessions", "error");
  }
}

function parseBrowser(ua: string | null): string {
  if (!ua) return "Unknown";
  if (ua.includes("Firefox")) return "Firefox";
  if (ua.includes("Edg/")) return "Edge";
  if (ua.includes("Chrome")) return "Chrome";
  if (ua.includes("Safari")) return "Safari";
  return "Browser";
}

function relativeTime(dt: string): string {
  const diff = Date.now() - new Date(dt).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

onMounted(loadSessions);
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <div>
        <h3 class="text-sm font-semibold text-[var(--text-primary)]">Active Sessions</h3>
        <p class="text-xs text-[var(--text-muted)]">Manage where you're logged in</p>
      </div>
      <button
        v-if="sessions.length > 1"
        class="px-3 py-1.5 rounded-lg text-xs font-medium text-red-400 hover:bg-red-500/10 border border-red-500/30 transition-colors"
        @click="revokeAll"
      >
        Revoke All Others
      </button>
    </div>

    <div v-if="error" class="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-xs text-red-400">
      {{ error }}
    </div>

    <div v-if="loading" class="text-xs text-[var(--text-muted)]">Loading...</div>

    <div v-else-if="sessions.length" class="space-y-2">
      <div
        v-for="session in sessions"
        :key="session.id"
        :class="[
          'flex items-center gap-3 px-4 py-3 rounded-lg border transition-colors',
          session.is_current
            ? 'border-[var(--primary)]/30 bg-[var(--primary)]/5'
            : 'border-[var(--border)] bg-[var(--bg-raised)]',
        ]"
      >
        <div class="h-8 w-8 rounded-full bg-[var(--bg-base)] border border-[var(--border)] flex items-center justify-center shrink-0">
          <svg class="h-4 w-4 text-[var(--text-muted)]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25A2.25 2.25 0 015.25 3h13.5A2.25 2.25 0 0121 5.25z" />
          </svg>
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="text-xs font-medium text-[var(--text-primary)]">{{ parseBrowser(session.user_agent) }}</span>
            <span v-if="session.is_current" class="text-[10px] px-1.5 py-0.5 rounded bg-[var(--primary)]/20 text-[var(--primary)] font-medium">Current</span>
          </div>
          <div class="flex items-center gap-3 mt-0.5 text-[10px] text-[var(--text-muted)]">
            <span v-if="session.ip_address">{{ session.ip_address }}</span>
            <span>{{ relativeTime(session.created_at) }}</span>
          </div>
        </div>
        <button
          v-if="!session.is_current"
          class="px-2.5 py-1 rounded-lg text-xs font-medium text-[var(--text-muted)] hover:text-red-400 hover:bg-red-500/10 transition-colors"
          @click="revokeSession(session.id)"
        >
          Revoke
        </button>
      </div>
    </div>

    <div v-else class="text-center py-6">
      <p class="text-xs text-[var(--text-muted)]">No active sessions</p>
    </div>
  </div>
</template>
