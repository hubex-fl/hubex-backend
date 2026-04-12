<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from "vue";
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
  status?: string;
  last_seen?: string;
}

interface ApiVariable {
  key: string;
  scope: string;
  value_type: string;
  description: string | null;
  unit: string | null;
  current_value?: unknown;
  direction?: string;
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
  last_fired_at?: string;
  events_today?: number;
}

interface ApiWebhook {
  id: number;
  url: string;
  event_filter: string[];
  active: boolean;
  delivery_count?: number;
  last_delivery_status?: string;
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
const searchFocused = ref(false);
const searchDropdownIndex = ref(0);
const zoom = ref(1);
const pan = ref({ x: 0, y: 0 });
const isPanning = ref(false);
const panStart = ref({ x: 0, y: 0 });
const canvasRef = ref<HTMLElement | null>(null);
const transformLayerRef = ref<HTMLElement | null>(null);
const searchInputRef = ref<HTMLInputElement | null>(null);
const isAnimating = ref(false);
const pulsingNodeId = ref<string | null>(null);

// ── Layout mode ───────────────────────────────────────────────────────────
const layoutMode = ref<"columns" | "free">("columns");
const customPositions = ref<Record<string, { x: number; y: number }>>({});

// ── Drag state ────────────────────────────────────────────────────────────
const draggingNodeId = ref<string | null>(null);
const dragOffset = ref({ x: 0, y: 0 });

// ── Touch zoom state ──────────────────────────────────────────────────────
const touchStartDist = ref(0);
const touchStartZoom = ref(1);
const touchStartPan = ref({ x: 0, y: 0 });
const touchStartMid = ref({ x: 0, y: 0 });
const isTouchPanning = ref(false);
const lastTouchPos = ref({ x: 0, y: 0 });

// Stats
const stats = ref({ devices: 0, variables: 0, automations: 0, alerts: 0, webhooks: 0 });

// ── Legend toggle ──────────────────────────────────────────────────────────

const showLegend = ref(false);

// ── Filter state ──────────────────────────────────────────────────────────

const filterTypes = ref<Record<NodeType, boolean>>({
  device: true,
  variable: true,
  automation: true,
  alert: true,
  webhook: true,
});
const filterOnlyActive = ref(false);
const filterOnlyOffline = ref(false);
const filterPathNodeId = ref<string | null>(null);

// ── Context menu state ────────────────────────────────────────────────────

const contextMenu = ref<{ x: number; y: number; node: FlowNode } | null>(null);

// ── Detail panel state ────────────────────────────────────────────────────

const inspectorOpen = ref(false);

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

// ── Layout constants ───────────────────────────────────────────────────────

const COL_X = [60, 370, 680, 990]; // 4 columns — 310/310/310 gaps for readability
const NODE_W = 180;
const NODE_H_DEVICE = 50;
const NODE_H_SMALL = 42;
const ROW_GAP = 16;
const COL_START_Y = 60;

// ── Computed ───────────────────────────────────────────────────────────────

// Get the set of node IDs that are connected to the filterPathNodeId
const pathFilterIds = computed(() => {
  if (!filterPathNodeId.value) return null;
  const ids = new Set<string>();
  ids.add(filterPathNodeId.value);
  // Walk all edges recursively to find connected nodes
  let changed = true;
  while (changed) {
    changed = false;
    for (const e of edges.value) {
      if (ids.has(e.from) && !ids.has(e.to)) {
        ids.add(e.to);
        changed = true;
      }
      if (ids.has(e.to) && !ids.has(e.from)) {
        ids.add(e.from);
        changed = true;
      }
    }
  }
  return ids;
});

const visibleNodes = computed(() => {
  return nodes.value.filter((n) => {
    // Type filter
    if (!filterTypes.value[n.type]) return false;
    // Only active filter
    if (filterOnlyActive.value) {
      if (n.type === "automation" && n.enabled === false) return false;
      if (n.type === "alert" && n.enabled === false) return false;
      if (n.type === "webhook" && n.enabled === false) return false;
    }
    // Only offline devices filter
    if (filterOnlyOffline.value && n.type === "device") {
      const status = (n.meta?.status as string) || "";
      if (status === "online") return false;
    }
    // Path filter
    if (pathFilterIds.value && !pathFilterIds.value.has(n.id)) return false;
    return true;
  });
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

// Search results for dropdown
const searchResults = computed(() => {
  if (!searchQuery.value.trim()) return [];
  const q = searchQuery.value.toLowerCase();
  return nodes.value
    .filter(
      (n) =>
        n.label.toLowerCase().includes(q) ||
        n.type.includes(q) ||
        n.sublabel.toLowerCase().includes(q) ||
        (n.meta?.url as string || "").toLowerCase().includes(q)
    )
    .slice(0, 8);
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

    // Build variable→device ownership map by fetching per-device variables.
    // The API returns ALL variable definitions for every device, so we filter
    // to only variables that have actual data (value !== null) — those are
    // the ones the device truly owns/populates.
    const varToDeviceUid: Record<string, string> = {};
    const deviceVarResults = await Promise.allSettled(
      devices.map((d) =>
        apiFetch<{ device_uid: string; device: Array<{ key: string; value: unknown }> }>(
          `/api/v1/variables/device/${encodeURIComponent(d.device_uid)}`
        ).then((res) => ({ device_uid: d.device_uid, vars: res.device || [] }))
      )
    );
    for (const r of deviceVarResults) {
      if (r.status === "fulfilled") {
        for (const v of r.value.vars) {
          // Only count variables that have actual data from this device
          if (v.value != null && !varToDeviceUid[v.key]) {
            varToDeviceUid[v.key] = r.value.device_uid;
          }
        }
      }
    }

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
        meta: {
          device_id: d.id,
          category: d.category,
          status: d.status || "unknown",
          last_seen: d.last_seen,
        },
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
        meta: {
          scope: v.scope,
          value_type: v.value_type,
          unit: v.unit,
          current_value: v.current_value,
          direction: v.direction,
          description: v.description,
        },
      });
      y += NODE_H_SMALL + ROW_GAP;

      // Connect variables to their owning device using the per-device API data
      if (v.scope === "device") {
        // 1. Use the per-device variables map (most accurate)
        const ownerUid = varToDeviceUid[v.key];
        // 2. Fallback: check explicit device_uid from API
        const varDeviceUid = ownerUid || (v as Record<string, unknown>).device_uid as string | undefined;
        // 3. Fallback: parse key prefix (keys like "esp32-001.temperature")
        const dotIdx = v.key.indexOf(".");
        const keyPrefix = !varDeviceUid && dotIdx > 0 ? v.key.substring(0, dotIdx) : null;

        let matchDevice: ApiDevice | undefined;

        if (varDeviceUid) {
          matchDevice = devices.find(
            (d) => d.device_uid === varDeviceUid || String(d.id) === varDeviceUid
          );
        } else if (keyPrefix) {
          matchDevice = devices.find((d) => d.device_uid === keyPrefix);
        }

        if (matchDevice) {
          // Connect to the verified owning device
          newEdges.push({
            id: `edge-dev-var-${matchDevice.id}-${v.key}`,
            from: `device-${matchDevice.id}`,
            to: nodeId,
            type: "data",
          });
        }
        // No fallback — if we can't determine the owner, leave the variable unconnected
        // rather than incorrectly connecting it to the first device
      }
      // Global variables (scope != "device") get no device edges — they stand alone.
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
          description: a.description,
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
    y += 20;
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
        meta: {
          severity: ar.severity,
          condition_type: ar.condition_type,
          condition_config: ar.condition_config,
          last_fired_at: ar.last_fired_at,
          events_today: ar.events_today,
        },
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
        meta: {
          url: wh.url,
          delivery_count: wh.delivery_count,
          last_delivery_status: wh.last_delivery_status,
        },
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
  if (selectedNode.value?.id === node.id) {
    selectedNode.value = null;
    inspectorOpen.value = false;
  } else {
    selectedNode.value = node;
    inspectorOpen.value = true;
  }
}

function navigateToNode(node: FlowNode) {
  if (node.route) {
    router.push(node.route);
  }
}

function highlightNode(nodeId: string) {
  const node = nodes.value.find((n) => n.id === nodeId);
  if (!node) return;
  selectedNode.value = node;
  inspectorOpen.value = true;
  flyToNode(node);
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

  const x1 = fromNode.x + NODE_W;
  const y1 = fromNode.y + fromH / 2;
  const x2 = toNode.x;
  const y2 = toNode.y + toH / 2;

  if (toNode.column <= fromNode.column) {
    const midX = Math.min(x1, x2) - 40;
    return `M${x1},${y1} C${x1 + 40},${y1} ${midX},${y2} ${x2},${y2}`;
  }

  const dx = Math.abs(x2 - x1);
  const cpOffset = Math.min(dx * 0.4, 80);
  return `M${x1},${y1} C${x1 + cpOffset},${y1} ${x2 - cpOffset},${y2} ${x2},${y2}`;
}

// ── Zoom & Pan ─────────────────────────────────────────────────────────────

// Sprint 10 B2: zoom towards a focal point (cursor for wheel, center
// for +/- buttons) instead of always zooming to top-left corner.
// The math keeps the world-space point under the focal point fixed:
//   newPan = focal - (focal - oldPan) * (newZoom / oldZoom)
function _zoomTo(newZoom: number, focalX: number, focalY: number) {
  newZoom = Math.max(0.3, Math.min(2.5, newZoom));
  const ratio = newZoom / zoom.value;
  pan.value = {
    x: focalX - (focalX - pan.value.x) * ratio,
    y: focalY - (focalY - pan.value.y) * ratio,
  };
  zoom.value = newZoom;
}

function zoomIn() {
  // +/- buttons: zoom towards viewport center
  const c = canvasRef.value;
  const cx = c ? c.clientWidth / 2 : 0;
  const cy = c ? c.clientHeight / 2 : 0;
  _zoomTo(zoom.value + 0.15, cx, cy);
}
function zoomOut() {
  const c = canvasRef.value;
  const cx = c ? c.clientWidth / 2 : 0;
  const cy = c ? c.clientHeight / 2 : 0;
  _zoomTo(zoom.value - 0.15, cx, cy);
}
function zoomReset() {
  zoom.value = 1;
  pan.value = { x: 0, y: 0 };
}

function onWheel(e: WheelEvent) {
  e.preventDefault();
  const delta = e.deltaY > 0 ? -0.08 : 0.08;
  // Zoom towards cursor position (relative to canvas container)
  const rect = canvasRef.value?.getBoundingClientRect();
  const fx = rect ? e.clientX - rect.left : 0;
  const fy = rect ? e.clientY - rect.top : 0;
  _zoomTo(zoom.value + delta, fx, fy);
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

// ── Touch zoom & pan (pinch-to-zoom) ──────────────────────────────────────

function getTouchDistance(e: TouchEvent): number {
  const t1 = e.touches[0];
  const t2 = e.touches[1];
  return Math.sqrt((t2.clientX - t1.clientX) ** 2 + (t2.clientY - t1.clientY) ** 2);
}

function getTouchMidpoint(e: TouchEvent): { x: number; y: number } {
  const t1 = e.touches[0];
  const t2 = e.touches[1];
  return { x: (t1.clientX + t2.clientX) / 2, y: (t1.clientY + t2.clientY) / 2 };
}

function onTouchStart(e: TouchEvent) {
  if (e.touches.length === 2) {
    e.preventDefault();
    touchStartDist.value = getTouchDistance(e);
    touchStartZoom.value = zoom.value;
    touchStartPan.value = { ...pan.value };
    touchStartMid.value = getTouchMidpoint(e);
    isTouchPanning.value = false;
  } else if (e.touches.length === 1) {
    isTouchPanning.value = true;
    lastTouchPos.value = { x: e.touches[0].clientX, y: e.touches[0].clientY };
  }
}

function onTouchMove(e: TouchEvent) {
  if (e.touches.length === 2) {
    e.preventDefault();
    const currentDist = getTouchDistance(e);
    const scale = currentDist / touchStartDist.value;
    const newZoom = Math.max(0.3, Math.min(2.5, touchStartZoom.value * scale));

    // Sprint 10 B2: zoom towards the pinch midpoint, not just pan offset.
    // This combines the focal-point zoom with the pan-delta from finger movement.
    const currentMid = getTouchMidpoint(e);
    const rect = canvasRef.value?.getBoundingClientRect();
    const fx = rect ? currentMid.x - rect.left : currentMid.x;
    const fy = rect ? currentMid.y - rect.top : currentMid.y;
    const ratio = newZoom / touchStartZoom.value;
    pan.value = {
      x: fx - (fx - touchStartPan.value.x) * ratio + (currentMid.x - touchStartMid.value.x),
      y: fy - (fy - touchStartPan.value.y) * ratio + (currentMid.y - touchStartMid.value.y),
    };
    zoom.value = newZoom;
  } else if (e.touches.length === 1 && isTouchPanning.value) {
    const dx = e.touches[0].clientX - lastTouchPos.value.x;
    const dy = e.touches[0].clientY - lastTouchPos.value.y;
    pan.value = { x: pan.value.x + dx, y: pan.value.y + dy };
    lastTouchPos.value = { x: e.touches[0].clientX, y: e.touches[0].clientY };
  }
}

function onTouchEnd(e: TouchEvent) {
  if (e.touches.length < 2) {
    isTouchPanning.value = false;
  }
}

// ── Node dragging ─────────────────────────────────────────────────────────

const dragStartPos = ref({ x: 0, y: 0 });
const dragStarted = ref(false);
const DRAG_THRESHOLD = 5;

function onNodeMouseDown(e: MouseEvent, node: FlowNode) {
  e.stopPropagation();
  draggingNodeId.value = node.id;
  dragStarted.value = false;
  dragStartPos.value = { x: e.clientX, y: e.clientY };
  const nodeX = customPositions.value[node.id]?.x ?? node.x;
  const nodeY = customPositions.value[node.id]?.y ?? node.y;
  dragOffset.value = {
    x: e.clientX / zoom.value - nodeX,
    y: e.clientY / zoom.value - nodeY,
  };
  document.addEventListener("mousemove", onNodeDragMove);
  document.addEventListener("mouseup", onNodeDragEnd);
}

function onNodeDragMove(e: MouseEvent) {
  if (!draggingNodeId.value) return;
  // Check if we've exceeded drag threshold before starting actual drag
  if (!dragStarted.value) {
    const dx = e.clientX - dragStartPos.value.x;
    const dy = e.clientY - dragStartPos.value.y;
    if (Math.sqrt(dx * dx + dy * dy) < DRAG_THRESHOLD) return;
    dragStarted.value = true;
  }
  const newX = e.clientX / zoom.value - dragOffset.value.x;
  const newY = e.clientY / zoom.value - dragOffset.value.y;
  customPositions.value[draggingNodeId.value] = { x: newX, y: newY };
  const node = nodes.value.find((n) => n.id === draggingNodeId.value);
  if (node) {
    node.x = newX;
    node.y = newY;
  }
}

function onNodeDragEnd() {
  if (!dragStarted.value && draggingNodeId.value) {
    // It was a click, not a drag — select the node
    const node = nodes.value.find((n) => n.id === draggingNodeId.value);
    if (node) selectNode(node);
  }
  draggingNodeId.value = null;
  dragStarted.value = false;
  document.removeEventListener("mousemove", onNodeDragMove);
  document.removeEventListener("mouseup", onNodeDragEnd);
}

// ── Touch support for node dragging ─────────────────────────────────────

function onNodeTouchStart(e: TouchEvent, node: FlowNode) {
  if (e.touches.length !== 1) return;
  e.stopPropagation();
  e.preventDefault(); // prevent canvas pan from taking over
  draggingNodeId.value = node.id;
  dragStarted.value = false;
  const touch = e.touches[0];
  dragStartPos.value = { x: touch.clientX, y: touch.clientY };
  const nodeX = customPositions.value[node.id]?.x ?? node.x;
  const nodeY = customPositions.value[node.id]?.y ?? node.y;
  dragOffset.value = {
    x: touch.clientX / zoom.value - nodeX,
    y: touch.clientY / zoom.value - nodeY,
  };
  document.addEventListener("touchmove", onNodeTouchMove, { passive: false });
  document.addEventListener("touchend", onNodeTouchEnd);
  document.addEventListener("touchcancel", onNodeTouchEnd);
}

function onNodeTouchMove(e: TouchEvent) {
  if (!draggingNodeId.value || e.touches.length !== 1) return;
  e.preventDefault();
  const touch = e.touches[0];
  if (!dragStarted.value) {
    const dx = touch.clientX - dragStartPos.value.x;
    const dy = touch.clientY - dragStartPos.value.y;
    if (Math.sqrt(dx * dx + dy * dy) < DRAG_THRESHOLD) return;
    dragStarted.value = true;
  }
  const newX = touch.clientX / zoom.value - dragOffset.value.x;
  const newY = touch.clientY / zoom.value - dragOffset.value.y;
  customPositions.value[draggingNodeId.value] = { x: newX, y: newY };
  const node = nodes.value.find((n) => n.id === draggingNodeId.value);
  if (node) {
    node.x = newX;
    node.y = newY;
  }
}

function onNodeTouchEnd() {
  if (!dragStarted.value && draggingNodeId.value) {
    const node = nodes.value.find((n) => n.id === draggingNodeId.value);
    if (node) selectNode(node);
  }
  draggingNodeId.value = null;
  dragStarted.value = false;
  document.removeEventListener("touchmove", onNodeTouchMove);
  document.removeEventListener("touchend", onNodeTouchEnd);
  document.removeEventListener("touchcancel", onNodeTouchEnd);
}

function fitToView() {
  if (!nodes.value.length) return;
  const minX = Math.min(...nodes.value.map((n) => n.x));
  const maxX = Math.max(...nodes.value.map((n) => n.x + NODE_W));
  const minY = Math.min(...nodes.value.map((n) => n.y));
  const maxY = Math.max(...nodes.value.map((n) => n.y + getNodeHeight(n.type)));

  const canvas = canvasRef.value;
  if (!canvas) return;

  const cw = canvas.clientWidth - (inspectorOpen.value ? 300 : 0);
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

// ── Animated Camera Fly-To ────────────────────────────────────────────────

function flyToNode(node: FlowNode) {
  const canvas = canvasRef.value;
  if (!canvas) return;

  const nodeH = getNodeHeight(node.type);
  const nodeCenterX = node.x + NODE_W / 2;
  const nodeCenterY = node.y + nodeH / 2;

  const cw = canvas.clientWidth - (inspectorOpen.value ? 300 : 0);
  const ch = canvas.clientHeight;

  // Target: center the node in the viewport
  const targetZoom = Math.max(zoom.value, 1.0);
  const targetPanX = cw / 2 - nodeCenterX * targetZoom;
  const targetPanY = ch / 2 - nodeCenterY * targetZoom;

  // Enable CSS transition on the transform layer
  isAnimating.value = true;
  pulsingNodeId.value = null;

  // Apply new transform (CSS transition will animate it)
  zoom.value = targetZoom;
  pan.value = { x: targetPanX, y: targetPanY };

  // After transition ends, start pulsing
  setTimeout(() => {
    isAnimating.value = false;
    pulsingNodeId.value = node.id;
    // Stop pulsing after 3 seconds
    setTimeout(() => {
      if (pulsingNodeId.value === node.id) {
        pulsingNodeId.value = null;
      }
    }, 3000);
  }, 650);
}

// ── Search handling ───────────────────────────────────────────────────────

function onSearchKeydown(e: KeyboardEvent) {
  if (e.key === "Escape") {
    searchQuery.value = "";
    searchFocused.value = false;
    (e.target as HTMLElement)?.blur();
    return;
  }
  if (e.key === "ArrowDown") {
    e.preventDefault();
    searchDropdownIndex.value = Math.min(searchDropdownIndex.value + 1, searchResults.value.length - 1);
    return;
  }
  if (e.key === "ArrowUp") {
    e.preventDefault();
    searchDropdownIndex.value = Math.max(searchDropdownIndex.value - 1, 0);
    return;
  }
  if (e.key === "Enter" && searchResults.value.length > 0) {
    e.preventDefault();
    const node = searchResults.value[searchDropdownIndex.value];
    if (node) selectSearchResult(node);
  }
}

function selectSearchResult(node: FlowNode) {
  searchQuery.value = "";
  searchFocused.value = false;
  selectedNode.value = node;
  inspectorOpen.value = true;
  flyToNode(node);
}

watch(searchQuery, () => {
  searchDropdownIndex.value = 0;
});

// ── Context menu ──────────────────────────────────────────────────────────

function onNodeContextMenu(e: MouseEvent, node: FlowNode) {
  e.preventDefault();
  e.stopPropagation();
  contextMenu.value = { x: e.clientX, y: e.clientY, node };
}

function closeContextMenu() {
  contextMenu.value = null;
}

function ctxGoToDetail() {
  if (contextMenu.value?.node) {
    navigateToNode(contextMenu.value.node);
  }
  closeContextMenu();
}

function ctxHighlightConnections() {
  if (contextMenu.value?.node) {
    selectedNode.value = contextMenu.value.node;
    inspectorOpen.value = true;
  }
  closeContextMenu();
}

function ctxFilterToPath() {
  if (contextMenu.value?.node) {
    filterPathNodeId.value = contextMenu.value.node.id;
    selectedNode.value = contextMenu.value.node;
    inspectorOpen.value = true;
  }
  closeContextMenu();
}

function clearPathFilter() {
  filterPathNodeId.value = null;
}

// ── Close context menu on click outside ───────────────────────────────────

function onDocumentClick() {
  if (contextMenu.value) {
    closeContextMenu();
  }
}

// ── AI Coop: fly-to-node event listener ─────────────────────────────────

function onAiFlyTo(e: Event) {
  const detail = (e as CustomEvent).detail;
  const nodeId = detail?.node_id;
  if (!nodeId) return;
  const node = nodes.value.find((n) => n.id === nodeId);
  if (node) {
    selectedNode.value = node;
    inspectorOpen.value = true;
    flyToNode(node);
  }
}

onMounted(async () => {
  document.addEventListener("click", onDocumentClick);
  window.addEventListener("ai-fly-to", onAiFlyTo);
  await loadSystemGraph();
  await nextTick();
  fitToView();
});

onUnmounted(() => {
  document.removeEventListener("click", onDocumentClick);
  window.removeEventListener("ai-fly-to", onAiFlyTo);
});

// ── Inspector helpers ─────────────────────────────────────────────────────

function getInspectorRoute(node: FlowNode): string {
  switch (node.type) {
    case "device": return t("pages.flowEditor.goToDevice");
    case "variable": return t("pages.flowEditor.goToVariable");
    case "automation": return t("pages.flowEditor.editAutomation");
    case "alert": return t("pages.flowEditor.viewAlerts");
    case "webhook": return t("pages.flowEditor.viewWebhook");
    default: return t("pages.flowEditor.openDetail");
  }
}

function getConnectedCount(nodeId: string): number {
  return edges.value.filter((e) => e.from === nodeId || e.to === nodeId).length;
}

// Column headers
const columnHeaders = computed(() => [
  { label: t("pages.flowEditor.colDevices"), count: stats.value.devices, color: NODE_COLORS.device },
  { label: t("pages.flowEditor.colVariables"), count: stats.value.variables, color: NODE_COLORS.variable },
  { label: t("pages.flowEditor.colLogic"), count: stats.value.automations + stats.value.alerts, color: NODE_COLORS.automation },
  { label: t("pages.flowEditor.colOutputs"), count: stats.value.webhooks, color: NODE_COLORS.webhook },
]);

// Toggle filter type
function toggleFilterType(type: NodeType) {
  filterTypes.value[type] = !filterTypes.value[type];
}

// Check if any filters are active
const hasActiveFilters = computed(() => {
  return !filterTypes.value.device || !filterTypes.value.variable || !filterTypes.value.automation ||
    !filterTypes.value.alert || !filterTypes.value.webhook ||
    filterOnlyActive.value || filterOnlyOffline.value || filterPathNodeId.value !== null;
});

function resetFilters() {
  filterTypes.value = { device: true, variable: true, automation: true, alert: true, webhook: true };
  filterOnlyActive.value = false;
  filterOnlyOffline.value = false;
  filterPathNodeId.value = null;
}

// ── Layout mode toggle ───────────────────────────────────────────────────

function toggleLayoutMode() {
  layoutMode.value = layoutMode.value === "columns" ? "free" : "columns";
  applyLayout();
  nextTick(() => fitToView());
}

function applyLayout() {
  if (layoutMode.value === "columns") {
    // Restore column positions (re-run layout algorithm)
    customPositions.value = {};
    // Re-assign column-based positions
    const colCounts = [0, 0, 0, 0];
    for (const node of nodes.value) {
      const colIdx = node.column;
      node.x = COL_X[colIdx];
      node.y = COL_START_Y + colCounts[colIdx] * (getNodeHeight(node.type) + ROW_GAP);
      colCounts[colIdx]++;
    }
  } else {
    // Free layout: spread nodes in a wider area using a simple force-directed approximation
    const centerX = 500;
    const centerY = 400;
    const radius = Math.max(200, nodes.value.length * 25);
    nodes.value.forEach((node, i) => {
      const angle = (i / nodes.value.length) * 2 * Math.PI;
      const colOffset = node.column * 150;
      const x = centerX + colOffset + Math.cos(angle) * (radius * 0.3);
      const y = centerY + Math.sin(angle) * radius * 0.6;
      node.x = x;
      node.y = y;
      customPositions.value[node.id] = { x, y };
    });
  }
}
</script>

<template>
  <div class="h-[calc(100vh-60px)] flex flex-col">
    <!-- Toolbar -->
    <div class="flex items-center justify-between px-4 py-2 border-b border-[var(--border)] bg-[var(--bg-surface)]">
      <div class="flex items-center gap-3">
        <h1 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('pages.flowEditor.title') }}</h1>
        <UInfoTooltip :title="t('infoTooltips.flowEditor.title')" :items="tm('infoTooltips.flowEditor.items').map((i: any) => rt(i))" tourId="data-path-trace" />

        <!-- Stats pills -->
        <div class="flex items-center gap-1.5">
          <span v-for="(s, key) in { D: stats.devices, V: stats.variables, A: stats.automations, R: stats.alerts, W: stats.webhooks }"
            :key="key"
            class="px-1.5 py-0.5 rounded text-[9px] font-mono border border-[var(--border)] text-[var(--text-muted)]"
          >{{ key }}:{{ s }}</span>
        </div>
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

        <span class="w-px h-4 bg-[var(--border)]" />

        <!-- Layout mode toggle -->
        <button
          class="px-2 py-1 rounded text-[10px] border transition-colors"
          :class="layoutMode === 'free'
            ? 'border-[var(--primary)]/50 text-[var(--primary)] bg-[var(--primary)]/10'
            : 'border-[var(--border)] text-[var(--text-muted)] hover:bg-[var(--bg-raised)]'"
          @click="toggleLayoutMode"
        >{{ layoutMode === 'columns' ? 'Free Layout' : 'Columns' }}</button>
      </div>
    </div>

    <!-- Main area with canvas + inspector -->
    <div class="flex-1 flex relative overflow-hidden">

      <!-- Canvas area -->
      <div
        ref="canvasRef"
        class="flex-1 relative overflow-hidden bg-[var(--bg-base)] canvas-bg"
        :class="{ 'cursor-grab': !isPanning, 'cursor-grabbing': isPanning }"
        @mousedown="startPan"
        @mousemove="onPanMove"
        @mouseup="stopPan"
        @mouseleave="stopPan"
        @wheel.prevent="onWheel"
        @touchstart="onTouchStart"
        @touchmove="onTouchMove"
        @touchend="onTouchEnd"
        style="background-image: radial-gradient(circle, var(--border) 1px, transparent 1px); background-size: 30px 30px;"
      >
        <!-- Floating search field -->
        <div class="absolute top-3 left-3 z-30 w-64">
          <div class="relative">
            <input
              ref="searchInputRef"
              v-model="searchQuery"
              class="w-full px-3 py-1.5 pl-8 rounded-lg border border-[var(--border)] bg-[var(--bg-surface)]/90 backdrop-blur-sm text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)]/40"
              :placeholder="t('pages.flowEditor.searchPlaceholder')"
              @focus="searchFocused = true"
              @blur="setTimeout(() => searchFocused = false, 200)"
              @keydown="onSearchKeydown"
            />
            <!-- Search icon -->
            <svg class="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--text-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
            </svg>
          </div>

          <!-- Search dropdown -->
          <Transition name="fade">
            <div
              v-if="searchFocused && searchQuery.trim() && searchResults.length > 0"
              class="absolute top-full left-0 right-0 mt-1 bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg shadow-xl overflow-hidden z-40"
            >
              <div
                v-for="(node, idx) in searchResults"
                :key="node.id"
                class="flex items-center gap-2 px-3 py-1.5 cursor-pointer text-xs transition-colors"
                :class="idx === searchDropdownIndex ? 'bg-[var(--primary)]/10' : 'hover:bg-[var(--bg-raised)]'"
                @mousedown.prevent="selectSearchResult(node)"
              >
                <div class="w-2 h-2 rounded-full shrink-0" :style="{ background: NODE_COLORS[node.type] }" />
                <span class="text-[var(--text-primary)] truncate flex-1">{{ node.label }}</span>
                <span class="text-[9px] text-[var(--text-muted)] shrink-0">{{ node.type }}</span>
              </div>
            </div>
          </Transition>

          <!-- No results -->
          <Transition name="fade">
            <div
              v-if="searchFocused && searchQuery.trim() && searchResults.length === 0"
              class="absolute top-full left-0 right-0 mt-1 bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg shadow-xl px-3 py-2 z-40"
            >
              <span class="text-[10px] text-[var(--text-muted)]">{{ t('pages.flowEditor.noResults') }}</span>
            </div>
          </Transition>
        </div>

        <!-- Filter bar -->
        <div class="absolute top-3 left-[280px] z-30 flex items-center gap-1.5">
          <!-- Type filter chips -->
          <button
            v-for="(active, type) in filterTypes"
            :key="type"
            class="px-2 py-1 rounded-full text-[10px] font-medium border transition-all duration-150"
            :class="active
              ? 'border-transparent text-white'
              : 'border-[var(--border)] text-[var(--text-muted)] bg-[var(--bg-surface)]/80 opacity-60'"
            :style="active ? { background: NODE_COLORS[type as NodeType] + 'dd' } : {}"
            @click="toggleFilterType(type as NodeType)"
          >
            {{ t(`pages.flowEditor.filter${(type as string).charAt(0).toUpperCase() + (type as string).slice(1)}s`) }}
          </button>

          <span class="w-px h-4 bg-[var(--border)]" />

          <!-- Only active toggle -->
          <button
            class="px-2 py-1 rounded-full text-[10px] border transition-all duration-150"
            :class="filterOnlyActive
              ? 'border-green-500/50 text-green-400 bg-green-500/10'
              : 'border-[var(--border)] text-[var(--text-muted)] bg-[var(--bg-surface)]/80'"
            @click="filterOnlyActive = !filterOnlyActive"
          >
            {{ t('pages.flowEditor.onlyActive') }}
          </button>

          <!-- Only offline toggle -->
          <button
            class="px-2 py-1 rounded-full text-[10px] border transition-all duration-150"
            :class="filterOnlyOffline
              ? 'border-red-500/50 text-red-400 bg-red-500/10'
              : 'border-[var(--border)] text-[var(--text-muted)] bg-[var(--bg-surface)]/80'"
            @click="filterOnlyOffline = !filterOnlyOffline"
          >
            {{ t('pages.flowEditor.onlyOffline') }}
          </button>

          <!-- Path filter indicator -->
          <button
            v-if="filterPathNodeId"
            class="px-2 py-1 rounded-full text-[10px] border border-amber-500/50 text-amber-400 bg-amber-500/10 flex items-center gap-1"
            @click="clearPathFilter"
          >
            {{ t('pages.flowEditor.filterToPath') }}
            <span class="text-[8px]">x</span>
          </button>

          <!-- Reset filters -->
          <button
            v-if="hasActiveFilters"
            class="px-2 py-1 rounded-full text-[10px] border border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text-primary)] bg-[var(--bg-surface)]/80"
            @click="resetFilters"
          >
            {{ t('pages.flowEditor.resetView') }}
          </button>
        </div>

        <!-- Loading -->
        <div v-if="loading" class="absolute inset-0 flex items-center justify-center z-10">
          <div class="flex items-center gap-2">
            <div class="w-4 h-4 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
            <span class="text-sm text-[var(--text-muted)]">{{ t('pages.flowEditor.loading') }}</span>
          </div>
        </div>

        <!-- Legend overlay -->
        <Transition name="fade">
          <div v-if="showLegend" class="absolute top-14 right-4 z-50 bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg p-3 shadow-xl min-w-[180px]">
            <p class="text-[10px] font-semibold text-[var(--text-primary)] mb-2">{{ t('pages.flowEditor.legendNodeTypes') }}</p>
            <div class="space-y-1.5">
              <div class="flex items-center gap-2">
                <div class="w-3 h-3 rounded-sm" :style="{ background: NODE_COLORS.device }" />
                <span class="text-[10px] text-[var(--text-muted)]">{{ t('pages.flowEditor.legendDevice') }}</span>
              </div>
              <div class="flex items-center gap-2">
                <div class="w-3 h-3 rounded-sm" :style="{ background: NODE_COLORS.variable }" />
                <span class="text-[10px] text-[var(--text-muted)]">{{ t('pages.flowEditor.legendVariable') }}</span>
              </div>
              <div class="flex items-center gap-2">
                <div class="w-3 h-3 rounded-sm" :style="{ background: NODE_COLORS.automation }" />
                <span class="text-[10px] text-[var(--text-muted)]">{{ t('pages.flowEditor.legendAutomation') }}</span>
              </div>
              <div class="flex items-center gap-2">
                <div class="w-3 h-3 rounded-sm" :style="{ background: NODE_COLORS.alert }" />
                <span class="text-[10px] text-[var(--text-muted)]">{{ t('pages.flowEditor.legendAlert') }}</span>
              </div>
              <div class="flex items-center gap-2">
                <div class="w-3 h-3 rounded-sm" :style="{ background: NODE_COLORS.webhook }" />
                <span class="text-[10px] text-[var(--text-muted)]">{{ t('pages.flowEditor.legendWebhook') }}</span>
              </div>
            </div>
            <hr class="border-[var(--border)] my-2" />
            <p class="text-[10px] font-semibold text-[var(--text-primary)] mb-2">{{ t('pages.flowEditor.legendConnections') }}</p>
            <div class="space-y-1.5">
              <div class="flex items-center gap-2">
                <div class="w-6 h-0.5" :style="{ background: EDGE_COLORS.data }" />
                <span class="text-[10px] text-[var(--text-muted)]">{{ t('pages.flowEditor.legendDataFlow') }}</span>
                <span class="text-[8px] text-[var(--text-muted)] ml-auto">Device &#8594; Variable</span>
              </div>
              <div class="flex items-center gap-2">
                <div class="w-6 h-0.5" :style="{ background: EDGE_COLORS.trigger }" />
                <span class="text-[10px] text-[var(--text-muted)]">{{ t('pages.flowEditor.legendTrigger') }}</span>
                <span class="text-[8px] text-[var(--text-muted)] ml-auto">Variable &#8594; Auto/Alert</span>
              </div>
              <div class="flex items-center gap-2">
                <div class="w-6 h-0.5" :style="{ background: EDGE_COLORS.action }" />
                <span class="text-[10px] text-[var(--text-muted)]">{{ t('pages.flowEditor.legendAction') }}</span>
                <span class="text-[8px] text-[var(--text-muted)] ml-auto">Auto &#8594; Webhook/Var</span>
              </div>
              <div class="flex items-center gap-2">
                <div class="w-6 h-0.5 border-t-2 border-dashed" :style="{ borderColor: EDGE_COLORS.monitor }" />
                <span class="text-[10px] text-[var(--text-muted)]">{{ t('pages.flowEditor.legendMonitor') }}</span>
                <span class="text-[8px] text-[var(--text-muted)] ml-auto">Alert &#8596; Variable</span>
              </div>
            </div>
          </div>
        </Transition>

        <!-- Transformed layer -->
        <div
          v-if="!loading"
          ref="transformLayerRef"
          :style="{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: '0 0',
          }"
          :class="{ 'flow-animate': isAnimating }"
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
              pulsingNodeId === node.id ? 'node-pulse' : '',
            ]"
            :style="{
              left: node.x + 'px',
              top: node.y + 'px',
              width: NODE_W + 'px',
              height: getNodeHeight(node.type) + 'px',
              borderColor: NODE_COLORS[node.type] + '60',
              backgroundColor: NODE_BG[node.type],
              zIndex: draggingNodeId === node.id ? 20 : selectedNode?.id === node.id ? 10 : 2,
              cursor: draggingNodeId === node.id ? 'grabbing' : 'grab',
            }"
            @dblclick.stop="navigateToNode(node)"
            @contextmenu="onNodeContextMenu($event, node)"
            @mousedown.stop="onNodeMouseDown($event, node)"
            @touchstart.stop="onNodeTouchStart($event, node)"
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
                  :title="node.enabled ? t('pages.flowEditor.active') : t('pages.flowEditor.inactive')"
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

      <!-- ── Detail Inspector Panel (right side, 300px) ─────────────────── -->
      <Transition name="slide-right">
        <div
          v-if="inspectorOpen && selectedNode"
          class="w-[300px] shrink-0 border-l border-[var(--border)] bg-[var(--bg-surface)] overflow-y-auto"
        >
          <!-- Panel header -->
          <div class="flex items-center justify-between px-4 py-3 border-b border-[var(--border)]">
            <div class="flex items-center gap-2">
              <div class="w-2.5 h-2.5 rounded-sm" :style="{ background: NODE_COLORS[selectedNode.type] }" />
              <span class="text-xs font-semibold text-[var(--text-primary)]">{{ t('pages.flowEditor.inspector') }}</span>
            </div>
            <button
              class="w-5 h-5 flex items-center justify-center rounded hover:bg-[var(--bg-raised)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
              @click="inspectorOpen = false; selectedNode = null"
            >
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>

          <!-- Node title -->
          <div class="px-4 py-3 border-b border-[var(--border)]">
            <div class="text-sm font-semibold text-[var(--text-primary)]">{{ selectedNode.label }}</div>
            <div class="text-[10px] text-[var(--text-muted)] mt-0.5">{{ selectedNode.sublabel }}</div>
          </div>

          <!-- ── Device details ──────────────────────────────────────────── -->
          <div v-if="selectedNode.type === 'device'" class="px-4 py-3 space-y-2.5">
            <div class="flex justify-between text-[11px]">
              <span class="text-[var(--text-muted)]">{{ t('pages.flowEditor.deviceType') }}</span>
              <span class="px-1.5 py-0.5 rounded text-[9px] font-medium border border-[var(--border)] text-[var(--text-primary)]">
                {{ (selectedNode.meta?.category as string) || 'hardware' }}
              </span>
            </div>
            <div class="flex justify-between text-[11px]">
              <span class="text-[var(--text-muted)]">{{ t('pages.flowEditor.deviceStatus') }}</span>
              <span
                class="px-1.5 py-0.5 rounded text-[9px] font-medium"
                :class="(selectedNode.meta?.status as string) === 'online'
                  ? 'bg-green-500/10 text-green-400'
                  : 'bg-red-500/10 text-red-400'"
              >
                {{ (selectedNode.meta?.status as string) === 'online' ? t('pages.flowEditor.online') : t('pages.flowEditor.offline') }}
              </span>
            </div>
            <div v-if="selectedNode.meta?.last_seen" class="flex justify-between text-[11px]">
              <span class="text-[var(--text-muted)]">{{ t('pages.flowEditor.lastSeen') }}</span>
              <span class="text-[var(--text-primary)] text-[10px]">{{ selectedNode.meta?.last_seen }}</span>
            </div>
            <div class="flex justify-between text-[11px]">
              <span class="text-[var(--text-muted)]">{{ t('pages.flowEditor.variableCount') }}</span>
              <span class="text-[var(--text-primary)]">{{ getConnectedCount(selectedNode.id) }}</span>
            </div>
            <button
              class="w-full mt-2 px-3 py-1.5 rounded text-[11px] font-medium text-[var(--primary)] border border-[var(--primary)]/30 hover:bg-[var(--primary)]/10 transition-colors"
              @click="highlightNode(selectedNode.id)"
            >&#8594; {{ t('pages.flowEditor.goToDevice') }}</button>
            <button
              class="w-full mt-1 px-3 py-1 rounded text-[10px] text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
              @click="navigateToNode(selectedNode)"
            >{{ t('pages.flowEditor.openDetail') }} &#8599;</button>
          </div>

          <!-- ── Variable details ────────────────────────────────────────── -->
          <div v-if="selectedNode.type === 'variable'" class="px-4 py-3 space-y-2.5">
            <div class="flex justify-between text-[11px]">
              <span class="text-[var(--text-muted)]">{{ t('pages.flowEditor.variableKey') }}</span>
              <span class="text-[var(--text-primary)] font-mono text-[10px]">{{ selectedNode.label }}</span>
            </div>
            <div class="flex justify-between text-[11px]">
              <span class="text-[var(--text-muted)]">{{ t('pages.flowEditor.currentValue') }}</span>
              <span class="text-[var(--text-primary)] font-mono text-[10px]">
                {{ selectedNode.meta?.current_value !== undefined ? String(selectedNode.meta.current_value) : '—' }}
                <span v-if="selectedNode.meta?.unit" class="text-[var(--text-muted)]">{{ selectedNode.meta.unit }}</span>
              </span>
            </div>
            <div class="flex justify-between text-[11px]">
              <span class="text-[var(--text-muted)]">{{ t('pages.flowEditor.valueType') }}</span>
              <span class="px-1.5 py-0.5 rounded text-[9px] font-medium border border-[var(--border)] text-[var(--text-primary)]">
                {{ selectedNode.meta?.value_type || '—' }}
              </span>
            </div>
            <div v-if="selectedNode.meta?.direction" class="flex justify-between text-[11px]">
              <span class="text-[var(--text-muted)]">{{ t('pages.flowEditor.direction') }}</span>
              <span class="text-[var(--text-primary)]">{{ selectedNode.meta.direction }}</span>
            </div>
            <!-- Sparkline placeholder (last 10 values) -->
            <div class="mt-2">
              <span class="text-[10px] text-[var(--text-muted)]">{{ t('pages.flowEditor.recentValues') }}</span>
              <div class="mt-1 h-8 rounded bg-[var(--bg-raised)] flex items-end gap-px px-1">
                <div
                  v-for="i in 10"
                  :key="i"
                  class="flex-1 rounded-t"
                  :style="{
                    height: (20 + Math.random() * 60) + '%',
                    background: NODE_COLORS.variable + '80',
                  }"
                />
              </div>
            </div>
            <button
              class="w-full mt-2 px-3 py-1.5 rounded text-[11px] font-medium text-teal-400 border border-teal-400/30 hover:bg-teal-400/10 transition-colors"
              @click="highlightNode(selectedNode.id)"
            >&#8594; {{ t('pages.flowEditor.goToVariable') }}</button>
            <button
              class="w-full mt-1 px-3 py-1 rounded text-[10px] text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
              @click="navigateToNode(selectedNode)"
            >{{ t('pages.flowEditor.openDetail') }} &#8599;</button>
          </div>

          <!-- ── Automation details ──────────────────────────────────────── -->
          <div v-if="selectedNode.type === 'automation'" class="px-4 py-3 space-y-2.5">
            <div class="flex justify-between text-[11px]">
              <span class="text-[var(--text-muted)]">{{ t('pages.flowEditor.automationName') }}</span>
              <span class="text-[var(--text-primary)]">{{ selectedNode.label }}</span>
            </div>
            <div class="flex justify-between text-[11px]">
              <span class="text-[var(--text-muted)]">{{ t('pages.flowEditor.triggerType') }}</span>
              <span class="px-1.5 py-0.5 rounded text-[9px] font-medium border border-[var(--border)] text-[var(--text-primary)]">
                {{ (selectedNode.meta?.trigger_type as string || '').replace(/_/g, ' ') }}
              </span>
            </div>
            <div class="flex justify-between text-[11px]">
              <span class="text-[var(--text-muted)]">{{ t('pages.flowEditor.actionType') }}</span>
              <span class="px-1.5 py-0.5 rounded text-[9px] font-medium border border-[var(--border)] text-[var(--text-primary)]">
                {{ (selectedNode.meta?.action_type as string || '').replace(/_/g, ' ') }}
              </span>
            </div>
            <div class="flex justify-between text-[11px]">
              <span class="text-[var(--text-muted)]">{{ t('common.status') }}</span>
              <span
                class="px-1.5 py-0.5 rounded text-[9px] font-medium"
                :class="selectedNode.enabled ? 'bg-green-500/10 text-green-400' : 'bg-gray-500/10 text-gray-400'"
              >{{ selectedNode.enabled ? t('pages.flowEditor.active') : t('pages.flowEditor.inactive') }}</span>
            </div>
            <button
              class="w-full mt-2 px-3 py-1.5 rounded text-[11px] font-medium text-blue-400 border border-blue-400/30 hover:bg-blue-400/10 transition-colors"
              @click="highlightNode(selectedNode.id)"
            >&#8594; {{ t('pages.flowEditor.editAutomation') }}</button>
            <button
              class="w-full mt-1 px-3 py-1 rounded text-[10px] text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
              @click="navigateToNode(selectedNode)"
            >{{ t('pages.flowEditor.openDetail') }} &#8599;</button>
          </div>

          <!-- ── Alert Rule details ──────────────────────────────────────── -->
          <div v-if="selectedNode.type === 'alert'" class="px-4 py-3 space-y-2.5">
            <div class="flex justify-between text-[11px]">
              <span class="text-[var(--text-muted)]">{{ t('pages.flowEditor.alertCondition') }}</span>
              <span class="px-1.5 py-0.5 rounded text-[9px] font-medium border border-[var(--border)] text-[var(--text-primary)]">
                {{ (selectedNode.meta?.condition_type as string || '').replace(/_/g, ' ') }}
              </span>
            </div>
            <div class="flex justify-between text-[11px]">
              <span class="text-[var(--text-muted)]">{{ t('pages.flowEditor.severity') }}</span>
              <span
                class="px-1.5 py-0.5 rounded text-[9px] font-medium"
                :class="{
                  'bg-red-500/10 text-red-400': selectedNode.meta?.severity === 'critical',
                  'bg-amber-500/10 text-amber-400': selectedNode.meta?.severity === 'warning',
                  'bg-blue-500/10 text-blue-400': selectedNode.meta?.severity === 'info',
                }"
              >{{ selectedNode.meta?.severity || '—' }}</span>
            </div>
            <div class="flex justify-between text-[11px]">
              <span class="text-[var(--text-muted)]">{{ t('pages.flowEditor.lastFired') }}</span>
              <span class="text-[var(--text-primary)] text-[10px]">{{ selectedNode.meta?.last_fired_at || '—' }}</span>
            </div>
            <div class="flex justify-between text-[11px]">
              <span class="text-[var(--text-muted)]">{{ t('pages.flowEditor.eventsToday') }}</span>
              <span class="text-[var(--text-primary)]">{{ selectedNode.meta?.events_today ?? '—' }}</span>
            </div>
            <button
              class="w-full mt-2 px-3 py-1.5 rounded text-[11px] font-medium text-red-400 border border-red-400/30 hover:bg-red-400/10 transition-colors"
              @click="highlightNode(selectedNode.id)"
            >&#8594; {{ t('pages.flowEditor.viewAlerts') }}</button>
            <button
              class="w-full mt-1 px-3 py-1 rounded text-[10px] text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
              @click="navigateToNode(selectedNode)"
            >{{ t('pages.flowEditor.openDetail') }} &#8599;</button>
          </div>

          <!-- ── Webhook details ─────────────────────────────────────────── -->
          <div v-if="selectedNode.type === 'webhook'" class="px-4 py-3 space-y-2.5">
            <div class="text-[11px]">
              <span class="text-[var(--text-muted)]">{{ t('pages.flowEditor.webhookUrl') }}</span>
              <div class="mt-0.5 text-[10px] font-mono text-[var(--text-primary)] break-all bg-[var(--bg-raised)] rounded px-2 py-1">
                {{ selectedNode.meta?.url || selectedNode.label }}
              </div>
            </div>
            <div class="flex justify-between text-[11px]">
              <span class="text-[var(--text-muted)]">{{ t('pages.flowEditor.eventCount') }}</span>
              <span class="text-[var(--text-primary)]">{{ selectedNode.meta?.delivery_count ?? '—' }}</span>
            </div>
            <div class="flex justify-between text-[11px]">
              <span class="text-[var(--text-muted)]">{{ t('pages.flowEditor.lastDelivery') }}</span>
              <span
                class="px-1.5 py-0.5 rounded text-[9px] font-medium"
                :class="(selectedNode.meta?.last_delivery_status as string) === 'success'
                  ? 'bg-green-500/10 text-green-400'
                  : 'bg-gray-500/10 text-gray-400'"
              >{{ selectedNode.meta?.last_delivery_status || '—' }}</span>
            </div>
            <div class="flex justify-between text-[11px]">
              <span class="text-[var(--text-muted)]">{{ t('common.status') }}</span>
              <span
                class="px-1.5 py-0.5 rounded text-[9px] font-medium"
                :class="selectedNode.enabled ? 'bg-green-500/10 text-green-400' : 'bg-gray-500/10 text-gray-400'"
              >{{ selectedNode.enabled ? t('pages.flowEditor.active') : t('pages.flowEditor.inactive') }}</span>
            </div>
            <button
              class="w-full mt-2 px-3 py-1.5 rounded text-[11px] font-medium text-purple-400 border border-purple-400/30 hover:bg-purple-400/10 transition-colors"
              @click="highlightNode(selectedNode.id)"
            >&#8594; {{ t('pages.flowEditor.viewWebhook') }}</button>
            <button
              class="w-full mt-1 px-3 py-1 rounded text-[10px] text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors"
              @click="navigateToNode(selectedNode)"
            >{{ t('pages.flowEditor.openDetail') }} &#8599;</button>
          </div>
        </div>
      </Transition>
    </div>

    <!-- ── Context menu ─────────────────────────────────────────────────── -->
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="contextMenu"
          class="fixed z-[100] min-w-[180px] bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg shadow-xl overflow-hidden"
          :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
          @click.stop
        >
          <button
            class="w-full flex items-center gap-2 px-3 py-2 text-[11px] text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors text-left"
            @click="ctxGoToDetail"
          >
            <span class="text-[var(--text-muted)]">&#8594;</span>
            {{ t('pages.flowEditor.goToDetail') }}
          </button>
          <button
            class="w-full flex items-center gap-2 px-3 py-2 text-[11px] text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors text-left"
            @click="ctxHighlightConnections"
          >
            <span class="text-[var(--text-muted)]">&#9733;</span>
            {{ t('pages.flowEditor.highlightConnections') }}
          </button>
          <hr class="border-[var(--border)]" />
          <button
            class="w-full flex items-center gap-2 px-3 py-2 text-[11px] text-[var(--text-primary)] hover:bg-[var(--bg-raised)] transition-colors text-left"
            @click="ctxFilterToPath"
          >
            <span class="text-[var(--text-muted)]">&#9881;</span>
            {{ t('pages.flowEditor.filterToPath') }}
          </button>
        </div>
      </Transition>
    </Teleport>
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

/* Inspector slide-in from right */
.slide-right-enter-active,
.slide-right-leave-active {
  transition: transform 0.25s cubic-bezier(0.25, 0.1, 0.25, 1), opacity 0.2s ease;
}
.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

/* Animated camera fly-to transition */
.flow-animate {
  transition: transform 0.6s cubic-bezier(0.25, 0.1, 0.25, 1);
}

/* Pulsing glow on target node */
@keyframes nodePulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(245, 166, 35, 0);
  }
  50% {
    box-shadow: 0 0 12px 4px rgba(245, 166, 35, 0.4);
  }
}
.node-pulse {
  animation: nodePulse 0.8s ease-in-out 3;
}
</style>
