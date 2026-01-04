import { createRouter, createWebHistory } from "vue-router";
import SystemStage from "./pages/SystemStage.vue";
import Events from "./pages/Events.vue";
import Effects from "./pages/Effects.vue";
import Observability from "./pages/Observability.vue";
import SettingsAuth from "./pages/SettingsAuth.vue";
import TraceHub from "./pages/TraceHub.vue";
import Audit from "./pages/Audit.vue";
import Executions from "./pages/Executions.vue";
import Correlation from "./pages/Correlation.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/system-stage" },
    { path: "/system-stage", component: SystemStage },
    { path: "/events", component: Events },
    { path: "/effects", component: Effects },
    { path: "/trace-hub", component: TraceHub },
    { path: "/observability", component: Observability },
    { path: "/executions", component: Executions },
    { path: "/audit", component: Audit },
    { path: "/correlation", component: Correlation },
    { path: "/settings/auth", component: SettingsAuth },
  ],
});

export default router;
