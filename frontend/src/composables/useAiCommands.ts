/**
 * useAiCommands — AI Coop command dispatcher.
 *
 * Receives "ui_command" messages from the WebSocket and executes them
 * in the browser: navigate, start tours, highlight elements, etc.
 * Also maintains a reactive log of recent AI actions for the indicator.
 */
import { ref, type Ref } from "vue";
import router from "../router";
import { useTourStore } from "../stores/tour";
import { useToastStore, type ToastVariant } from "../stores/toast";

// ---- Module-level singleton state ----

export interface AiAction {
  id: number;
  command: string;
  summary: string;
  ts: number; // Date.now()
}

let _counter = 0;
const recentActions: Ref<AiAction[]> = ref([]);
const lastCommandTs: Ref<number> = ref(0);

const MAX_LOG = 30;

function logAction(command: string, summary: string) {
  const action: AiAction = {
    id: ++_counter,
    command,
    summary,
    ts: Date.now(),
  };
  recentActions.value.unshift(action);
  if (recentActions.value.length > MAX_LOG) {
    recentActions.value.pop();
  }
  lastCommandTs.value = Date.now();
}

// ---- Spotlight helper ----

function spotlightElement(selector: string, message?: string, durationSec = 3) {
  const el = document.querySelector(selector) as HTMLElement | null;
  if (!el) return;

  // Create overlay backdrop
  const overlay = document.createElement("div");
  overlay.className = "ai-spotlight-overlay";
  Object.assign(overlay.style, {
    position: "fixed",
    inset: "0",
    background: "rgba(0,0,0,0.55)",
    zIndex: "9998",
    pointerEvents: "none",
    transition: "opacity 0.3s",
  });

  // Create highlight ring
  const ring = document.createElement("div");
  ring.className = "ai-spotlight-ring";
  const rect = el.getBoundingClientRect();
  const pad = 8;
  Object.assign(ring.style, {
    position: "fixed",
    left: `${rect.left - pad}px`,
    top: `${rect.top - pad}px`,
    width: `${rect.width + pad * 2}px`,
    height: `${rect.height + pad * 2}px`,
    border: "2px solid #F5A623",
    borderRadius: "8px",
    boxShadow: "0 0 0 9999px rgba(0,0,0,0.55), 0 0 20px rgba(245,166,35,0.4)",
    zIndex: "9999",
    pointerEvents: "none",
    transition: "opacity 0.3s",
  });

  // Optional tooltip
  let tooltip: HTMLDivElement | null = null;
  if (message) {
    tooltip = document.createElement("div");
    tooltip.className = "ai-spotlight-tooltip";
    tooltip.textContent = message;
    Object.assign(tooltip.style, {
      position: "fixed",
      left: `${rect.left}px`,
      top: `${rect.bottom + pad + 8}px`,
      background: "#1c1c1a",
      color: "#e5e5e3",
      padding: "6px 12px",
      borderRadius: "6px",
      fontSize: "13px",
      fontFamily: "Inter, sans-serif",
      border: "1px solid #333",
      zIndex: "9999",
      pointerEvents: "none",
      maxWidth: "280px",
    });
  }

  document.body.appendChild(overlay);
  document.body.appendChild(ring);
  if (tooltip) document.body.appendChild(tooltip);

  setTimeout(() => {
    overlay.style.opacity = "0";
    ring.style.opacity = "0";
    if (tooltip) tooltip.style.opacity = "0";
    setTimeout(() => {
      overlay.remove();
      ring.remove();
      tooltip?.remove();
    }, 350);
  }, durationSec * 1000);
}

// ---- Camera zoom/pan handler ----

/**
 * Zoom a viewport element so a target child element lands centered on screen
 * at the requested scale factor.
 *
 * Sprint 3.4 bugfix — the previous implementation had multiple fundamental
 * issues that made every previous "camera zoom fix" commit unreliable:
 *
 *   1. It called `el.scrollIntoView()` BEFORE applying scale. scroll gives
 *      the element a position in the pre-scale layout. Then transform:scale
 *      was applied with origin "center center" — but "center center" is
 *      the center of the VIEWPORT, not of the element, so the element
 *      ends up off-center (sometimes off-screen entirely).
 *   2. Setting overflow:hidden on the viewport after the scale prevents
 *      the user from ever scrolling away from the zoomed area — brittle.
 *   3. No reset of transform/overflow/transition on subsequent zoom calls
 *      leaked state between invocations.
 *
 * New approach (math-based, reliable):
 *   - Compute the target element's center in the viewport's coordinate
 *     space BEFORE any transform (via getBoundingClientRect of both).
 *   - Compute the translation needed to move that center to the viewport
 *     center.
 *   - Compose `translate(...) scale(N)` with `transform-origin: 0 0` so the
 *     math is predictable (scale around top-left, translate to position).
 *   - Do it all in one transform update so the CSS transition animates
 *     the element straight to the focused position, smoothly.
 */
