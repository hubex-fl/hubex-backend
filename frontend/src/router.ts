import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/",             component: () => import("./pages/DashboardPage.vue"), meta: { title: "Dashboard" } },
    { path: "/login",        component: () => import("./pages/Login.vue"),          meta: { layout: "auth",  title: "Sign In" } },
    { path: "/system-stage", component: () => import("./pages/SystemStage.vue"),    meta: { title: "System Stage" } },
    { path: "/devices",      component: () => import("./pages/Devices.vue"),         meta: { title: "Devices" } },
    { path: "/devices/:id",  component: () => import("./pages/DeviceDetail.vue"),    meta: { title: "Device Detail" }, name: "device-detail" },
    { path: "/events",       component: () => import("./pages/Events.vue"),          meta: { title: "Events" } },
    { path: "/effects",      component: () => import("./pages/Effects.vue"),         meta: { title: "Effects" } },
    { path: "/trace-hub",    component: () => import("./pages/TraceHub.vue"),        meta: { title: "Trace Hub" } },
    { path: "/executions",   component: () => import("./pages/Executions.vue"),      meta: { title: "Executions" } },
    { path: "/audit",        component: () => import("./pages/Audit.vue"),           meta: { title: "Audit Log" } },
    { path: "/correlation",  component: () => import("./pages/Correlation.vue"),     meta: { title: "Correlation" } },
    { path: "/observability",component: () => import("./pages/Observability.vue"),   meta: { title: "Observability" } },
    { path: "/settings/auth",component: () => import("./pages/SettingsAuth.vue"),    meta: { title: "Auth Settings" } },
    { path: "/token",        component: () => import("./pages/TokenInspector.vue"),  meta: { title: "Token Inspector" } },
    { path: "/variables",    component: () => import("./pages/Variables.vue"),       meta: { title: "Variables" } },
    { path: "/pairing",      component: () => import("./pages/Pairing.vue"),         meta: { title: "Pairing" } },
  ],
});

export default router;
