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
  // -- Plugins
  {
    id: "nav-plugins",
    page: "/sandbox",
    target: "[data-tour='nav-plugins']",
    action: "spotlight+pulse",
    position: "right",
    title: "tours.onboarding.steps.navPlugins.title",
    text: "tours.onboarding.steps.navPlugins.text",
  },
  // -- CMS
  {
    id: "nav-cms",
    page: "/sandbox",
    target: "[data-tour='nav-cms'] , a[href='/cms']",
    action: "spotlight+pulse",
    position: "right",
    title: "tours.onboarding.steps.navCms.title",
    text: "tours.onboarding.steps.navCms.text",
  },
  // -- Info icons explanation — spotlight an actual info icon on the current page
  {
    id: "info-icons",
    page: "/sandbox",
    target: ".info-trigger",
    action: "spotlight+pulse",
    position: "bottom",
    title: "tours.onboarding.steps.infoIcons.title",
    text: "tours.onboarding.steps.infoIcons.text",
  },
  // -- Dark/Light mode toggle
  {
    id: "theme-toggle",
    page: "/sandbox",
    target: "[data-tour='theme-toggle']",
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
  // -- Feedback button (fixed position bottom-right)
  {
    id: "feedback",
    target: "[data-tour='feedback-button']",
    action: "spotlight+pulse",
    position: "top",
    title: "tours.onboarding.steps.feedback.title",
    text: "tours.onboarding.steps.feedback.text",
  },
  // -- Done — return to dashboard
  {
    id: "done",
    page: "/",
    action: "info",
    position: "center",
    title: "tours.onboarding.steps.done.title",
    text: "tours.onboarding.steps.done.text",
    delay: 600,
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
  // Sprint 10: increased 5s→10s→30s — user says still too fast to read.
  // 30s gives ample time for reading + looking at the highlighted element.
  autoplayInterval: 30000,
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
    target: "[data-tour='alert-event'], .space-y-2 > div:first-child, .space-y-4 > div:nth-child(3), main",
    action: "spotlight+pulse",
    position: "bottom",
    title: "tours.alertInvestigation.steps.alertEvent.title",
    text: "tours.alertInvestigation.steps.alertEvent.text",
  },
  {
    id: "alert-rule",
    page: "/alerts",
    target: "[data-tour='alert-rule'], .space-y-2, .space-y-4 > div:last-child, main",
    action: "spotlight",
    position: "bottom",
    title: "tours.alertInvestigation.steps.alertRule.title",
    text: "tours.alertInvestigation.steps.alertRule.text",
  },
  {
    id: "variable-history",
    page: "/variables",
    target: "[data-tour='variable-chart'], .sparkline, canvas, .vars-table-wrap, main",
    action: "spotlight",
    position: "top",
    title: "tours.alertInvestigation.steps.variableHistory.title",
    text: "tours.alertInvestigation.steps.variableHistory.text",
    delay: 600,
  },
  {
    id: "device-source",
    page: "/devices",
    target: "[data-tour='device-detail'], h1, [data-tour='page-header'], main",
    action: "spotlight",
    position: "bottom",
    title: "tours.alertInvestigation.steps.deviceSource.title",
    text: "tours.alertInvestigation.steps.deviceSource.text",
    delay: 600,
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
    target: "h1",
    action: "spotlight",
    position: "bottom",
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
    target: "table, .space-y-3, main > div:last-child",
    action: "spotlight",
    position: "top",
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
    target: "h1, .vars-title",
    action: "spotlight",
    position: "bottom",
    title: "tours.variablesOverview.steps.intro.title",
    text: "tours.variablesOverview.steps.intro.text",
  },
  {
    id: "table",
    page: "/variables",
    target: ".vars-table-wrap, .vars-table, table, main",
    action: "spotlight",
    position: "top",
    title: "tours.variablesOverview.steps.table.title",
    text: "tours.variablesOverview.steps.table.text",
  },
  {
    id: "scope-filter",
    page: "/variables",
    target: ".toolbar-scope, .vars-toolbar select, .vars-toolbar",
    action: "spotlight+pulse",
    position: "bottom",
    title: "tours.variablesOverview.steps.scopeFilter.title",
    text: "tours.variablesOverview.steps.scopeFilter.text",
  },
  {
    id: "device-filter",
    page: "/variables",
    target: ".toolbar-device, .vars-toolbar .entity-select, .vars-toolbar",
    action: "spotlight+pulse",
    position: "bottom",
    title: "tours.variablesOverview.steps.deviceFilter.title",
    text: "tours.variablesOverview.steps.deviceFilter.text",
  },
  {
    id: "editing",
    page: "/variables",
    target: ".vars-table tbody tr:first-child, .vars-table tr:nth-child(2), table tbody, main",
    action: "spotlight",
    position: "top",
    title: "tours.variablesOverview.steps.editing.title",
    text: "tours.variablesOverview.steps.editing.text",
  },
  {
    id: "done",
    page: "/variables",
    target: ".vars-toolbar, .vars-table-wrap, main",
    action: "spotlight",
    position: "top",
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
/* ─────────────────────────────────────────────────────────────────────────────
 * 8-12. Page-specific inline tours
 * ────────────────────────────────────────────────────────────────────────── */

const entitiesOverviewTour: TourDefinition = {
  id: "entities-overview", name: "tours.entitiesOverview.name",
  description: "tours.entitiesOverview.description", icon: "boxes", category: "builtin",
  autoplay: false, autoplayInterval: 10000,
  steps: [
    { id: "intro", page: "/entities", target: "h1", action: "spotlight", position: "bottom",
      title: "tours.entitiesOverview.steps.intro.title", text: "tours.entitiesOverview.steps.intro.text" },
    { id: "create", page: "/entities", target: "button:last-of-type", action: "spotlight+pulse", position: "left",
      title: "tours.entitiesOverview.steps.create.title", text: "tours.entitiesOverview.steps.create.text" },
    { id: "hierarchy", page: "/entities", action: "info", position: "center",
      title: "tours.entitiesOverview.steps.hierarchy.title", text: "tours.entitiesOverview.steps.hierarchy.text" },
  ],
};

const settingsOverviewTour: TourDefinition = {
  id: "settings-overview", name: "tours.settingsOverview.name",
  description: "tours.settingsOverview.description", icon: "cog", category: "builtin",
  autoplay: false, autoplayInterval: 10000,
  steps: [
    { id: "intro", page: "/settings", target: "h1", action: "spotlight", position: "bottom",
      title: "tours.settingsOverview.steps.intro.title", text: "tours.settingsOverview.steps.intro.text" },
    { id: "search", page: "/settings", target: "input[type='search']", action: "spotlight+pulse", position: "bottom",
      title: "tours.settingsOverview.steps.search.title", text: "tours.settingsOverview.steps.search.text" },
    { id: "sections", page: "/settings", target: ".space-y-2", action: "spotlight", position: "top",
      title: "tours.settingsOverview.steps.sections.title", text: "tours.settingsOverview.steps.sections.text" },
  ],
};

const sandboxOverviewTour: TourDefinition = {
  id: "sandbox-overview", name: "tours.sandboxOverview.name",
  description: "tours.sandboxOverview.description", icon: "flask", category: "builtin",
  autoplay: false, autoplayInterval: 10000,
  steps: [
    { id: "intro", page: "/sandbox", target: "h1", action: "spotlight", position: "bottom",
      title: "tours.sandboxOverview.steps.intro.title", text: "tours.sandboxOverview.steps.intro.text" },
    { id: "templates", page: "/sandbox", action: "info", position: "center",
      title: "tours.sandboxOverview.steps.templates.title", text: "tours.sandboxOverview.steps.templates.text" },
    { id: "create", page: "/sandbox", target: "button", action: "spotlight+pulse", position: "left",
      title: "tours.sandboxOverview.steps.create.title", text: "tours.sandboxOverview.steps.create.text" },
  ],
};

const eventsOverviewTour: TourDefinition = {
  id: "events-overview", name: "tours.eventsOverview.name",
  description: "tours.eventsOverview.description", icon: "list", category: "builtin",
  autoplay: false, autoplayInterval: 10000,
  steps: [
    { id: "intro", page: "/events", target: "h2", action: "spotlight", position: "bottom",
      title: "tours.eventsOverview.steps.intro.title", text: "tours.eventsOverview.steps.intro.text" },
    { id: "stream", page: "/events", target: ".entity-select, select, .flex-col.sm\\:flex-row .flex-1:first-child, main", action: "spotlight+pulse", position: "bottom",
      title: "tours.eventsOverview.steps.stream.title", text: "tours.eventsOverview.steps.stream.text" },
    { id: "controls", page: "/events", target: "table, .overflow-x-auto, .w-full.text-xs, main", action: "spotlight", position: "top",
      title: "tours.eventsOverview.steps.controls.title", text: "tours.eventsOverview.steps.controls.text" },
  ],
};

const cmsOverviewTour: TourDefinition = {
  id: "cms-overview", name: "tours.cmsOverview.name",
  description: "tours.cmsOverview.description", icon: "page", category: "builtin",
  autoplay: false, autoplayInterval: 10000,
  steps: [
    { id: "intro", page: "/cms", target: "h1", action: "spotlight", position: "bottom",
      title: "tours.cmsOverview.steps.intro.title", text: "tours.cmsOverview.steps.intro.text" },
    { id: "create", page: "/cms", target: "button:last-of-type", action: "spotlight+pulse", position: "left",
      title: "tours.cmsOverview.steps.create.title", text: "tours.cmsOverview.steps.create.text" },
    { id: "templates", page: "/cms", action: "info", position: "center",
      title: "tours.cmsOverview.steps.templates.title", text: "tours.cmsOverview.steps.templates.text" },
  ],
};

/* ─────────────────────────────────────────────────────────────────────────────
 * 13-22. Page-specific inline tours (batch 2)
 * ────────────────────────────────────────────────────────────────────────── */

const webhooksOverviewTour: TourDefinition = {
  id: "webhooks-overview", name: "tours.webhooksOverview.name",
  description: "tours.webhooksOverview.description", icon: "globe", category: "builtin",
  autoplay: false, autoplayInterval: 10000,
  steps: [
    { id: "intro", page: "/webhooks", target: "h1", action: "spotlight", position: "bottom",
      title: "tours.webhooksOverview.steps.intro.title", text: "tours.webhooksOverview.steps.intro.text" },
    { id: "create", page: "/webhooks", target: "button:last-of-type", action: "spotlight+pulse", position: "left",
      title: "tours.webhooksOverview.steps.create.title", text: "tours.webhooksOverview.steps.create.text" },
    { id: "deliveries", page: "/webhooks", target: ".space-y-3, main", action: "spotlight", position: "top",
      title: "tours.webhooksOverview.steps.deliveries.title", text: "tours.webhooksOverview.steps.deliveries.text" },
  ],
};

const pluginsOverviewTour: TourDefinition = {
  id: "plugins-overview", name: "tours.pluginsOverview.name",
  description: "tours.pluginsOverview.description", icon: "puzzle", category: "builtin",
  autoplay: false, autoplayInterval: 10000,
  steps: [
    { id: "intro", page: "/plugins", target: "h1", action: "spotlight", position: "bottom",
      title: "tours.pluginsOverview.steps.intro.title", text: "tours.pluginsOverview.steps.intro.text" },
    { id: "install", page: "/plugins", target: "button:last-of-type", action: "spotlight+pulse", position: "left",
      title: "tours.pluginsOverview.steps.install.title", text: "tours.pluginsOverview.steps.install.text" },
    { id: "manage", page: "/plugins", target: ".space-y-3, main", action: "spotlight", position: "top",
      title: "tours.pluginsOverview.steps.manage.title", text: "tours.pluginsOverview.steps.manage.text" },
  ],
};

const hardwareOverviewTour: TourDefinition = {
  id: "hardware-overview", name: "tours.hardwareOverview.name",
  description: "tours.hardwareOverview.description", icon: "chip", category: "builtin",
  autoplay: false, autoplayInterval: 10000,
  steps: [
    { id: "intro", page: "/hardware", target: "h1", action: "spotlight", position: "bottom",
      title: "tours.hardwareOverview.steps.intro.title", text: "tours.hardwareOverview.steps.intro.text" },
    { id: "wizard", page: "/hardware", target: ".wizard-cta-btn", action: "spotlight+pulse", position: "left",
      title: "tours.hardwareOverview.steps.wizard.title", text: "tours.hardwareOverview.steps.wizard.text" },
    { id: "firmware", page: "/hardware", target: ".grid.grid-cols-1, main", action: "spotlight", position: "top",
      title: "tours.hardwareOverview.steps.firmware.title", text: "tours.hardwareOverview.steps.firmware.text" },
  ],
};

const firmwareOverviewTour: TourDefinition = {
  id: "firmware-overview", name: "tours.firmwareOverview.name",
  description: "tours.firmwareOverview.description", icon: "cpu", category: "builtin",
  autoplay: false, autoplayInterval: 10000,
  steps: [
    { id: "intro", page: "/firmware", target: "h1", action: "spotlight", position: "bottom",
      title: "tours.firmwareOverview.steps.intro.title", text: "tours.firmwareOverview.steps.intro.text" },
    { id: "board", page: "/firmware", target: "select", action: "spotlight+pulse", position: "bottom",
      title: "tours.firmwareOverview.steps.board.title", text: "tours.firmwareOverview.steps.board.text" },
    { id: "output", page: "/firmware", target: ".divide-y, main", action: "spotlight", position: "top",
      title: "tours.firmwareOverview.steps.output.title", text: "tours.firmwareOverview.steps.output.text" },
  ],
};

const reportsOverviewTour: TourDefinition = {
  id: "reports-overview", name: "tours.reportsOverview.name",
  description: "tours.reportsOverview.description", icon: "document", category: "builtin",
  autoplay: false, autoplayInterval: 10000,
  steps: [
    { id: "intro", page: "/reports", target: "h1", action: "spotlight", position: "bottom",
      title: "tours.reportsOverview.steps.intro.title", text: "tours.reportsOverview.steps.intro.text" },
    { id: "create", page: "/reports", target: "button:last-of-type", action: "spotlight+pulse", position: "left",
      title: "tours.reportsOverview.steps.create.title", text: "tours.reportsOverview.steps.create.text" },
    { id: "schedule", page: "/reports", target: ".space-y-3, main", action: "spotlight", position: "top",
      title: "tours.reportsOverview.steps.schedule.title", text: "tours.reportsOverview.steps.schedule.text" },
  ],
};

const emailTemplatesOverviewTour: TourDefinition = {
  id: "email-templates-overview", name: "tours.emailTemplatesOverview.name",
  description: "tours.emailTemplatesOverview.description", icon: "mail", category: "builtin",
  autoplay: false, autoplayInterval: 10000,
  steps: [
    { id: "intro", page: "/email-templates", target: "h1", action: "spotlight", position: "bottom",
      title: "tours.emailTemplatesOverview.steps.intro.title", text: "tours.emailTemplatesOverview.steps.intro.text" },
    { id: "editor", page: "/email-templates", target: "button:last-of-type", action: "spotlight+pulse", position: "left",
      title: "tours.emailTemplatesOverview.steps.editor.title", text: "tours.emailTemplatesOverview.steps.editor.text" },
    { id: "variables", page: "/email-templates", target: ".space-y-3, main", action: "spotlight", position: "top",
      title: "tours.emailTemplatesOverview.steps.variables.title", text: "tours.emailTemplatesOverview.steps.variables.text" },
  ],
};

const adminOverviewTour: TourDefinition = {
  id: "admin-overview", name: "tours.adminOverview.name",
  description: "tours.adminOverview.description", icon: "shield", category: "builtin",
  autoplay: false, autoplayInterval: 10000,
  steps: [
    { id: "intro", page: "/admin", target: "h1", action: "spotlight", position: "bottom",
      title: "tours.adminOverview.steps.intro.title", text: "tours.adminOverview.steps.intro.text" },
    { id: "roles", page: "/admin", target: ".grid.grid-cols-1.sm\\:grid-cols-3, .grid", action: "spotlight+pulse", position: "bottom",
      title: "tours.adminOverview.steps.roles.title", text: "tours.adminOverview.steps.roles.text" },
    { id: "caps", page: "/admin", target: ".flex.flex-wrap.gap-1\\.5, main", action: "spotlight", position: "top",
      title: "tours.adminOverview.steps.caps.title", text: "tours.adminOverview.steps.caps.text" },
  ],
};

const healthOverviewTour: TourDefinition = {
  id: "health-overview", name: "tours.healthOverview.name",
  description: "tours.healthOverview.description", icon: "heart", category: "builtin",
  autoplay: false, autoplayInterval: 10000,
  steps: [
    { id: "intro", page: "/system-health", target: "h1", action: "spotlight", position: "bottom",
      title: "tours.healthOverview.steps.intro.title", text: "tours.healthOverview.steps.intro.text" },
    { id: "indicators", page: "/system-health", target: ".grid.grid-cols-1.sm\\:grid-cols-3, .grid", action: "spotlight+pulse", position: "bottom",
      title: "tours.healthOverview.steps.indicators.title", text: "tours.healthOverview.steps.indicators.text" },
    { id: "refresh", page: "/system-health", target: "button:last-of-type", action: "spotlight", position: "left",
      title: "tours.healthOverview.steps.refresh.title", text: "tours.healthOverview.steps.refresh.text" },
  ],
};

const auditOverviewTour: TourDefinition = {
  id: "audit-overview", name: "tours.auditOverview.name",
  description: "tours.auditOverview.description", icon: "clipboard", category: "builtin",
  autoplay: false, autoplayInterval: 10000,
  steps: [
    { id: "intro", page: "/audit", target: "h2", action: "spotlight", position: "bottom",
      title: "tours.auditOverview.steps.intro.title", text: "tours.auditOverview.steps.intro.text" },
    { id: "filters", page: "/audit", target: ".flex.flex-col.sm\\:flex-row, .flex-col", action: "spotlight+pulse", position: "bottom",
      title: "tours.auditOverview.steps.filters.title", text: "tours.auditOverview.steps.filters.text" },
    { id: "export", page: "/audit", target: "a[download], .flex.gap-2", action: "spotlight", position: "left",
      title: "tours.auditOverview.steps.export.title", text: "tours.auditOverview.steps.export.text" },
  ],
};

const traceHubOverviewTour: TourDefinition = {
  id: "trace-hub-overview", name: "tours.traceHubOverview.name",
  description: "tours.traceHubOverview.description", icon: "search", category: "builtin",
  autoplay: false, autoplayInterval: 10000,
  steps: [
    { id: "intro", page: "/trace-hub", target: "h2", action: "spotlight", position: "bottom",
      title: "tours.traceHubOverview.steps.intro.title", text: "tours.traceHubOverview.steps.intro.text" },
    { id: "events", page: "/trace-hub", target: ".form-row, .btn.secondary:first-of-type, .card", action: "spotlight+pulse", position: "bottom",
      title: "tours.traceHubOverview.steps.events.title", text: "tours.traceHubOverview.steps.events.text" },
    { id: "effects", page: "/trace-hub", target: ".form-row, .card", action: "spotlight", position: "bottom",
      title: "tours.traceHubOverview.steps.effects.title", text: "tours.traceHubOverview.steps.effects.text" },
  ],
};

/* ─────────────────────────────────────────────────────────────────────────────
 * Trace Timeline Overview  ("trace-timeline-overview")
 *
 * Referenced by the UInfoTooltip on /trace-timeline.
 * Shows incident summary cards, anomaly detection, the event timeline,
 * and the trace detail panel.
 * ────────────────────────────────────────────────────────────────────────── */

const traceTimelineOverviewTour: TourDefinition = {
  id: "trace-timeline-overview", name: "tours.traceTimelineOverview.name",
  description: "tours.traceTimelineOverview.description", icon: "activity", category: "builtin",
  autoplay: false, autoplayInterval: 10000,
  steps: [
    { id: "intro", page: "/trace-timeline", target: "h1, .text-xl", action: "spotlight", position: "bottom",
      title: "tours.traceTimelineOverview.steps.intro.title", text: "tours.traceTimelineOverview.steps.intro.text" },
    { id: "time-range", page: "/trace-timeline", target: "select, .flex.items-center.gap-2", action: "spotlight+pulse", position: "bottom",
      title: "tours.traceTimelineOverview.steps.timeRange.title", text: "tours.traceTimelineOverview.steps.timeRange.text" },
    { id: "incidents", page: "/trace-timeline", target: ".grid.grid-cols-2.sm\\:grid-cols-4, .grid.grid-cols-2, main", action: "spotlight", position: "bottom",
      title: "tours.traceTimelineOverview.steps.incidents.title", text: "tours.traceTimelineOverview.steps.incidents.text" },
    { id: "anomalies", page: "/trace-timeline", target: ".space-y-2, .rounded-lg.bg-\\[var\\(--status-warn\\)\\], main", action: "spotlight", position: "top",
      title: "tours.traceTimelineOverview.steps.anomalies.title", text: "tours.traceTimelineOverview.steps.anomalies.text" },
    { id: "timeline", page: "/trace-timeline", target: ".space-y-1.max-h-\\[50vh\\], .overflow-y-auto, main", action: "spotlight", position: "top",
      title: "tours.traceTimelineOverview.steps.timeline.title", text: "tours.traceTimelineOverview.steps.timeline.text" },
    { id: "detail", page: "/trace-timeline", target: ".grid.grid-cols-2.gap-2, .space-y-6 > div:last-child, main", action: "spotlight", position: "top",
      title: "tours.traceTimelineOverview.steps.detail.title", text: "tours.traceTimelineOverview.steps.detail.text" },
  ],
};

export const builtinTours: TourDefinition[] = [
  onboardingTour,
  testerTour,
  dataPathTour,
  dashboardPresentTour,
  alertInvestigationTour,
  devicesOverviewTour,
  automationsOverviewTour,
  variablesOverviewTour,
  entitiesOverviewTour,
  settingsOverviewTour,
  sandboxOverviewTour,
  eventsOverviewTour,
  cmsOverviewTour,
  webhooksOverviewTour,
  pluginsOverviewTour,
  hardwareOverviewTour,
  firmwareOverviewTour,
  reportsOverviewTour,
  emailTemplatesOverviewTour,
  adminOverviewTour,
  healthOverviewTour,
  auditOverviewTour,
  traceHubOverviewTour,
  traceTimelineOverviewTour,
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
