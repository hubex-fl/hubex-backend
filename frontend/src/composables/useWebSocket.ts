/**
 * useWebSocket — singleton composable for the user-level WebSocket connection.
 *
 * Connects to /api/v1/ws?token=JWT and handles:
 * - Auto-reconnect with exponential backoff
 * - Channel-based event routing
 * - Notification delivery
 */
import { ref, computed, onUnmounted } from "vue";
import { getToken } from "../lib/api";

export type WsMessageType = "connected" | "ping" | "notification" | "event";

export interface WsNotification {
  id: number;
  type: string;
  severity: string;
  title: string;
  message: string;
  entity_ref: string | null;
  created_at: string;
  read_at: string | null;
}

export interface WsMessage {
  type: WsMessageType;
  user_id?: number;
  channel?: string;
  data?: WsNotification | Record<string, unknown>;
}

type NotificationHandler = (n: WsNotification) => void;
type EventHandler = (channel: string, data: Record<string, unknown>) => void;

// ---- Module-level singleton state ----
const isConnected = ref(false);
const lastError = ref<string | null>(null);
const notificationHandlers = new Set<NotificationHandler>();
const eventHandlers = new Set<EventHandler>();

let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectDelay = 1000;
let intentionalClose = false;

function getWsUrl(): string {
  const token = getToken();
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  // Use the backend port 8000 for WS
  const host = window.location.hostname;
  return `${protocol}://${host}:8000/api/v1/ws?token=${token}`;
}

function connect(): void {
  if (!getToken()) return;
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

  intentionalClose = false;
  const url = getWsUrl();
  ws = new WebSocket(url);

  ws.onopen = () => {
    isConnected.value = true;
    lastError.value = null;
    reconnectDelay = 1000; // reset backoff
  };

  ws.onmessage = (event: MessageEvent) => {
    try {
      const msg: WsMessage = JSON.parse(event.data as string);
      if (msg.type === "notification" && msg.data) {
        notificationHandlers.forEach((h) => h(msg.data as WsNotification));
      } else if (msg.type === "event" && msg.channel && msg.data) {
        eventHandlers.forEach((h) => h(msg.channel!, msg.data as Record<string, unknown>));
      }
    } catch {
      // ignore parse errors
    }
  };

  ws.onerror = () => {
    lastError.value = "WebSocket error";
  };

  ws.onclose = () => {
    isConnected.value = false;
    ws = null;
    if (!intentionalClose) {
      scheduleReconnect();
    }
  };
}

function scheduleReconnect(): void {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(() => {
    reconnectDelay = Math.min(reconnectDelay * 1.5, 30000);
    connect();
  }, reconnectDelay);
}

function disconnect(): void {
  intentionalClose = true;
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (ws) {
    ws.close();
    ws = null;
  }
  isConnected.value = false;
}

// ---- Exported composable ----
export function useWebSocket() {
  function start(): void {
    connect();
  }

  function stop(): void {
    disconnect();
  }

  function onNotification(handler: NotificationHandler): () => void {
    notificationHandlers.add(handler);
    return () => notificationHandlers.delete(handler);
  }

  function onEvent(handler: EventHandler): () => void {
    eventHandlers.add(handler);
    return () => eventHandlers.delete(handler);
  }

  return {
    isConnected: computed(() => isConnected.value),
    lastError: computed(() => lastError.value),
    start,
    stop,
    onNotification,
    onEvent,
  };
}
