<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { apiFetch } from "../lib/api";
import UInfoTooltip from "../components/ui/UInfoTooltip.vue";

const { t, tm, rt } = useI18n();
const router = useRouter();

// ── Raw API data types ─────────────────────────────────────────────────────

interface ApiDevice {
  id: number;
  device_uid: string;
  name: string | null;
  category?: string;
}

interface ApiVariable {
  key: string;
  scope: string;
  value_type: string;
  description: string | null;
  unit: string | null;
}

interface ApiAutomation {
  id: number;
  name: string;
  description: string | null;
  enabled: boolean;
  trigger_type: string;
  trigger_config: Record<string, unknown>;
  action_type: string;
  action_config: Record<string, unknown>;
}

interface ApiAlertRule {
  id: number;
  name: string;
  condition_type: string;
  condition_config: Record<string, unknown>;
  entity_id: string | null;
  severity: string;
  enabled: boolean;
}

interface ApiWebhook {
  id: number;
  url: string;
  event_filter: string[];
  active: boolean;
}

// ── Flow node type ─────────────────────────────────────────────────────────

type NodeType = "device" | "variable" | "automation" | "alert" | "webhook";

interface FlowNode {
  id: string;
  type: NodeType;
  label: string;
  sublabel: string;
  x: number;
  y: number;
  column: number;
  route?: string;
  enabled?: boolean;
  meta?: Record<string, unknown>;
}

interface FlowEdge {
  id: string;
  from: string;
  to: string;
  label?: string;
  type: "data" | "trigger" | "action" | "monitor";
}

// ── State ──────────────────────────────────────────────────────────────────

const nodes = ref<FlowNode[]>([]);
const edges = ref<FlowEdge[]>([]);
const selectedNode = ref<FlowNode | null>(null);
const hoveredNode = ref<string | null>(null);
const loading = ref(true);
const searchQuery = ref("");
const zoom = ref(1);
const pan = ref({ x: 0, y: 0 });
const isPanning = ref(false);
const panStart = ref({ x: 0, y: 0 });
const canvasRef = ref<HTMLElement | null>(null);

// Stats
const stats = ref({ devices: 0, variables: 0, automations: 0, alerts: 0, webhooks: 0 });

// ── Legend toggle ──────────────────────────────────────────────────────────

const showLegend = ref(false);

// ── Colors & Icons ─────────────────────────────────────────────────────────

const NODE_COLORS: Record<NodeType, string> = {
  device: "#F5A623",
  variable: "#2DD4BF",
  automation: "#3b82f6",
  alert: "#ef4444",
  webhook: "#8b5cf6",
};

const NODE_BG: Record<NodeType, string> = {
  device: "rgba(245,166,35,0.08)",
  variable: "rgba(45,212,191,0.08)",
  automation: "rgba(59,130,246,0.08)",
  alert: "rgba(239,68,68,0.08)",
  webhook: "rgba(139,92,246,0.08)",
};

const EDGE_COLORS: Record<string, string> = {
  data: "#2DD4BF",
  trigger: "#ef4444",
  action: "#3b82f6",
  monitor: "#F5A623",
};

const NODE_LABELS: Record<NodeType, string> = {
  device: "Device",
  variable: "Variable",
  automation: "Automation",
  alert: "Alert Rule",
  webhook: "Webhook",
};

// ── Layout constants ───────────────────────────────────────────────────────

const COL_X = [60, 300, 560, 820]; // 4 columns
const NODE_W = 180;
const NODE_H_DEVICE = 50;
const NODE_H_SMALL = 42;
const ROW_GAP = 16;
const COL_START_Y = 60;

// ── Computed ───────────────────────────────────────────────────────────────

const visibleNodes = computed(() => {
  if (!searchQuery.value) return nodes.value;
  const q = searchQuery.value.toLowerCase();
  return nodes.value.filter(
    (n) => n.label.toLowerCase().includes(q) || n.type.includes(q) || n.sublabel.toLowerCase().includes(q)
  );
});

const visibleEdges = computed(() => {
  const visibleIds = new Set(visibleNodes.value.map((n) => n.id));
  return edges.value.filter((e) => visibleIds.has(e.from) && visibleIds.has(e.to));
});

