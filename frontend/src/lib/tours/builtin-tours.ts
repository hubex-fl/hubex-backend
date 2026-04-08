/**
 * Built-in Tour Definitions for HUBEX
 *
 * Four guided tours:
 *  1. getting-started  — Onboarding: walk new users through the entire system
 *  2. data-path-trace  — Trace data flow from device to action on the System Map
 *  3. dashboard-present — Dynamic: present each widget on the current dashboard
 *  4. alert-investigation — Trace an alert back to its root cause
 *
 * All titles / texts use i18n keys resolved at runtime via `t()`.
 */

import type { TourDefinition, TourStep } from "../tour-engine";

/* ─────────────────────────────────────────────────────────────────────────────
 * 1. Onboarding Tour  ("getting-started")
 * ────────────────────────────────────────────────────────────────────────── */

const onboardingSteps: TourStep[] = [
  {
    id: "welcome",
    page: "/",
    action: "info",
    position: "center",
    title: "tours.onboarding.steps.welcome.title",
    text: "tours.onboarding.steps.welcome.text",
  },
  {
    id: "dashboard-kpis",
    page: "/",
    target: ".grid.grid-cols-2.lg\\:grid-cols-4",
    action: "spotlight",
    position: "bottom",
    title: "tours.onboarding.steps.dashboardKpis.title",
    text: "tours.onboarding.steps.dashboardKpis.text",
  },
  {
    id: "devices-page",
    page: "/devices",
    target: "h1, [data-tour='page-header']",
    action: "spotlight+pulse",
    position: "bottom",
    title: "tours.onboarding.steps.devices.title",
    text: "tours.onboarding.steps.devices.text",
    delay: 600,
  },
  {
    id: "add-device",
    page: "/devices",
    target: "button[data-tour='add-device'], .page-header button:last-child, header button",
    action: "spotlight+pulse",
    position: "bottom",
    title: "tours.onboarding.steps.addDevice.title",
    text: "tours.onboarding.steps.addDevice.text",
  },
  {
    id: "variables",
    page: "/variables",
    target: ".space-y-6, [data-tour='variable-list'], main",
    action: "spotlight",
    position: "bottom",
    title: "tours.onboarding.steps.variables.title",
    text: "tours.onboarding.steps.variables.text",
    delay: 600,
  },
  {
    id: "automations",
    page: "/automations",
    target: "h1, [data-tour='page-header']",
    action: "spotlight",
    position: "bottom",
    title: "tours.onboarding.steps.automations.title",
    text: "tours.onboarding.steps.automations.text",
    delay: 600,
  },
  {
    id: "system-map",
    page: "/flow-editor",
    target: ".vue-flow, [data-tour='canvas'], main",
    action: "spotlight",
    position: "top",
    title: "tours.onboarding.steps.systemMap.title",
    text: "tours.onboarding.steps.systemMap.text",
    delay: 800,
  },
  {
    id: "dashboards",
    page: "/dashboards",
    target: "h1, [data-tour='page-header']",
    action: "spotlight",
    position: "bottom",
    title: "tours.onboarding.steps.dashboards.title",
    text: "tours.onboarding.steps.dashboards.text",
    delay: 600,
  },
  {
    id: "settings",
    page: "/settings",
    target: "h1, [data-tour='page-header'], main",
    action: "spotlight",
    position: "bottom",
    title: "tours.onboarding.steps.settings.title",
    text: "tours.onboarding.steps.settings.text",
    delay: 600,
  },
  {
    id: "done",
    action: "info",
    position: "center",
    title: "tours.onboarding.steps.done.title",
    text: "tours.onboarding.steps.done.text",
  },
];

export const onboardingTour: TourDefinition = {
  id: "getting-started",
  name: "tours.onboarding.name",
  description: "tours.onboarding.description",
  icon: "rocket",
  steps: onboardingSteps,
  category: "builtin",
  autoplay: true,
  autoplayInterval: 5000,
};

/* ─────────────────────────────────────────────────────────────────────────────
 * 2. Data Path Trace  ("data-path-trace")
 * ────────────────────────────────────────────────────────────────────────── */

const dataPathSteps: TourStep[] = [
  {
    id: "intro",
    action: "info",
    position: "center",
    title: "tours.dataPath.steps.intro.title",
    text: "tours.dataPath.steps.intro.text",
  },
  {
    id: "device-node",
    page: "/flow-editor",
    action: "fly-to",
    position: "right",
    title: "tours.dataPath.steps.device.title",
    text: "tours.dataPath.steps.device.text",
    flyToNode: "__first_device__",
    delay: 800,
  },
  {
    id: "variable-node",
    action: "fly-to",
    position: "right",
    title: "tours.dataPath.steps.variables.title",
    text: "tours.dataPath.steps.variables.text",
    highlightPath: true,
  },
  {
    id: "automation-node",
    action: "fly-to",
    position: "right",
    title: "tours.dataPath.steps.automations.title",
    text: "tours.dataPath.steps.automations.text",
    highlightPath: true,
  },
  {
    id: "output-node",
    action: "fly-to",
    position: "left",
    title: "tours.dataPath.steps.outputs.title",
    text: "tours.dataPath.steps.outputs.text",
    highlightPath: true,
  },
  {
    id: "done",
    action: "info",
    position: "center",
    title: "tours.dataPath.steps.done.title",
    text: "tours.dataPath.steps.done.text",
  },
];

export const dataPathTour: TourDefinition = {
  id: "data-path-trace",
  name: "tours.dataPath.name",
  description: "tours.dataPath.description",
  icon: "route",
  steps: dataPathSteps,
  category: "builtin",
  autoplay: true,
  autoplayInterval: 5000,
};

