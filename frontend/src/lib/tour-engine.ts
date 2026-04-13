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
 * Calculates a comfortable reading duration for a step.
 *
 * Formula: 4s base (orient to spotlight) + 300ms per word.
 * Average reading speed is ~250ms/word; we add 20% buffer.
 * Clamped between 8s minimum and 45s maximum.
 */
export function calcStepDuration(step: TourStep): number {
  if (step.duration != null) return step.duration;
  const fullText = `${step.title} ${step.text}`;
  const wordCount = fullText.trim().split(/\s+/).length;
  return Math.max(8000, Math.min(45000, 4000 + wordCount * 300));
}

/**
 * Resolves the bounding rect of a target element on screen.
 * Returns `null` when the element is not (yet) in the DOM.
 *
 * For sidebar nav items (`[data-tour="nav-*"]`), this function will:
 * 1. Expand any collapsed sidebar group containing the item
 * 2. Scroll the sidebar to make the item visible
 * 3. Wait briefly for the scroll animation before measuring
 */
export async function resolveTargetRect(selector: string | undefined): Promise<DOMRect | null> {
  if (!selector) return null;

  let el = document.querySelector(selector);

  // If targeting a sidebar nav item, ensure it's visible
  if (selector.includes('data-tour') && selector.includes('nav-')) {
    // Find the sidebar scroll container
    const sidebar = document.querySelector('aside, nav, .sidebar, [class*="sidebar"]');

    if (el) {
      // Scroll the element into view within the sidebar
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // Wait for scroll animation
      await new Promise(r => setTimeout(r, 400));
    } else if (sidebar) {
      // Element might be hidden inside a collapsed group — try scrolling sidebar down
      sidebar.scrollTop = sidebar.scrollHeight;
      await new Promise(r => setTimeout(r, 300));
      el = document.querySelector(selector);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        await new Promise(r => setTimeout(r, 400));
      }
    }
  } else if (el) {
    // Non-sidebar elements: also scroll into view for below-the-fold items
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    await new Promise(r => setTimeout(r, 200));
  }

  if (!el) {
    // Final attempt after all scrolling
    el = document.querySelector(selector);
  }

  return el?.getBoundingClientRect() ?? null;
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