const highlightedEdges = computed(() => {
  if (!hoveredNode.value && !selectedNode.value) return new Set<string>();
  const nodeId = hoveredNode.value || selectedNode.value?.id;
  return new Set(
    edges.value
      .filter((e) => e.from === nodeId || e.to === nodeId)
      .map((e) => e.id)
  );
});

const highlightedNodes = computed(() => {
  if (!hoveredNode.value && !selectedNode.value) return new Set<string>();
  const nodeId = hoveredNode.value || selectedNode.value?.id;
  const connectedEdges = edges.value.filter((e) => e.from === nodeId || e.to === nodeId);
  const ids = new Set<string>();
  if (nodeId) ids.add(nodeId);
  for (const e of connectedEdges) {
    ids.add(e.from);
    ids.add(e.to);
  }
  return ids;
});

// ── Load system graph ──────────────────────────────────────────────────────

async function loadSystemGraph() {
  loading.value = true;
  try {
    const [devRes, varRes, autoRes, alertRes, whRes] = await Promise.allSettled([
      apiFetch<ApiDevice[]>("/api/v1/devices"),
      apiFetch<ApiVariable[]>("/api/v1/variables/definitions"),
      apiFetch<ApiAutomation[]>("/api/v1/automations"),
      apiFetch<ApiAlertRule[]>("/api/v1/alerts/rules"),
      apiFetch<ApiWebhook[]>("/api/v1/webhooks"),
    ]);

    const devices = devRes.status === "fulfilled" ? devRes.value : [];
    const variables = varRes.status === "fulfilled" ? varRes.value : [];
    const automations = autoRes.status === "fulfilled" ? autoRes.value : [];
    const alertRules = alertRes.status === "fulfilled" ? alertRes.value : [];
    const webhooks = whRes.status === "fulfilled" ? whRes.value : [];

    stats.value = {
      devices: devices.length,
      variables: variables.length,
      automations: automations.length,
      alerts: alertRules.length,
      webhooks: webhooks.length,
    };

    const newNodes: FlowNode[] = [];
    const newEdges: FlowEdge[] = [];

    // ── Column 1: Devices ──────────────────────────────────────────────
    let y = COL_START_Y;
    for (const d of devices) {
      newNodes.push({
        id: `device-${d.id}`,
        type: "device",
        label: d.name || d.device_uid,
        sublabel: d.device_uid,
        x: COL_X[0],
        y,
        column: 0,
        route: `/devices/${d.id}`,
        meta: { device_id: d.id, category: d.category },
      });
      y += NODE_H_DEVICE + ROW_GAP;
    }

    // ── Column 2: Variables ────────────────────────────────────────────
    y = COL_START_Y;
    for (const v of variables) {
      const nodeId = `var-${v.key}`;
      newNodes.push({
        id: nodeId,
        type: "variable",
        label: v.key,
        sublabel: `${v.value_type}${v.unit ? " (" + v.unit + ")" : ""} | ${v.scope}`,
        x: COL_X[1],
        y,
        column: 1,
        route: "/variables",
        meta: { scope: v.scope, value_type: v.value_type },
      });
      y += NODE_H_SMALL + ROW_GAP;

      // Connect device-scoped variables to ALL devices (they belong to each device)
      if (v.scope === "device") {
        for (const d of devices) {
          newEdges.push({
            id: `edge-dev-var-${d.id}-${v.key}`,
            from: `device-${d.id}`,
            to: nodeId,
            type: "data",
          });
        }
      }
    }

    // ── Column 3: Automations + Alert Rules ────────────────────────────
    y = COL_START_Y;

    for (const a of automations) {
      const autoNodeId = `auto-${a.id}`;
      newNodes.push({
        id: autoNodeId,
        type: "automation",
        label: a.name,
        sublabel: `${a.trigger_type} -> ${a.action_type}`,
        x: COL_X[2],
        y,
        column: 2,
        route: "/automations",
        enabled: a.enabled,
        meta: {
          trigger_type: a.trigger_type,
          action_type: a.action_type,
          trigger_config: a.trigger_config,
          action_config: a.action_config,
        },
      });
      y += NODE_H_SMALL + ROW_GAP;

      // Connect automation triggers to variables
      const triggerVarKey = a.trigger_config?.variable_key as string | undefined;
      if (triggerVarKey && (a.trigger_type === "variable_threshold" || a.trigger_type === "variable_change" || a.trigger_type === "variable_geofence")) {
        const varNodeId = `var-${triggerVarKey}`;
        if (newNodes.some((n) => n.id === varNodeId)) {
          newEdges.push({
            id: `edge-var-auto-${a.id}`,
            from: varNodeId,
            to: autoNodeId,
            label: a.trigger_type.replace("variable_", ""),
            type: "trigger",
          });
        }
      }

      // Connect device triggers to devices
      if (a.trigger_type === "device_offline" || a.trigger_type === "device_online") {
        const devId = a.trigger_config?.device_id as number | undefined;
        if (devId) {
          const devNodeId = `device-${devId}`;
          if (newNodes.some((n) => n.id === devNodeId)) {
            newEdges.push({
              id: `edge-dev-auto-${a.id}`,
              from: devNodeId,
              to: autoNodeId,
              label: a.trigger_type.replace("device_", ""),
              type: "trigger",
            });
          }
        } else {
          // All devices
          for (const d of devices) {
            newEdges.push({
              id: `edge-dev-auto-${d.id}-${a.id}`,
              from: `device-${d.id}`,
              to: autoNodeId,
              label: a.trigger_type.replace("device_", ""),
              type: "trigger",
            });
          }
        }
      }

      // Connect automation actions to webhooks
      if (a.action_type === "call_webhook") {
        const webhookUrl = a.action_config?.url as string | undefined;
        if (webhookUrl) {
          const matchingWebhook = webhooks.find((w) => w.url === webhookUrl);
          if (matchingWebhook) {
            newEdges.push({
              id: `edge-auto-wh-${a.id}-${matchingWebhook.id}`,
              from: autoNodeId,
              to: `webhook-${matchingWebhook.id}`,
              type: "action",
            });
          }
        }
      }

      // Connect automation actions to variables (set_variable)
      if (a.action_type === "set_variable") {
        const targetKey = a.action_config?.variable_key as string | undefined;
        if (targetKey) {
          const targetNodeId = `var-${targetKey}`;
          if (newNodes.some((n) => n.id === targetNodeId)) {
            newEdges.push({
              id: `edge-auto-setvar-${a.id}`,
              from: autoNodeId,
              to: targetNodeId,
              label: "set",
              type: "action",
            });
          }
        }
      }
    }

    // Alert rules (same column, below automations)
    y += 20; // gap between sections
    for (const ar of alertRules) {
      const alertNodeId = `alert-${ar.id}`;
      newNodes.push({
        id: alertNodeId,
        type: "alert",
        label: ar.name,
        sublabel: `${ar.condition_type} | ${ar.severity}`,
        x: COL_X[2],
        y,
        column: 2,
        route: "/alerts",
        enabled: ar.enabled,
        meta: { severity: ar.severity, condition_type: ar.condition_type },
      });
      y += NODE_H_SMALL + ROW_GAP;

      // Connect alert rules to variables they monitor
      if (ar.condition_type === "variable_threshold") {
        const varKey = ar.condition_config?.variable_key as string | undefined;
        if (varKey) {
          const varNodeId = `var-${varKey}`;
          if (newNodes.some((n) => n.id === varNodeId)) {
            newEdges.push({
              id: `edge-var-alert-${ar.id}`,
              from: varNodeId,
              to: alertNodeId,
              label: "monitors",
              type: "monitor",
            });
          }
        }
      }

      // Connect device-related alert rules to devices
      if (ar.condition_type === "device_offline" || ar.condition_type === "entity_health") {
        if (ar.entity_id) {
          // Try to match entity_id to a device
          const matchDevice = devices.find(
            (d) => d.device_uid === ar.entity_id || String(d.id) === ar.entity_id
          );
          if (matchDevice) {
            newEdges.push({
              id: `edge-dev-alert-${ar.id}`,
              from: `device-${matchDevice.id}`,
              to: alertNodeId,
              label: ar.condition_type.replace("_", " "),
              type: "monitor",
            });
          }
        } else {
          // All devices
          for (const d of devices) {
            newEdges.push({
              id: `edge-dev-alert-${d.id}-${ar.id}`,
              from: `device-${d.id}`,
              to: alertNodeId,
              type: "monitor",
            });
          }
        }
      }
    }

    // ── Column 4: Webhooks ─────────────────────────────────────────────
    y = COL_START_Y;
    for (const wh of webhooks) {
      newNodes.push({
        id: `webhook-${wh.id}`,
        type: "webhook",
        label: truncateUrl(wh.url),
        sublabel: wh.event_filter.length ? wh.event_filter.join(", ") : "all events",
        x: COL_X[3],
        y,
        column: 3,
        route: "/webhooks",
        enabled: wh.active,
        meta: { url: wh.url },
      });
      y += NODE_H_SMALL + ROW_GAP;
    }

    nodes.value = newNodes;
    edges.value = newEdges;
  } catch {
    // Empty canvas on failure
  } finally {
    loading.value = false;
  }
}

