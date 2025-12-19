import { createRouter, createWebHistory } from "vue-router";
import Login from "./pages/Login.vue";
import Devices from "./pages/Devices.vue";
import DeviceDetail from "./pages/DeviceDetail.vue";
import Pairing from "./pages/Pairing.vue";
import { hasToken } from "./lib/api";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/devices" },
    { path: "/login", component: Login },
    { path: "/devices", component: Devices },
    { path: "/devices/:id", component: DeviceDetail, props: true },
    { path: "/pairing", component: Pairing },
  ],
});

router.beforeEach((to) => {
  if (to.path !== "/login" && !hasToken()) {
    return "/login";
  }
  return true;
});

export default router;