/* ─────────────────────────────────────────────────────────────────────────────
 * 3. Dashboard Presentation  ("dashboard-present")
 *
 * This tour is DYNAMIC — the step list is generated at runtime from the
 * current dashboard's widgets.  `buildDashboardPresentTour()` returns a
 * fresh TourDefinition each time it is called.
 * ────────────────────────────────────────────────────────────────────────── */

export interface DashboardWidget {
  id: string | number;
  label: string;
  value?: string;
  description?: string;
}

/**
 * Build a presentation tour for the given list of dashboard widgets.
 * Called dynamically when the user starts this tour from a dashboard view.
 */
export function buildDashboardPresentTour(
  widgets: DashboardWidget[],
): TourDefinition {
  const steps: TourStep[] = [
    {
      id: "intro",
      action: "info",
      position: "center",
      title: "tours.dashboardPresent.steps.intro.title",
      text: "tours.dashboardPresent.steps.intro.text",
    },
  ];

  widgets.forEach((w, idx) => {
    steps.push({
      id: `widget-${w.id}`,
      target: `[data-widget-id="${w.id}"], .dashboard-widget:nth-child(${idx + 1})`,
      action: "spotlight",
      position: idx % 2 === 0 ? "bottom" : "top",
      title: w.label,
      text: w.description || (w.value ? `Current value: ${w.value}` : "Live widget"),
    });
  });

  steps.push({
    id: "done",
    action: "info",
    position: "center",
    title: "tours.dashboardPresent.steps.done.title",
    text: "tours.dashboardPresent.steps.done.text",
  });

  return {
    id: "dashboard-present",
    name: "tours.dashboardPresent.name",
    description: "tours.dashboardPresent.description",
    icon: "presentation",
    steps,
    category: "builtin",
    autoplay: true,
    autoplayInterval: 4000,
  };
}

/** Static placeholder definition used for the tour selector UI. */
export const dashboardPresentTour: TourDefinition = {
  id: "dashboard-present",
  name: "tours.dashboardPresent.name",
  description: "tours.dashboardPresent.description",
  icon: "presentation",
  steps: [
    {
      id: "intro",
      action: "info",
      position: "center",
      title: "tours.dashboardPresent.steps.intro.title",
      text: "tours.dashboardPresent.steps.intro.text",
    },
    {
      id: "done",
      action: "info",
      position: "center",
      title: "tours.dashboardPresent.steps.done.title",
      text: "tours.dashboardPresent.steps.done.text",
    },
  ],
  category: "builtin",
  autoplay: true,
  autoplayInterval: 4000,
};

/* ─────────────────────────────────────────────────────────────────────────────
 * 4. Alert Investigation  ("alert-investigation")
 * ────────────────────────────────────────────────────────────────────────── */

const alertInvestigationSteps: TourStep[] = [
  {
    id: "alert-event",
    page: "/alerts",
    target: "[data-tour='alert-event'], .alert-event-card, table tbody tr:first-child",
    action: "spotlight+pulse",
    position: "bottom",
    title: "tours.alertInvestigation.steps.alertEvent.title",
    text: "tours.alertInvestigation.steps.alertEvent.text",
  },
  {
    id: "alert-rule",
    target: "[data-tour='alert-rule'], .alert-rule-config",
    action: "spotlight",
    position: "bottom",
    title: "tours.alertInvestigation.steps.alertRule.title",
    text: "tours.alertInvestigation.steps.alertRule.text",
  },
  {
    id: "variable-history",
    page: "/variables",
    target: "[data-tour='variable-chart'], .sparkline, canvas",
    action: "spotlight",
    position: "top",
    title: "tours.alertInvestigation.steps.variableHistory.title",
    text: "tours.alertInvestigation.steps.variableHistory.text",
    delay: 600,
  },
  {
    id: "device-source",
    target: "[data-tour='device-detail'], .device-header, h1",
    action: "spotlight",
    position: "bottom",
    title: "tours.alertInvestigation.steps.deviceSource.title",
    text: "tours.alertInvestigation.steps.deviceSource.text",
  },
  {
    id: "resolution",
    action: "info",
    position: "center",
    title: "tours.alertInvestigation.steps.resolution.title",
    text: "tours.alertInvestigation.steps.resolution.text",
  },
];

export const alertInvestigationTour: TourDefinition = {
  id: "alert-investigation",
  name: "tours.alertInvestigation.name",
  description: "tours.alertInvestigation.description",
  icon: "search",
  steps: alertInvestigationSteps,
  category: "builtin",
  autoplay: false,
  autoplayInterval: 5000,
};

/* ─────────────────────────────────────────────────────────────────────────────
 * Registration
 * ────────────────────────────────────────────────────────────────────────── */

/** All static built-in tour definitions (excluding dynamic dashboard-present). */
export const builtinTours: TourDefinition[] = [
  onboardingTour,
  dataPathTour,
  dashboardPresentTour,
  alertInvestigationTour,
];

/**
 * Register all built-in tours with the tour store.
 * Call this once during app initialization (e.g. in DefaultLayout.vue onMounted).
 *
 * The function accepts a `register` callback so it stays decoupled from
 * the store implementation. Usage:
 *
 * ```ts
 * import { useTourStore } from '@/stores/tour';
 * import { registerBuiltinTours } from '@/lib/tours/builtin-tours';
 *
 * const tourStore = useTourStore();
 * registerBuiltinTours((tour) => tourStore.register(tour));
 * ```
 */
export function registerBuiltinTours(
  register: (tour: TourDefinition) => void,
): void {
  for (const tour of builtinTours) {
    register(tour);
  }
}