function truncateUrl(url: string): string {
  try {
    const u = new URL(url);
    const path = u.pathname.length > 20 ? u.pathname.slice(0, 20) + "..." : u.pathname;
    return u.hostname + path;
  } catch {
    return url.length > 30 ? url.slice(0, 30) + "..." : url;
  }
}

// ── Node interaction ───────────────────────────────────────────────────────

function selectNode(node: FlowNode) {
  selectedNode.value = selectedNode.value?.id === node.id ? null : node;
}

function navigateToNode(node: FlowNode) {
  if (node.route) {
    router.push(node.route);
  }
}

function getNodeHeight(type: NodeType): number {
  return type === "device" ? NODE_H_DEVICE : NODE_H_SMALL;
}

// ── Edge path calculation (smooth curves) ──────────────────────────────────

function getEdgePath(edge: FlowEdge): string {
  const fromNode = nodes.value.find((n) => n.id === edge.from);
  const toNode = nodes.value.find((n) => n.id === edge.to);
  if (!fromNode || !toNode) return "";

  const fromH = getNodeHeight(fromNode.type);
  const toH = getNodeHeight(toNode.type);

  // Right side of from-node
  const x1 = fromNode.x + NODE_W;
  const y1 = fromNode.y + fromH / 2;

  // Left side of to-node
  const x2 = toNode.x;
  const y2 = toNode.y + toH / 2;

  // If same column or to is left of from, draw differently
  if (toNode.column <= fromNode.column) {
    // Curve around
    const midX = Math.min(x1, x2) - 40;
    return `M${x1},${y1} C${x1 + 40},${y1} ${midX},${y2} ${x2},${y2}`;
  }

  // Normal left-to-right bezier
  const dx = Math.abs(x2 - x1);
  const cpOffset = Math.min(dx * 0.4, 80);
  return `M${x1},${y1} C${x1 + cpOffset},${y1} ${x2 - cpOffset},${y2} ${x2},${y2}`;
}

