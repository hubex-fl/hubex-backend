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
  // -- Navigate to Devices: highlight sidebar nav first
  {
    id: "nav-devices",
    page: "/",
    target: "[data-tour='nav-devices']",
    action: "spotlight+pulse",
    position: "right",
    title: "tours.onboarding.steps.navDevices.title",
    text: "tours.onboarding.steps.navDevices.text",
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
    target: "[data-tour='add-device']",
    action: "spotlight+pulse",
    position: "bottom",
    title: "tours.onboarding.steps.addDevice.title",
    text: "tours.onboarding.steps.addDevice.text",
  },
  // -- Navigate to Variables: highlight sidebar nav first
  {
    id: "nav-variables",
    page: "/devices",
    target: "[data-tour='nav-variables']",
    action: "spotlight+pulse",
    position: "right",
    title: "tours.onboarding.steps.navVariables.title",
    text: "tours.onboarding.steps.navVariables.text",
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
  // -- Navigate to Automations: highlight sidebar nav first
  {
    id: "nav-automations",
    page: "/variables",
    target: "[data-tour='nav-automations']",
    action: "spotlight+pulse",
    position: "right",
    title: "tours.onboarding.steps.navAutomations.title",
    text: "tours.onboarding.steps.navAutomations.text",
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
  // -- Navigate to System Map: highlight sidebar nav first
  {
    id: "nav-system-map",
    page: "/automations",
    target: "[data-tour='nav-flow-editor']",
    action: "spotlight+pulse",
    position: "right",
    title: "tours.onboarding.steps.navSystemMap.title",
    text: "tours.onboarding.steps.navSystemMap.text",
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
  // -- Navigate to Dashboards: highlight sidebar nav first
  {
    id: "nav-dashboards",
    page: "/flow-editor",
    target: "[data-tour='nav-dashboards']",
    action: "spotlight+pulse",
    position: "right",
    title: "tours.onboarding.steps.navDashboards.title",
    text: "tours.onboarding.steps.navDashboards.text",
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
  // -- Navigate to Settings: highlight sidebar nav first
  {
    id: "nav-settings",
    page: "/dashboards",
    target: "[data-tour='nav-settings']",
    action: "spotlight+pulse",
    position: "right",
    title: "tours.onboarding.steps.navSettings.title",
    text: "tours.onboarding.steps.navSettings.text",
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
  // Sprint 10 E1: extended tour — alerts, entities, sandbox, dark mode, tour guide
  // -- Navigate to Alerts
  {
    id: "nav-alerts",
    page: "/settings",
    target: "[data-tour='nav-alerts']",
    action: "spotlight+pulse",
    position: "right",
    title: "tours.onboarding.steps.navAlerts.title",
    text: "tours.onboarding.steps.navAlerts.text",
  },
  {
    id: "alerts-page",
    page: "/alerts",
    target: "h1, [data-tour='page-header']",
    action: "spotlight",
    position: "bottom",
    title: "tours.onboarding.steps.alerts.title",
    text: "tours.onboarding.steps.alerts.text",
    delay: 600,
  },
  // -- Entities
  {
    id: "nav-entities",
    page: "/alerts",
    target: "[data-tour='nav-entities']",
    action: "spotlight+pulse",
    position: "right",
    title: "tours.onboarding.steps.navEntities.title",
    text: "tours.onboarding.steps.navEntities.text",
  },
  {
    id: "entities-page",
    page: "/entities",
    target: "h1, main",
    action: "spotlight",
    position: "bottom",
    title: "tours.onboarding.steps.entities.title",
    text: "tours.onboarding.steps.entities.text",
    delay: 600,
  },
  // -- Sandbox
  {
    id: "nav-sandbox",
    page: "/entities",
    target: "[data-tour='nav-sandbox']",
    action: "spotlight+pulse",
    position: "right",
    title: "tours.onboarding.steps.navSandbox.title",
    text: "tours.onboarding.steps.navSandbox.text",
  },
  {
    id: "sandbox-page",
    page: "/sandbox",
    target: "h1, main",
    action: "spotlight",
    position: "bottom",
    title: "tours.onboarding.steps.sandbox.title",
    text: "tours.onboarding.steps.sandbox.text",
    delay: 600,
  },
  // -- Dark/Light mode toggle
  {
    id: "theme-toggle",
    page: "/sandbox",
    target: "[data-tour='theme-toggle'], button:has(svg[viewBox='0 0 24 24'])",
    action: "spotlight+pulse",
    position: "bottom",
    title: "tours.onboarding.steps.themeToggle.title",
    text: "tours.onboarding.steps.themeToggle.text",
  },
  // -- Tour Guide button
  {
    id: "tour-launcher",
    page: "/sandbox",
    target: "[data-tour='tour-launcher']",
    action: "spotlight+pulse",
    position: "bottom",
    title: "tours.onboarding.steps.tourLauncher.title",
    text: "tours.onboarding.steps.tourLauncher.text",
  },
  // -- Done
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
 * 1b. Tester Tour  ("tester-welcome")
 *
 * Sprint 10 E1: tailored for test-instance users. Explains what they
 * CAN do (devices, simulators, dashboards, automations) and what they
 * CANNOT (publish CMS, config, admin, webhooks). Short and focused.
 * ────────────────────────────────────────────────────────────────────────── */

const testerSteps: TourStep[] = [
  {
    id: "welcome",
    page: "/",
    action: "info",
    position: "center",
    title: "tours.tester.steps.welcome.title",
    text: "tours.tester.steps.welcome.text",
  },
  {
    id: "sandbox",
    page: "/sandbox",
    target: "h1, main",
    action: "spotlight",
    position: "bottom",
    title: "tours.tester.steps.sandbox.title",
    text: "tours.tester.steps.sandbox.text",
    delay: 600,
  },
  {
    id: "devices",
    page: "/devices",
    target: "h1, main",
    action: "spotlight",
    position: "bottom",
    title: "tours.tester.steps.devices.title",
    text: "tours.tester.steps.devices.text",
    delay: 600,
  },
  {
    id: "variables",
    page: "/variables",
    target: "h1, main",
    action: "spotlight",
    position: "bottom",
    title: "tours.tester.steps.variables.title",
    text: "tours.tester.steps.variables.text",
    delay: 600,
  },
  {
    id: "limits",
    action: "info",
    position: "center",
    title: "tours.tester.steps.limits.title",
    text: "tours.tester.steps.limits.text",
  },
  {
    id: "done",
    action: "info",
    position: "center",
    title: "tours.tester.steps.done.title",
    text: "tours.tester.steps.done.text",
  },
];

export const testerTour: TourDefinition = {
  id: "tester-welcome",
  name: "tours.tester.name",
  description: "tours.tester.description",
  icon: "flask",
  steps: testerSteps,
  category: "builtin",
  autoplay: false,
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

/* ─────────────────────────────────────────────────────────────────────────────
 * 5. Devices Overview  ("devices-overview")
 *
 * Sprint 8 R4 Bucket C F09: short inline tour that fires from the
 * UInfoTooltip on /devices. Explains the category filter, the row
 * indicators, and the add-device wizard.
 * ────────────────────────────────────────────────────────────────────────── */

const devicesOverviewSteps: TourStep[] = [
  {
    id: "intro",
    page: "/devices",
    action: "info",
    position: "center",
    title: "tours.devicesOverview.steps.intro.title",
    text: "tours.devicesOverview.steps.intro.text",
  },
  {
    id: "add-device",
    page: "/devices",
    target: "[data-tour='add-device']",
    action: "spotlight+pulse",
    position: "left",
    title: "tours.devicesOverview.steps.addDevice.title",
    text: "tours.devicesOverview.steps.addDevice.text",
  },
  {
    id: "row-indicator",
    page: "/devices",
    target: "tbody tr:first-child",
    action: "spotlight",
    position: "top",
    title: "tours.devicesOverview.steps.rowIndicator.title",
    text: "tours.devicesOverview.steps.rowIndicator.text",
  },
  {
    id: "done",
    action: "info",
    position: "center",
    title: "tours.devicesOverview.steps.done.title",
    text: "tours.devicesOverview.steps.done.text",
  },
];

export const devicesOverviewTour: TourDefinition = {
  id: "devices-overview",
  name: "tours.devicesOverview.name",
  description: "tours.devicesOverview.description",
  icon: "cpu",
  steps: devicesOverviewSteps,
  category: "builtin",
  autoplay: false,
  // TourDefinition requires autoplayInterval even when autoplay is false;
  // this value is unused because autoplay is off but satisfies the type.
  autoplayInterval: 5000,
};

/* ─────────────────────────────────────────────────────────────────────────────
 * 6. Automations Overview  ("automations-overview")
 * ────────────────────────────────────────────────────────────────────────── */

const automationsOverviewSteps: TourStep[] = [
  {
    id: "intro",
    page: "/automations",
    action: "info",
    position: "center",
    title: "tours.automationsOverview.steps.intro.title",
    text: "tours.automationsOverview.steps.intro.text",
  },
  {
    id: "create",
    page: "/automations",
    target: "[data-tour='create-automation'], button:has(+ span)",
    action: "spotlight+pulse",
    position: "left",
    title: "tours.automationsOverview.steps.create.title",
    text: "tours.automationsOverview.steps.create.text",
  },
  {
    id: "list",
    page: "/automations",
    action: "info",
    position: "center",
    title: "tours.automationsOverview.steps.list.title",
    text: "tours.automationsOverview.steps.list.text",
  },
];

export const automationsOverviewTour: TourDefinition = {
  id: "automations-overview",
  name: "tours.automationsOverview.name",
  description: "tours.automationsOverview.description",
  icon: "zap",
  steps: automationsOverviewSteps,
  category: "builtin",
  autoplay: false,
  autoplayInterval: 5000,
};

/* ─────────────────────────────────────────────────────────────────────────────
 * 7. Variables Overview  ("variables-overview")
 * ────────────────────────────────────────────────────────────────────────── */

const variablesOverviewSteps: TourStep[] = [
  {
    id: "intro",
    page: "/variables",
    action: "info",
    position: "center",
    title: "tours.variablesOverview.steps.intro.title",
    text: "tours.variablesOverview.steps.intro.text",
  },
  {
    id: "filters",
    page: "/variables",
    action: "info",
    position: "center",
    title: "tours.variablesOverview.steps.filters.title",
    text: "tours.variablesOverview.steps.filters.text",
  },
  {
    id: "done",
    page: "/variables",
    action: "info",
    position: "center",
    title: "tours.variablesOverview.steps.done.title",
    text: "tours.variablesOverview.steps.done.text",
  },
];

export const variablesOverviewTour: TourDefinition = {
  id: "variables-overview",
  name: "tours.variablesOverview.name",
  description: "tours.variablesOverview.description",
  icon: "database",
  steps: variablesOverviewSteps,
  category: "builtin",
  autoplay: false,
  autoplayInterval: 5000,
};

/** All static built-in tour definitions (excluding dynamic dashboard-present). */
export const builtinTours: TourDefinition[] = [
  onboardingTour,
  testerTour,         // Sprint 10 E1: test-instance specific tour
  dataPathTour,
  dashboardPresentTour,
  alertInvestigationTour,
  // Sprint 8 F09: inline "Erklärung" tours for the top-level pages.
  devicesOverviewTour,
  automationsOverviewTour,
  variablesOverviewTour,
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
