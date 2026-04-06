<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { apiFetch } from "../lib/api";
import UCard from "../components/ui/UCard.vue";

// ── Types ───────────────────────────────────────────────────────────────────

type FlowNode = {
  id: string;
  type: "device" | "variable" | "trigger" | "action" | "webhook" | "external";
  label: string;
  x: number;
  y: number;
  config: Record<string, unknown>;
};

type FlowEdge = {
  id: string;
  from: string;
  to: string;
  label?: string;
};

// ── State ───────────────────────────────────────────────────────────────────

const nodes = ref<FlowNode[]>([]);
const edges = ref<FlowEdge[]>([]);
const selectedNode = ref<FlowNode | null>(null);
const draggingNode = ref<string | null>(null);
const dragOffset = ref({ x: 0, y: 0 });
const canvasOffset = ref({ x: 0, y: 0 });
const zoom = ref(1);
const connecting = ref<string | null>(null);
const mousePos = ref({ x: 0, y: 0 });
const loading = ref(true);

const NODE_COLORS: Record<string, string> = {
  device: "#F5A623",
  variable: "#2DD4BF",
  trigger: "#ef4444",
  action: "#3b82f6",
  webhook: "#8b5cf6",
  external: "#6b7280",
};

const NODE_ICONS: Record<string, string> = {
  device: "M8.25 3v1.5M4.5 8.25H3m18 0h-1.5",
  variable: "M4.5 12.75l7.5-7.5 7.5 7.5",
  trigger: "M3.75 13.5l10.5-11.25L12 10.5h8.25",
  action: "M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z",
  webhook: "M12 21a9.004 9.004 0 008.716-6.747",
  external: "M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25",
};

// ── Load from API (devices + automations → nodes) ───────────────────────────

async function loadSystemGraph() {
  loading.value = true;
  try {
    const [devices, automations] = await Promise.allSettled([
      apiFetch<Array<{ id: number; device_uid: string; name: string | null }>>("/api/v1/devices"),
      apiFetch<Array<{ id: number; name: string; trigger_type: string; action_type: string }>>("/api/v1/automations"),
    ]);

    let x = 80, y = 80;
    const newNodes: FlowNode[] = [];
    const newEdges: FlowEdge[] = [];

    // Device nodes
    if (devices.status === "fulfilled") {
      for (const d of devices.value) {
        newNodes.push({
          id: `device-${d.id}`, type: "device",
          label: d.name || d.device_uid, x, y,
          config: { device_id: d.id, device_uid: d.device_uid },
        });
        y += 100;
        if (y > 500) { y = 80; x += 250; }
      }
    }

    // Automation nodes (trigger + action)
    x += 250; y = 80;
    if (automations.status === "fulfilled") {
      for (const a of automations.value) {
        const triggerId = `trigger-${a.id}`;
        const actionId = `action-${a.id}`;
        newNodes.push({
          id: triggerId, type: "trigger",
          label: `${a.trigger_type}`, x, y,
          config: { automation_id: a.id },
        });
        newNodes.push({
          id: actionId, type: "action",
          label: `${a.action_type}`, x: x + 200, y,
          config: { automation_id: a.id },
        });
        newEdges.push({ id: `edge-${a.id}`, from: triggerId, to: actionId, label: a.name });
        y += 100;
        if (y > 500) { y = 80; x += 450; }
      }
    }

    nodes.value = newNodes;
    edges.value = newEdges;
  } catch {
    // Empty canvas
  } finally {
    loading.value = false;
  }
}

// ── Node interaction ────────────────────────────────────────────────────────

function startDrag(node: FlowNode, e: MouseEvent) {
  draggingNode.value = node.id;
  dragOffset.value = { x: e.clientX - node.x * zoom.value, y: e.clientY - node.y * zoom.value };
  selectedNode.value = node;
}

function onMouseMove(e: MouseEvent) {
  mousePos.value = { x: e.clientX, y: e.clientY };
  if (draggingNode.value) {
    const node = nodes.value.find(n => n.id === draggingNode.value);
    if (node) {
      node.x = (e.clientX - dragOffset.value.x) / zoom.value;
      node.y = (e.clientY - dragOffset.value.y) / zoom.value;
    }
  }
}

function onMouseUp() {
  draggingNode.value = null;
}

function startConnection(nodeId: string) {
  if (connecting.value) {
    // Complete connection
    if (connecting.value !== nodeId) {
      edges.value.push({
        id: `edge-${Date.now()}`,
        from: connecting.value,
        to: nodeId,
      });
    }
    connecting.value = null;
  } else {
    connecting.value = nodeId;
  }
}

function addNode(type: FlowNode["type"]) {
  const id = `${type}-new-${Date.now()}`;
  nodes.value.push({
    id, type,
    label: `New ${type}`,
    x: 200 + Math.random() * 200,
    y: 200 + Math.random() * 200,
    config: {},
  });
}

function deleteSelected() {
  if (!selectedNode.value) return;
  const id = selectedNode.value.id;
  nodes.value = nodes.value.filter(n => n.id !== id);
  edges.value = edges.value.filter(e => e.from !== id && e.to !== id);
  selectedNode.value = null;
}

function getNodeCenter(node: FlowNode) {
  return { x: node.x + 70, y: node.y + 25 };
}

onMounted(loadSystemGraph);
</script>

