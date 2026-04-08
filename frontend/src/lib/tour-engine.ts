/**
 * Tour Engine — Core type definitions for the HUBEX guided tour system.
 *
 * Tours navigate users through the app, spotlighting elements and explaining
 * features step-by-step. This module defines the data structures only;
 * runtime logic lives in `stores/tour.ts`.
 */

/* ---------- Step definition ---------- */

export type TourAction =
  | "spotlight"
  | "spotlight+pulse"
  | "zoom"
  | "fly-to"
  | "highlight-path"
  | "info";

export type TooltipPosition = "top" | "bottom" | "left" | "right" | "center";

export interface TourStep {
  /** Unique step identifier (used for bookmarks / analytics). */
  id: string;

  /** Route to navigate to. When omitted the tour stays on the current page. */
  page?: string;

  /** CSS selector for the element to spotlight. */
  target?: string;

  /** Visual action for this step. */
  action: TourAction;

  /** Step title (i18n key or plain text). */
  title: string;

  /** Step description (i18n key or plain text). */
  text: string;

  /** Tooltip position relative to target. */
  position: TooltipPosition;

  /** Delay before showing this step (ms). @default 500 */
  delay?: number;

  /**
   * Auto-advance after N ms. When omitted the store calculates a duration
   * based on text length (~50 ms per character, clamped 3 000 – 8 000).
   */
  duration?: number;

  /** Callback when step activates. */
  onEnter?: () => void;

  /** Callback when step deactivates. */
  onLeave?: () => void;

  /* --- System Map / node-graph extensions --- */

  /** Node ID to fly-to on the System Map canvas. */
  flyToNode?: string;

  /** Whether to highlight the connected path on the System Map. */
  highlightPath?: boolean;
}

/* ---------- Tour definition ---------- */

export type TourCategory = "builtin" | "custom" | "plugin";

export interface TourDefinition {
  /** Unique tour identifier. */
  id: string;

  /** Display name shown in the tour selector. */
  name: string;

  /** Short description of what the tour covers. */
  description: string;

  /** Optional icon identifier for the tour selector card. */
  icon?: string;

  /** Ordered list of steps. */
  steps: TourStep[];

  /** Origin / category. */
  category: TourCategory;

  /** Whether the tour auto-plays by default. @default true */
  autoplay: boolean;

  /**
   * Base interval between steps in ms.
   * The store adjusts per step based on text length.
   * @default 4000
   */
  autoplayInterval: number;
}

/* ---------- Helpers ---------- */

/**
 * Calculates a readable duration for a step based on its text length.
 * Roughly 50 ms per character, clamped between 3 s and 8 s.
 */
export function calcStepDuration(step: TourStep): number {
  if (step.duration != null) return step.duration;
  const chars = step.title.length + step.text.length;
  return Math.max(3000, Math.min(8000, chars * 50));
}

/**
 * Resolves the bounding rect of a target element on screen.
 * Returns `null` when the element is not (yet) in the DOM.
 */
export function resolveTargetRect(selector: string | undefined): DOMRect | null {
  if (!selector) return null;
  const el = document.querySelector(selector);
  if (!el) return null;
  return el.getBoundingClientRect();
}

/**
 * Waits until a CSS selector matches an element in the DOM, up to `timeout` ms.
 * Resolves with the element or `null` on timeout.
 */
export function waitForElement(
  selector: string,
  timeout = 5000,
): Promise<Element | null> {
  return new Promise((resolve) => {
    const existing = document.querySelector(selector);
    if (existing) {
      resolve(existing);
      return;
    }

    const observer = new MutationObserver(() => {
      const el = document.querySelector(selector);
      if (el) {
        observer.disconnect();
        resolve(el);
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });

    setTimeout(() => {
      observer.disconnect();
      resolve(document.querySelector(selector));
    }, timeout);
  });
}
