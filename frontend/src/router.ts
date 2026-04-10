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
      meta: { title: "Dashboard" },
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
    { path: "/login",        component: () => import("./pages/Login.vue"),          meta: { layout: "auth",  title: "Sign In" } },
    { path: "/system-stage", component: () => import("./pages/SystemStage.vue"),    meta: { title: "System Stage" } },
    { path: "/devices",      component: () => import("./pages/Devices.vue"),         meta: { title: "Devices" } },
    { path: "/devices/:id",  component: () => import("./pages/DeviceDetail.vue"),    meta: { title: "Device Detail" }, name: "device-detail" },
    { path: "/entities",     component: () => import("./pages/EntitiesPage.vue"),    meta: { title: "Entities" } },
    { path: "/events",       component: () => import("./pages/Events.vue"),          meta: { title: "Events" } },
    { path: "/alerts",       component: () => import("./pages/Alerts.vue"),          meta: { title: "Alerts" } },
    { path: "/effects",      component: () => import("./pages/Effects.vue"),         meta: { title: "Effects" } },
    { path: "/trace-hub",    component: () => import("./pages/TraceHub.vue"),        meta: { title: "Trace Hub" } },
    { path: "/executions",   component: () => import("./pages/Executions.vue"),      meta: { title: "Executions" } },
    { path: "/audit",        component: () => import("./pages/Audit.vue"),           meta: { title: "Audit Log" } },
    // Correlation removed — merged into TraceTimeline
    { path: "/observability",component: () => import("./pages/Observability.vue"),   meta: { title: "Observability" } },
    { path: "/settings",     component: () => import("./pages/Settings.vue"),        meta: { title: "Settings" } },
    { path: "/settings/auth", redirect: "/settings" },
    { path: "/settings/types", component: () => import("./pages/SemanticTypes.vue"), meta: { title: "Semantic Types" } },
    { path: "/token",        component: () => import("./pages/TokenInspector.vue"),  meta: { title: "Token Inspector" } },
    { path: "/variables",    component: () => import("./pages/Variables.vue"),       meta: { title: "Variables" } },
    { path: "/variables/streams", component: () => import("./pages/VariableStreams.vue"), meta: { title: "Variable Streams" } },
    { path: "/pairing",      component: () => import("./pages/Pairing.vue"),         meta: { title: "Pairing" } },
    { path: "/system-health", component: () => import("./pages/SystemHealth.vue"),   meta: { title: "System Health" } },
    { path: "/automations",  component: () => import("./pages/Automations.vue"),     meta: { title: "Automations" } },
    { path: "/developer",    component: () => import("./pages/ApiDocs.vue"),         meta: { title: "API Docs" } },
    { path: "/webhooks",     component: () => import("./pages/Webhooks.vue"),        meta: { title: "Webhooks" } },
    { path: "/email-templates", component: () => import("./pages/EmailTemplates.vue"), meta: { title: "Email Templates" } },
    { path: "/admin",          component: () => import("./pages/AdminConsole.vue"),   meta: { title: "Admin Console" } },
    { path: "/custom-api",    component: () => import("./pages/CustomApiBuilder.vue"), meta: { title: "Custom API" } },
    { path: "/trace-timeline", component: () => import("./pages/TraceTimeline.vue"),  meta: { title: "Trace Timeline" } },
    { path: "/reports",       component: () => import("./pages/Reports.vue"),        meta: { title: "Reports" } },
    { path: "/plugins",       component: () => import("./pages/Plugins.vue"),        meta: { title: "Plugins" } },
    { path: "/hardware",      component: () => import("./pages/HardwareBoards.vue"), meta: { title: "Hardware Boards" } },
    { path: "/tours",          component: () => import("./pages/TourBuilder.vue"),     meta: { title: "Tour Builder" } },
    { path: "/sandbox",       component: () => import("./pages/Sandbox.vue"),         meta: { title: "Sandbox" } },
    { path: "/integrations",  component: () => import("./pages/Integrations.vue"),    meta: { title: "Integrations" } },
    { path: "/mcp",           component: () => import("./pages/McpServer.vue"),      meta: { title: "MCP Server" } },
    { path: "/flow-editor",   component: () => import("./pages/FlowEditor.vue"),     meta: { title: "Flow Editor", fullscreen: true } },
    { path: "/dashboards",   component: () => import("./pages/Dashboards.vue"),      meta: { title: "Dashboards" } },
    { path: "/dashboards/:id", component: () => import("./pages/DashboardView.vue"),meta: { title: "Dashboard" }, name: "dashboard-view" },
    { path: "/kiosk/slideshow", component: () => import("./pages/KioskSlideshow.vue"), meta: { title: "Kiosk Slideshow", layout: "kiosk" } },
    { path: "/kiosk/:id",     component: () => import("./pages/DashboardView.vue"),meta: { title: "Kiosk", layout: "kiosk" } },
    { path: "/embed/:token",  component: () => import("./pages/PublicDashboard.vue"), meta: { title: "Embedded Dashboard", layout: "embed" } },
    { path: "/public/:token", component: () => import("./pages/PublicDashboard.vue"), meta: { title: "Dashboard", layout: "public", noPublicShell: true } },
    // CMS
    { path: "/cms",            component: () => import("./pages/CmsPages.vue"),       meta: { title: "CMS Pages" } },
    { path: "/cms/forms",      component: () => import("./pages/CmsForms.vue"),       meta: { title: "CMS Forms" } },
    { path: "/cms/forms/:id/edit", component: () => import("./pages/CmsFormEditor.vue"), meta: { title: "Edit Form" } },
    { path: "/cms/forms/:id/submissions", component: () => import("./pages/CmsFormSubmissions.vue"), meta: { title: "Form Submissions" } },
    { path: "/cms/menus",      component: () => import("./pages/CmsMenus.vue"),       meta: { title: "CMS Menus" } },
    { path: "/cms/menus/:id/edit", component: () => import("./pages/CmsMenuEditor.vue"), meta: { title: "Edit Menu", fullscreen: true } },
    { path: "/cms/media",      component: () => import("./pages/CmsMedia.vue"),       meta: { title: "Media Library" } },
    { path: "/cms/redirects",  component: () => import("./pages/CmsRedirects.vue"),   meta: { title: "URL Redirects" } },
    { path: "/cms/settings",   component: () => import("./pages/SiteSettings.vue"),   meta: { title: "Site Settings" } },
    { path: "/cms/:id/edit",   component: () => import("./pages/CmsPageEditor.vue"),  meta: { title: "Edit Page", fullscreen: true } },
    { path: "/cms/:slug/view", component: () => import("./pages/CmsPageView.vue"),    meta: { title: "View Page", fullscreen: true } },
    { path: "/p/:slug",        component: () => import("./pages/CmsPageView.vue"),    meta: { title: "Page", layout: "public" } },
  ],
});

export default router;