// ── Zoom & Pan ─────────────────────────────────────────────────────────────

function zoomIn() {
  zoom.value = Math.min(zoom.value + 0.15, 2.5);
}
function zoomOut() {
  zoom.value = Math.max(zoom.value - 0.15, 0.3);
}
function zoomReset() {
  zoom.value = 1;
  pan.value = { x: 0, y: 0 };
}

function onWheel(e: WheelEvent) {
  e.preventDefault();
  const delta = e.deltaY > 0 ? -0.08 : 0.08;
  zoom.value = Math.max(0.3, Math.min(2.5, zoom.value + delta));
}

function startPan(e: MouseEvent) {
  if (e.target === canvasRef.value || (e.target as HTMLElement)?.closest?.(".canvas-bg")) {
    isPanning.value = true;
    panStart.value = { x: e.clientX - pan.value.x, y: e.clientY - pan.value.y };
  }
}

function onPanMove(e: MouseEvent) {
  if (isPanning.value) {
    pan.value = { x: e.clientX - panStart.value.x, y: e.clientY - panStart.value.y };
  }
}

function stopPan() {
  isPanning.value = false;
}

function fitToView() {
  if (!nodes.value.length) return;
  const minX = Math.min(...nodes.value.map((n) => n.x));
  const maxX = Math.max(...nodes.value.map((n) => n.x + NODE_W));
  const minY = Math.min(...nodes.value.map((n) => n.y));
  const maxY = Math.max(...nodes.value.map((n) => n.y + getNodeHeight(n.type)));

  const canvas = canvasRef.value;
  if (!canvas) return;

  const cw = canvas.clientWidth;
  const ch = canvas.clientHeight;
  const contentW = maxX - minX + 80;
  const contentH = maxY - minY + 80;

  const scaleX = cw / contentW;
  const scaleY = ch / contentH;
  zoom.value = Math.max(0.3, Math.min(1.2, Math.min(scaleX, scaleY)));

  pan.value = {
    x: (cw - contentW * zoom.value) / 2 - minX * zoom.value + 40 * zoom.value,
    y: (ch - contentH * zoom.value) / 2 - minY * zoom.value + 40 * zoom.value,
  };
}

// ── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(async () => {
  await loadSystemGraph();
  await nextTick();
  fitToView();
});

// Column headers
const columnHeaders = computed(() => [
  { label: t("pages.flowEditor.colDevices"), count: stats.value.devices, color: NODE_COLORS.device },
  { label: t("pages.flowEditor.colVariables"), count: stats.value.variables, color: NODE_COLORS.variable },
  { label: t("pages.flowEditor.colLogic"), count: stats.value.automations + stats.value.alerts, color: NODE_COLORS.automation },
  { label: t("pages.flowEditor.colOutputs"), count: stats.value.webhooks, color: NODE_COLORS.webhook },
]);
</script>

<template>
  <div class="h-[calc(100vh-60px)] flex flex-col">
    <!-- Toolbar -->
    <div class="flex items-center justify-between px-4 py-2 border-b border-[var(--border)] bg-[var(--bg-surface)]">
      <div class="flex items-center gap-3">
        <h1 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('pages.flowEditor.title') }}</h1>
        <UInfoTooltip :title="t('infoTooltips.flowEditor.title')" :items="tm('infoTooltips.flowEditor.items').map((i: any) => rt(i))" />

        <!-- Stats pills -->
        <div class="flex items-center gap-1.5">
          <span v-for="(s, key) in { D: stats.devices, V: stats.variables, A: stats.automations, R: stats.alerts, W: stats.webhooks }"
            :key="key"
            class="px-1.5 py-0.5 rounded text-[9px] font-mono border border-[var(--border)] text-[var(--text-muted)]"
          >{{ key }}:{{ s }}</span>
        </div>

        <input
          v-model="searchQuery"
          class="px-2 py-0.5 rounded border border-[var(--border)] bg-[var(--bg-base)] text-[10px] w-32 text-[var(--text-primary)]"
          :placeholder="t('pages.flowEditor.searchPlaceholder')"
        />
      </div>

      <div class="flex items-center gap-1.5">
        <!-- Quick nav links -->
        <router-link to="/devices" class="text-[10px] text-[var(--primary)] hover:underline">{{ t('nav.devices') }}</router-link>
        <router-link to="/variables" class="text-[10px] text-[var(--primary)] hover:underline">{{ t('nav.variables') }}</router-link>
        <router-link to="/automations" class="text-[10px] text-[var(--primary)] hover:underline">{{ t('nav.automations') }}</router-link>
        <router-link to="/alerts" class="text-[10px] text-[var(--primary)] hover:underline">{{ t('nav.alerts') }}</router-link>

        <span class="w-px h-4 bg-[var(--border)]" />

        <!-- Legend toggle -->
        <button
          class="px-2 py-1 rounded text-[10px] border border-[var(--border)] hover:bg-[var(--bg-raised)] text-[var(--text-muted)]"
          @click="showLegend = !showLegend"
        >{{ t('pages.flowEditor.legend') }}</button>

        <span class="w-px h-4 bg-[var(--border)]" />

        <!-- Zoom controls -->
        <button class="px-1.5 py-1 rounded text-[10px] font-mono border border-[var(--border)] hover:bg-[var(--bg-raised)] text-[var(--text-primary)]" @click="zoomOut" :title="t('pages.flowEditor.zoomOut')">-</button>
        <span class="text-[10px] text-[var(--text-muted)] w-10 text-center font-mono">{{ Math.round(zoom * 100) }}%</span>
        <button class="px-1.5 py-1 rounded text-[10px] font-mono border border-[var(--border)] hover:bg-[var(--bg-raised)] text-[var(--text-primary)]" @click="zoomIn" :title="t('pages.flowEditor.zoomIn')">+</button>
        <button class="px-2 py-1 rounded text-[10px] border border-[var(--border)] hover:bg-[var(--bg-raised)] text-[var(--text-muted)]" @click="zoomReset">{{ t('pages.flowEditor.resetView') }}</button>
        <button class="px-2 py-1 rounded text-[10px] border border-[var(--border)] hover:bg-[var(--bg-raised)] text-[var(--text-muted)]" @click="fitToView">{{ t('pages.flowEditor.fitView') }}</button>
        <button class="px-2 py-1 rounded text-[10px] border border-[var(--border)] hover:bg-[var(--bg-raised)] text-[var(--text-muted)]" @click="loadSystemGraph().then(fitToView)">{{ t('pages.flowEditor.refresh') }}</button>
      </div>
    </div>

    <!-- Legend overlay -->
    <Transition name="fade">
      <div v-if="showLegend" class="absolute top-14 right-4 z-50 bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg p-3 shadow-xl">
        <p class="text-[10px] font-semibold text-[var(--text-primary)] mb-2">{{ t('pages.flowEditor.legend') }}</p>
        <div class="space-y-1.5">
          <div v-for="(color, type) in NODE_COLORS" :key="type" class="flex items-center gap-2">
            <div class="w-3 h-3 rounded-sm" :style="{ background: color }" />
            <span class="text-[10px] text-[var(--text-muted)]">{{ NODE_LABELS[type as NodeType] }}</span>
          </div>
          <hr class="border-[var(--border)] my-1" />
          <div v-for="(color, type) in EDGE_COLORS" :key="type" class="flex items-center gap-2">
            <div class="w-6 h-0.5" :style="{ background: color }" />
            <span class="text-[10px] text-[var(--text-muted)]">{{ type }}</span>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Canvas -->
    <div
      ref="canvasRef"
      class="flex-1 relative overflow-hidden bg-[var(--bg-base)] canvas-bg"
      :class="{ 'cursor-grab': !isPanning, 'cursor-grabbing': isPanning }"
      @mousedown="startPan"
      @mousemove="onPanMove"
      @mouseup="stopPan"
      @mouseleave="stopPan"
      @wheel.prevent="onWheel"
      style="background-image: radial-gradient(circle, var(--border) 1px, transparent 1px); background-size: 30px 30px;"
    >
      <!-- Loading -->
      <div v-if="loading" class="absolute inset-0 flex items-center justify-center z-10">
        <div class="flex items-center gap-2">
          <div class="w-4 h-4 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
          <span class="text-sm text-[var(--text-muted)]">{{ t('pages.flowEditor.loading') }}</span>
        </div>
      </div>

      <!-- Transformed layer -->
      <div
        v-if="!loading"
        :style="{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transformOrigin: '0 0',
        }"
        class="absolute inset-0"
      >
        <!-- Column headers -->
        <div
          v-for="(col, idx) in columnHeaders"
          :key="idx"
          class="absolute text-center"
          :style="{ left: COL_X[idx] + 'px', top: '15px', width: NODE_W + 'px' }"
        >
          <span class="text-[10px] font-semibold uppercase tracking-wider" :style="{ color: col.color }">
            {{ col.label }}
          </span>
          <span class="text-[9px] text-[var(--text-muted)] ml-1">({{ col.count }})</span>
        </div>

        <!-- SVG Edges -->
        <svg class="absolute inset-0 w-full h-full pointer-events-none" style="z-index: 1; overflow: visible;">
          <defs>
            <marker id="arrowhead-data" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" :fill="EDGE_COLORS.data" opacity="0.7" />
            </marker>
            <marker id="arrowhead-trigger" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" :fill="EDGE_COLORS.trigger" opacity="0.7" />
            </marker>
            <marker id="arrowhead-action" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" :fill="EDGE_COLORS.action" opacity="0.7" />
            </marker>
            <marker id="arrowhead-monitor" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" :fill="EDGE_COLORS.monitor" opacity="0.7" />
            </marker>
          </defs>

          <path
            v-for="edge in visibleEdges"
            :key="edge.id"
            :d="getEdgePath(edge)"
            :stroke="EDGE_COLORS[edge.type] || 'var(--border-hover)'"
            :stroke-width="highlightedEdges.has(edge.id) ? 2.5 : 1.5"
            :opacity="highlightedEdges.size > 0 ? (highlightedEdges.has(edge.id) ? 1 : 0.15) : 0.5"
            fill="none"
            :stroke-dasharray="edge.type === 'monitor' ? '4 3' : 'none'"
            :marker-end="`url(#arrowhead-${edge.type})`"
            class="transition-opacity duration-150"
          />
        </svg>

        <!-- Nodes -->
        <div
          v-for="node in visibleNodes"
          :key="node.id"
          class="absolute rounded-lg border px-3 py-1.5 select-none transition-all duration-150"
          :class="[
            selectedNode?.id === node.id ? 'ring-2 ring-[var(--primary)]/60 shadow-lg' : 'shadow-sm',
            node.enabled === false ? 'opacity-50' : '',
            highlightedNodes.size > 0 && !highlightedNodes.has(node.id) ? 'opacity-20' : '',
          ]"
          :style="{
            left: node.x + 'px',
            top: node.y + 'px',
            width: NODE_W + 'px',
            height: getNodeHeight(node.type) + 'px',
            borderColor: NODE_COLORS[node.type] + '60',
            backgroundColor: NODE_BG[node.type],
            zIndex: selectedNode?.id === node.id ? 10 : 2,
            cursor: 'pointer',
          }"
          @click.stop="selectNode(node)"
          @dblclick.stop="navigateToNode(node)"
          @mouseenter="hoveredNode = node.id"
          @mouseleave="hoveredNode = null"
        >
          <!-- Left color bar -->
          <div
            class="absolute left-0 top-2 bottom-2 w-[3px] rounded-full"
            :style="{ background: NODE_COLORS[node.type] }"
          />

          <div class="flex items-center gap-1.5 ml-2 h-full">
            <!-- Type icon dot -->
            <div
              class="w-2 h-2 rounded-full shrink-0"
              :style="{ background: NODE_COLORS[node.type] }"
            />
            <div class="min-w-0 flex-1">
              <div class="text-[11px] font-medium text-[var(--text-primary)] truncate leading-tight">
                {{ node.label }}
              </div>
              <div class="text-[9px] text-[var(--text-muted)] truncate leading-tight">
                {{ node.sublabel }}
              </div>
            </div>
            <!-- Enabled/disabled indicator -->
            <div v-if="node.enabled !== undefined" class="shrink-0">
              <div
                class="w-1.5 h-1.5 rounded-full"
                :style="{ background: node.enabled ? '#22c55e' : '#6b7280' }"
                :title="node.enabled ? 'enabled' : 'disabled'"
              />
            </div>
          </div>

          <!-- Connection ports -->
          <div
            v-if="node.column < 3"
            class="absolute -right-1 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full border"
            :style="{ borderColor: NODE_COLORS[node.type], background: 'var(--bg-base)' }"
          />
          <div
            v-if="node.column > 0"
            class="absolute -left-1 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full border"
            :style="{ borderColor: NODE_COLORS[node.type], background: 'var(--bg-base)' }"
          />
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="!loading && !nodes.length" class="absolute inset-0 flex items-center justify-center">
        <div class="text-center">
          <p class="text-sm text-[var(--text-muted)]">{{ t('pages.flowEditor.emptyCanvas') }}</p>
          <p class="text-[10px] text-[var(--text-muted)] mt-1">{{ t('pages.flowEditor.emptyHint') }}</p>
        </div>
      </div>
    </div>

    <!-- Inspector panel (bottom) -->
    <Transition name="slide-up">
      <div v-if="selectedNode" class="border-t border-[var(--border)] bg-[var(--bg-surface)] px-4 py-2.5">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-2.5 h-2.5 rounded-sm" :style="{ background: NODE_COLORS[selectedNode.type] }" />
            <div>
              <span class="text-xs font-semibold text-[var(--text-primary)]">{{ selectedNode.label }}</span>
              <span class="text-[10px] text-[var(--text-muted)] ml-2">{{ NODE_LABELS[selectedNode.type] }}</span>
            </div>
            <span class="text-[10px] text-[var(--text-muted)]">{{ selectedNode.sublabel }}</span>
          </div>
          <div class="flex items-center gap-2">
            <button
              v-if="selectedNode.route"
              class="px-2 py-0.5 rounded text-[10px] font-medium text-[var(--primary)] border border-[var(--primary)]/30 hover:bg-[var(--primary)]/10 transition-colors"
              @click="navigateToNode(selectedNode)"
            >{{ t('pages.flowEditor.openDetail') }}</button>
            <button class="text-[10px] text-[var(--text-muted)] hover:text-[var(--text-primary)]" @click="selectedNode = null">
              {{ t('common.close') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.15s ease, opacity 0.15s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(8px);
  opacity: 0;
}
</style>