<template>
  <div class="h-[calc(100vh-60px)] flex flex-col">
    <!-- Toolbar -->
    <div class="flex items-center justify-between px-4 py-2 border-b border-[var(--border)] bg-[var(--bg-surface)]">
      <div class="flex items-center gap-2">
        <h1 class="text-sm font-semibold text-[var(--text-primary)]">Flow Editor</h1>
        <span class="text-[10px] text-[var(--text-muted)]">{{ nodes.length }} nodes, {{ edges.length }} edges</span>
      </div>
      <div class="flex items-center gap-1.5">
        <button v-for="type in ['device', 'variable', 'trigger', 'action', 'webhook', 'external']" :key="type"
          class="px-2 py-1 rounded text-[10px] font-medium border border-[var(--border)] hover:border-[var(--primary)]/40 transition-colors"
          :style="{ color: NODE_COLORS[type] }"
          @click="addNode(type as FlowNode['type'])"
        >+ {{ type }}</button>
        <button v-if="selectedNode" class="px-2 py-1 rounded text-[10px] font-medium text-red-400 border border-red-500/30 hover:bg-red-500/10" @click="deleteSelected">
          Delete
        </button>
      </div>
    </div>

    <!-- Canvas -->
    <div
      class="flex-1 relative overflow-hidden bg-[var(--bg-base)]"
      @mousemove="onMouseMove"
      @mouseup="onMouseUp"
      style="background-image: radial-gradient(circle, var(--border) 1px, transparent 1px); background-size: 30px 30px;"
    >
      <div v-if="loading" class="absolute inset-0 flex items-center justify-center">
        <span class="text-sm text-[var(--text-muted)]">Loading system graph...</span>
      </div>

      <!-- SVG Edges -->
      <svg class="absolute inset-0 w-full h-full pointer-events-none" style="z-index: 1">
        <line
          v-for="edge in edges"
          :key="edge.id"
          :x1="getNodeCenter(nodes.find(n => n.id === edge.from)!).x"
          :y1="getNodeCenter(nodes.find(n => n.id === edge.from)!).y"
          :x2="getNodeCenter(nodes.find(n => n.id === edge.to)!).x"
          :y2="getNodeCenter(nodes.find(n => n.id === edge.to)!).y"
          stroke="var(--border-hover)"
          stroke-width="2"
          stroke-dasharray="6 3"
        />
        <!-- Connection in progress -->
        <line v-if="connecting"
          :x1="getNodeCenter(nodes.find(n => n.id === connecting)!).x"
          :y1="getNodeCenter(nodes.find(n => n.id === connecting)!).y"
          :x2="mousePos.x" :y2="mousePos.y"
          stroke="var(--primary)" stroke-width="2" stroke-dasharray="4 2"
        />
      </svg>

      <!-- Nodes -->
      <div
        v-for="node in nodes"
        :key="node.id"
        :class="[
          'absolute rounded-lg border-2 px-3 py-2 cursor-move select-none transition-shadow',
          selectedNode?.id === node.id ? 'shadow-lg ring-2 ring-[var(--primary)]/50' : 'shadow',
        ]"
        :style="{
          left: node.x + 'px', top: node.y + 'px',
          borderColor: NODE_COLORS[node.type],
          backgroundColor: 'var(--bg-surface)',
          zIndex: 2,
          minWidth: '140px',
        }"
        @mousedown.prevent="startDrag(node, $event)"
        @dblclick="startConnection(node.id)"
      >
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full shrink-0" :style="{ background: NODE_COLORS[node.type] }" />
          <span class="text-xs font-medium text-[var(--text-primary)] truncate">{{ node.label }}</span>
        </div>
        <span class="text-[9px] text-[var(--text-muted)] mt-0.5 block">{{ node.type }}</span>

        <!-- Connection ports -->
        <div
          class="absolute -right-2 top-1/2 -translate-y-1/2 w-4 h-4 rounded-full border-2 cursor-crosshair hover:scale-125 transition-transform"
          :style="{ borderColor: NODE_COLORS[node.type], background: connecting === node.id ? NODE_COLORS[node.type] : 'var(--bg-base)' }"
          @mousedown.stop="startConnection(node.id)"
        />
      </div>

      <!-- Help hint -->
      <div v-if="!loading && !nodes.length" class="absolute inset-0 flex items-center justify-center">
        <div class="text-center">
          <p class="text-sm text-[var(--text-muted)]">Empty canvas</p>
          <p class="text-[10px] text-[var(--text-muted)] mt-1">Add nodes from the toolbar, drag to position, double-click ports to connect</p>
        </div>
      </div>
    </div>

    <!-- Inspector panel -->
    <div v-if="selectedNode" class="border-t border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3">
      <div class="flex items-center justify-between">
        <div>
          <span class="text-xs font-semibold text-[var(--text-primary)]">{{ selectedNode.label }}</span>
          <span class="text-[10px] text-[var(--text-muted)] ml-2">{{ selectedNode.type }} | {{ selectedNode.id }}</span>
        </div>
        <button class="text-[10px] text-[var(--text-muted)]" @click="selectedNode = null">Close</button>
      </div>
      <div class="mt-2 text-[10px] font-mono text-[var(--text-muted)]">
        {{ JSON.stringify(selectedNode.config, null, 2) }}
      </div>
    </div>
  </div>
</template>
