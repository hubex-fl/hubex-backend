import { createRouter, createWebHistory } from "vue-router";
import SystemStage from "./pages/SystemStage.vue";
import Events from "./pages/Events.vue";
import Effects from "./pages/Effects.vue";
import Observability from "./pages/Observability.vue";
import SettingsAuth from "./pages/SettingsAuth.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/system-stage" },
    { path: "/system-stage", component: SystemStage },
    { path: "/events", component: Events },
    { path: "/effects", component: Effects },
    { path: "/observability", component: Observability },
    { path: "/settings/auth", component: SettingsAuth },
  ],
});

export default router;
