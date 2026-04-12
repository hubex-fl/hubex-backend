import { createRouter, createWebHistory } from "vue-router";

function getHomepageDashboardId(): number | null {
  try {
    const raw = localStorage.getItem("hubex_user_prefs");
    if (!raw) return null;
    const prefs = JSON.parse(raw);
    const id = prefs.homepage_dashboard_id;
    return typeof id === "number" ? id : null;
  } catch {
    return null;
  }
}

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(to, _from, savedPosition) {
    // Browser back/forward: restore previous scroll position
    if (savedPosition) return savedPosition;
    // Hash link: scroll to the referenced element
    if (to.hash) return { el: to.hash };
    // Default: scroll to top on navigation
    return { top: 0 };
  },
  routes: [
    {
      path: "/",
      component: () => import("./pages/DashboardPage.vue"),
      meta: { title: "Dashboard", titleKey: "nav.dashboard" },
      beforeEnter: (_to, _from, next) => {
        const dashId = getHomepageDashboardId();
        if (dashId) {
          next({ path: `/dashboards/${dashId}` });
        } else {
          next();
        }
      },
    },
    { path: "/landing",      component: () => import("./pages/Landing.vue"),        meta: { layout: "public", noPublicShell: true, title: "HUBEX — The Universal IoT Device Hub" } },
    { path: "/impressum",    component: () => import("./pages/LegalPage.vue"),      meta: { layout: "public", noPublicShell: true, title: "Impressum" }, props: { page: "impressum" } },
    { path: "/datenschutz",  component: () => import("./pages/LegalPage.vue"),      meta: { layout: "public", noPublicShell: true, title: "Datenschutz" }, props: { page: "datenschutz" } },
    { path: "/login",        component: () => import("./pages/Login.vue"),          meta: { layout: "auth",  title: "Sign In", titleKey: "nav.signIn" } },
    { path: "/system-stage", component: () => import("./pages/SystemStage.vue"),    meta: { title: "System Stage", titleKey: "nav.systemStage" } },
    { path: "/devices",      component: () => import("./pages/Devices.vue"),         meta: { title: "Devices", titleKey: "nav.devices" } },
    { path: "/devices/:id",  component: () => import("./pages/DeviceDetail.vue"),    meta: { title: "Device Detail", titleKey: "nav.deviceDetail" }, name: "device-detail" },
    { path: "/entities",     component: () => import("./pages/EntitiesPage.vue"),    meta: { title: "Entities", titleKey: "nav.entities" } },
    { path: "/events",       component: () => import("./pages/Events.vue"),          meta: { title: "Events", titleKey: "nav.events" } },
    { path: "/alerts",       component: () => import("./pages/Alerts.vue"),          meta: { title: "Alerts", titleKey: "nav.alerts" } },
    { path: "/effects",      component: () => import("./pages/Effects.vue"),         meta: { title: "Effects", titleKey: "nav.effects" } },
    { path: "/trace-hub",    component: () => import("./pages/TraceHub.vue"),        meta: { title: "Trace Hub", titleKey: "nav.traceHub" } },
    { path: "/executions",   component: () => import("./pages/Executions.vue"),      meta: { title: "Executions", titleKey: "nav.executions" } },
    { path: "/audit",        component: () => import("./pages/Audit.vue"),           meta: { title: "Audit Log", titleKey: "nav.auditLog", feature: "audit_log" } },
    // Correlation removed — merged into TraceTimeline
    { path: "/observability",component: () => import("./pages/Observability.vue"),   meta: { title: "Observability", titleKey: "nav.observability", feature: "observability" } },
    { path: "/settings",     component: () => import("./pages/Settings.vue"),        meta: { title: "Settings", titleKey: "nav.settings" } },
    { path: "/settings/auth", redirect: "/settings" },
    { path: "/settings/types", component: () => import("./pages/SemanticTypes.vue"), meta: { title: "Semantic Types", titleKey: "nav.semanticTypes", feature: "semantic_types" } },
    { path: "/setup",        component: () => import("./pages/SetupWizard.vue"),    meta: { title: "Setup", titleKey: "nav.setup", fullscreen: true } },
    { path: "/disabled",     component: () => import("./pages/FeatureDisabled.vue"), meta: { title: "Feature Disabled", titleKey: "nav.featureDisabled" } },
    { path: "/token",        component: () => import("./pages/TokenInspector.vue"),  meta: { title: "Token Inspector", titleKey: "nav.tokenInspector" } },
    { path: "/variables",    component: () => import("./pages/Variables.vue"),       meta: { title: "Variables", titleKey: "nav.variables" } },
    { path: "/variables/streams", component: () => import("./pages/VariableStreams.vue"), meta: { title: "Variable Streams", titleKey: "nav.variableStreams" } },
    { path: "/pairing",      component: () => import("./pages/Pairing.vue"),         meta: { title: "Pairing", titleKey: "nav.pairing", feature: "pairing" } },
    { path: "/system-health", component: () => import("./pages/SystemHealth.vue"),   meta: { title: "System Health", titleKey: "nav.systemHealth" } },
    { path: "/automations",  component: () => import("./pages/Automations.vue"),     meta: { title: "Automations", titleKey: "nav.automations", feature: "automations" } },
    { path: "/developer",    component: () => import("./pages/ApiDocs.vue"),         meta: { title: "API Docs", titleKey: "nav.apiDocs" } },
    { path: "/webhooks",     component: () => import("./pages/Webhooks.vue"),        meta: { title: "Webhooks", titleKey: "nav.webhooks", feature: "webhooks" } },
    { path: "/email-templates", component: () => import("./pages/EmailTemplates.vue"), meta: { title: "Email Templates", titleKey: "nav.emailTemplates", feature: "email_templates" } },
    { path: "/admin",          component: () => import("./pages/AdminConsole.vue"),   meta: { title: "Admin Console", titleKey: "nav.adminConsole" } },
    { path: "/custom-api",    component: () => import("./pages/CustomApiBuilder.vue"), meta: { title: "Custom API", titleKey: "nav.customApi", feature: "custom_api" } },
    { path: "/trace-timeline", component: () => import("./pages/TraceTimeline.vue"),  meta: { title: "Trace Timeline", titleKey: "nav.traceTimeline" } },
    { path: "/reports",       component: () => import("./pages/Reports.vue"),        meta: { title: "Reports", titleKey: "nav.reports", feature: "reports" } },
    { path: "/plugins",       component: () => import("./pages/Plugins.vue"),        meta: { title: "Plugins", titleKey: "nav.plugins", feature: "plugins" } },
    { path: "/plugins/:key/embed", component: () => import("./pages/PluginEmbed.vue"), meta: { title: "Plugin", titleKey: "nav.plugin", feature: "plugins", fullscreen: true } },
    { path: "/hardware",      component: () => import("./pages/HardwareBoards.vue"), meta: { title: "Hardware Boards", titleKey: "nav.hardwareBoards", feature: "hardware" } },
    { path: "/hardware/wizard", component: () => import("./pages/HardwareWizard.vue"), meta: { title: "ESP Projekt", titleKey: "nav.hardwareWizard", feature: "hardware", fullscreen: true } },
    { path: "/firmware",      component: () => import("./pages/FirmwareBuilder.vue"), meta: { title: "Firmware Builder", titleKey: "nav.firmwareBuilder", feature: "firmware_builder" } },
    { path: "/tours",          component: () => import("./pages/TourBuilder.vue"),     meta: { title: "Tour Builder", titleKey: "nav.tourBuilder", feature: "tours" } },
    { path: "/sandbox",       component: () => import("./pages/Sandbox.vue"),         meta: { title: "Sandbox", titleKey: "nav.sandbox", feature: "sandbox" } },
    { path: "/integrations",  component: () => import("./pages/Integrations.vue"),    meta: { title: "Integrations", titleKey: "nav.integrations", feature: "integrations" } },
    { path: "/mcp",           component: () => import("./pages/McpServer.vue"),      meta: { title: "MCP Server", titleKey: "nav.mcpServer", feature: "mcp" } },
    { path: "/flow-editor",   component: () => import("./pages/FlowEditor.vue"),     meta: { title: "Flow Editor", titleKey: "nav.flowEditor", fullscreen: true, feature: "flow_editor" } },
    { path: "/dashboards",   component: () => import("./pages/Dashboards.vue"),      meta: { title: "Dashboards", titleKey: "nav.dashboards" } },
    { path: "/dashboards/:id", component: () => import("./pages/DashboardView.vue"),meta: { title: "Dashboard" }, name: "dashboard-view" },
    { path: "/kiosk/slideshow", component: () => import("./pages/KioskSlideshow.vue"), meta: { title: "Kiosk Slideshow", layout: "kiosk" } },
    { path: "/kiosk/:id",     component: () => import("./pages/DashboardView.vue"),meta: { title: "Kiosk", layout: "kiosk" } },
    { path: "/embed/:token",  component: () => import("./pages/PublicDashboard.vue"), meta: { title: "Embedded Dashboard", layout: "embed" } },
    { path: "/public/:token", component: () => import("./pages/PublicDashboard.vue"), meta: { title: "Dashboard", layout: "public", noPublicShell: true } },
    // CMS
    { path: "/cms",            component: () => import("./pages/CmsPages.vue"),       meta: { title: "CMS Pages", titleKey: "nav.cmsPages", feature: "cms" } },
    { path: "/cms/forms",      component: () => import("./pages/CmsForms.vue"),       meta: { title: "CMS Forms", titleKey: "nav.cmsForms", feature: "cms" } },
    { path: "/cms/forms/:id/edit", component: () => import("./pages/CmsFormEditor.vue"), meta: { title: "Edit Form", titleKey: "nav.cmsFormEdit", feature: "cms" } },
    { path: "/cms/forms/:id/submissions", component: () => import("./pages/CmsFormSubmissions.vue"), meta: { title: "Form Submissions", titleKey: "nav.cmsFormSubmissions", feature: "cms" } },
    { path: "/cms/menus",      component: () => import("./pages/CmsMenus.vue"),       meta: { title: "CMS Menus", titleKey: "nav.cmsMenus", feature: "cms" } },
    { path: "/cms/menus/:id/edit", component: () => import("./pages/CmsMenuEditor.vue"), meta: { title: "Edit Menu", titleKey: "nav.cmsMenuEdit", fullscreen: true, feature: "cms" } },
    { path: "/cms/media",      component: () => import("./pages/CmsMedia.vue"),       meta: { title: "Media Library", titleKey: "nav.cmsMedia", feature: "cms" } },
    { path: "/cms/redirects",  component: () => import("./pages/CmsRedirects.vue"),   meta: { title: "URL Redirects", titleKey: "nav.cmsRedirects", feature: "cms" } },
    { path: "/cms/settings",   component: () => import("./pages/SiteSettings.vue"),   meta: { title: "Site Settings", titleKey: "nav.cmsSettings", feature: "cms" } },
    { path: "/cms/:id/edit",   component: () => import("./pages/CmsPageEditor.vue"),  meta: { title: "Edit Page", titleKey: "nav.cmsPageEdit", fullscreen: true, feature: "cms" } },
    { path: "/cms/:slug/view", component: () => import("./pages/CmsPageView.vue"),    meta: { title: "View Page", titleKey: "nav.cmsPageView", fullscreen: true, feature: "cms" } },
    { path: "/p/:slug",        component: () => import("./pages/CmsPageView.vue"),    meta: { title: "Page", layout: "public" } },
  ],
});

export default router;
