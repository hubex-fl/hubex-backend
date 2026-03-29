<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from "vue";
import {
  type NotificationItem,
  fetchNotifications,
  fetchUnreadCount,
  markRead,
  markAllRead,
  deleteNotification,
  severityColor,
} from "../lib/notifications";
import { useWebSocket, type WsNotification } from "../composables/useWebSocket";

const isOpen = ref(false);
const notifications = ref<NotificationItem[]>([]);
const unreadCount = ref(0);
const loading = ref(false);

const { onNotification } = useWebSocket();

// Handle incoming WS notifications
const removeHandler = onNotification((n: WsNotification) => {
  // Prepend to list
  const item: NotificationItem = {
    id: n.id,
    type: n.type,
    severity: n.severity as NotificationItem["severity"],
    title: n.title,
    message: n.message,
    entity_ref: n.entity_ref,
    read_at: n.read_at,
    created_at: n.created_at,
  };
  notifications.value.unshift(item);
  unreadCount.value++;
});

onUnmounted(() => {
  removeHandler();
  document.removeEventListener("mousedown", handleOutside);
});

async function loadNotifications() {
  loading.value = true;
  try {
    [notifications.value, unreadCount.value] = await Promise.all([
      fetchNotifications(false, 50),
      fetchUnreadCount(),
    ]);
  } finally {
    loading.value = false;
  }
}

function toggleOpen() {
  isOpen.value = !isOpen.value;
  if (isOpen.value) {
    loadNotifications();
    document.addEventListener("mousedown", handleOutside);
  } else {
    document.removeEventListener("mousedown", handleOutside);
  }
}

const bellRef = ref<HTMLElement | null>(null);
function handleOutside(e: MouseEvent) {
  if (bellRef.value && !bellRef.value.contains(e.target as Node)) {
    isOpen.value = false;
    document.removeEventListener("mousedown", handleOutside);
  }
}

async function handleMarkRead(n: NotificationItem) {
  if (n.read_at) return;
  await markRead(n.id);
  n.read_at = new Date().toISOString();
  unreadCount.value = Math.max(0, unreadCount.value - 1);
}

async function handleMarkAll() {
  await markAllRead();
  notifications.value.forEach((n) => {
    if (!n.read_at) n.read_at = new Date().toISOString();
  });
  unreadCount.value = 0;
}

async function handleDelete(n: NotificationItem) {
  await deleteNotification(n.id);
  const idx = notifications.value.indexOf(n);
  if (idx > -1) {
    if (!n.read_at) unreadCount.value = Math.max(0, unreadCount.value - 1);
    notifications.value.splice(idx, 1);
  }
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffM = Math.floor(diffMs / 60000);
  if (diffM < 1) return "just now";
  if (diffM < 60) return `${diffM}m ago`;
  const diffH = Math.floor(diffM / 60);
  if (diffH < 24) return `${diffH}h ago`;
  const diffD = Math.floor(diffH / 24);
  return `${diffD}d ago`;
}

onMounted(async () => {
  try {
    unreadCount.value = await fetchUnreadCount();
  } catch {
    // ignore
  }
});
</script>

<template>
  <div ref="bellRef" class="relative">
    <!-- Bell Button -->
    <button
      class="relative p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
      :title="unreadCount > 0 ? `${unreadCount} unread notifications` : 'Notifications'"
      @click="toggleOpen"
    >
      <!-- Bell icon -->
      <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
      </svg>
      <!-- Unread badge -->
      <span
        v-if="unreadCount > 0"
        class="absolute top-1 right-1 min-w-[16px] h-4 px-0.5 rounded-full text-[9px] font-bold flex items-center justify-center bg-[var(--status-bad)] text-white leading-none"
      >
        {{ unreadCount > 99 ? "99+" : unreadCount }}
      </span>
    </button>

    <!-- Dropdown Panel -->
    <Transition name="notif-drop">
      <div
        v-if="isOpen"
        class="absolute right-0 top-full mt-1 w-80 rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] shadow-2xl overflow-hidden z-50"
      >
        <!-- Header -->
        <div class="flex items-center justify-between px-4 py-3 border-b border-[var(--border)]">
          <div class="flex items-center gap-2">
            <span class="text-sm font-semibold text-[var(--text-primary)]">Notifications</span>
            <span
              v-if="unreadCount > 0"
              class="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-[var(--status-bad)]/15 text-[var(--status-bad)]"
            >
              {{ unreadCount }} new
            </span>
          </div>
          <button
            v-if="unreadCount > 0"
            class="text-xs text-[var(--primary)] hover:underline"
            @click="handleMarkAll"
          >
            Mark all read
          </button>
        </div>

        <!-- Body -->
        <div class="max-h-80 overflow-y-auto">
          <!-- Loading -->
          <div v-if="loading" class="p-6 text-center text-sm text-[var(--text-muted)]">
            Loading…
          </div>

          <!-- Empty -->
          <div v-else-if="notifications.length === 0" class="p-6 text-center">
            <svg class="h-8 w-8 mx-auto mb-2 text-[var(--text-muted)] opacity-40" fill="none" stroke="currentColor" stroke-width="1" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
            </svg>
            <p class="text-sm text-[var(--text-muted)]">No notifications yet</p>
          </div>

          <!-- List -->
          <template v-else>
            <div
              v-for="n in notifications"
              :key="n.id"
              :class="[
                'group px-4 py-3 border-b border-[var(--border)] last:border-0 cursor-pointer transition-colors',
                n.read_at ? 'opacity-60' : 'bg-[var(--bg-raised)]/30 hover:bg-[var(--bg-raised)]',
                !n.read_at && 'hover:bg-[var(--bg-raised)]',
              ]"
              @click="handleMarkRead(n)"
            >
              <div class="flex items-start gap-2.5">
                <!-- Severity dot -->
                <div
                  class="mt-1 h-2 w-2 rounded-full shrink-0"
                  :style="{ background: severityColor(n.severity) }"
                />
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-[var(--text-primary)] truncate">{{ n.title }}</p>
                  <p v-if="n.message" class="text-xs text-[var(--text-muted)] line-clamp-2 mt-0.5">{{ n.message }}</p>
                  <p class="text-[10px] text-[var(--text-muted)] mt-1">{{ formatTime(n.created_at) }}</p>
                </div>
                <!-- Delete button -->
                <button
                  class="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-[var(--bg-raised)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-opacity shrink-0"
                  @click.stop="handleDelete(n)"
                  title="Dismiss"
                >
                  <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          </template>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.notif-drop-enter-active,
.notif-drop-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.notif-drop-enter-from,
.notif-drop-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.97);
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