function handleCamera(payload: Record<string, unknown>) {
  const action = payload.action as string;
  const duration = (payload.duration as number) || 800;

  // Zoom the main content viewport (not sidebar, not body)
  const vp = (document.getElementById("camera-viewport") ||
    document.querySelector("main") || document.body) as HTMLElement;

  // Single easing curve for all camera actions
  const easing = "cubic-bezier(0.22, 1, 0.36, 1)"; // easeOutQuint feels cinematic
  vp.style.transition = `transform ${duration}ms ${easing}`;
  vp.style.transformOrigin = "0 0";

  if (action === "zoom_to" && payload.selector) {
    const selectors = (payload.selector as string).split(",").map((s) => s.trim());
    let el: Element | null = null;
    for (const sel of selectors) {
      el = document.querySelector(sel);
      if (el) break;
    }
    if (!el) {
      console.warn("[camera] zoom_to: no element matched selector", payload.selector);
      return;
    }

    const zoom = Math.min(Math.max((payload.zoom as number) || 2.0, 1.0), 5.0);

    // Reset any existing transform so getBoundingClientRect measures the
    // un-transformed layout. The browser paints one frame of identity,
    // which is fine — the eased transition from there is invisible.
    vp.style.transform = "";

    // Next frame: measure + apply new transform
    requestAnimationFrame(() => {
      const vpRect = vp.getBoundingClientRect();
      const elRect = (el as HTMLElement).getBoundingClientRect();

      // Center of the target element in viewport-local coordinates
      const elCenterInVp = {
        x: elRect.left - vpRect.left + elRect.width / 2,
        y: elRect.top - vpRect.top + elRect.height / 2,
      };

      // Where we want that center to land: the center of the visible viewport
      const vpCenter = { x: vpRect.width / 2, y: vpRect.height / 2 };

      // With transform-origin at (0,0), a scale(z) maps a point (x,y) to (x*z, y*z).
      // We want elCenter * z + tx = vpCenter  =>  tx = vpCenter - elCenter * z
      const tx = vpCenter.x - elCenterInVp.x * zoom;
      const ty = vpCenter.y - elCenterInVp.y * zoom;

      vp.style.transform = `translate(${tx}px, ${ty}px) scale(${zoom})`;
    });
  } else if (action === "pan_to") {
    const x = (payload.x as number) || 0;
    const y = (payload.y as number) || 0;
    // pan_to accumulates on top of any current scale
    const current = window.getComputedStyle(vp).transform;
    const scaleMatch = /matrix\(([-\d.]+),/.exec(current);
    const currentScale = scaleMatch ? parseFloat(scaleMatch[1]) : 1;
    vp.style.transform = `translate(${x}px, ${y}px) scale(${currentScale})`;
  } else if (action === "reset") {
    vp.style.transform = "";
    // Clear transition AFTER the reset animation finishes so the next
    // direct style assignment doesn't re-animate from zero
    setTimeout(() => {
      vp.style.transition = "";
      vp.style.transformOrigin = "";
    }, duration + 50);
  }
}

// ---- Command handler (call from WS message handler) ----

export function handleAiCommand(command: { command: string; payload: Record<string, unknown> }) {
  // Use the imported router singleton — useRouter() only works in synchronous
  // component setup, but this function is called asynchronously from the
  // WebSocket message handler.
  const tourStore = useTourStore();
  const toast = useToastStore();

  console.log("[ai-coop] Received command:", command.command, "payload:", command.payload);

  switch (command.command) {
    case "navigate": {
      const path = command.payload.path as string;
      router.push(path);
      logAction("navigate", path);
      break;
    }
    case "start_tour": {
      const tourId = command.payload.tour_id as string;
      tourStore.start(tourId);
      logAction("start_tour", tourId);
      break;
    }
    case "highlight": {
      const selector = command.payload.selector as string;
      const message = (command.payload.message as string) || undefined;
      const duration = (command.payload.duration as number) || 3;
      spotlightElement(selector, message, duration);
      logAction("highlight", selector);
      break;
    }
    case "fly_to_node": {
      window.dispatchEvent(
        new CustomEvent("ai-fly-to", { detail: command.payload })
      );
      logAction("fly_to_node", command.payload.node_id as string);
      break;
    }
    case "camera": {
      handleCamera(command.payload);
      logAction("camera", (command.payload.action as string) || "unknown");
      break;
    }
    case "notification": {
      const msg = command.payload.message as string;
      const variant = (command.payload.type as ToastVariant) || "info";
      toast.addToast(msg, variant);
      logAction("notification", msg);
      break;
    }
    case "refresh": {
      window.dispatchEvent(new CustomEvent("ai-refresh"));
      logAction("refresh", "data refresh");
      break;
    }
    default:
      console.warn("[ai-coop] Unknown command:", command.command);
  }
}

// ---- Exported composable ----

export function useAiCommands() {
  return {
    recentActions,
    lastCommandTs,
    handleAiCommand,
  };
}
