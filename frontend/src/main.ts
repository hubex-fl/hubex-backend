import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import { i18n } from "./i18n";
import { injectTourRouter } from "./stores/tour";
import { useFeaturesStore } from "./stores/features";
import "./style.css";

// Inject the router into the tour store so it can navigate between pages.
// This must happen before the app mounts (useRouter() only works in setup
// context, but Pinia actions run outside of that).
injectTourRouter(router);

const pinia = createPinia();
// Expose the pinia instance globally so dynamically-mounted components
// (e.g. CMS BlockRenderer hydrated HubEx blocks) can share the same store.
try { (window as any).__hubex_pinia = pinia; } catch { /* noop */ }

const app = createApp(App).use(pinia).use(i18n).use(router);

// Feature-flag route guard: redirect disabled-feature routes to /disabled.
// The features store is lazy-loaded; we await the load on first navigation
// so a fresh page load lands on /disabled (not the destination followed by
// an API 404). After the first load the store stays cached.
router.beforeEach(async (to, _from, next) => {
  const feature = (to.meta as any)?.feature as string | undefined;
  if (!feature) return next();

  const features = useFeaturesStore();
  if (!features.loaded) {
    try {
      await features.load();
    } catch {
      // fail-open on network errors so the login / landing flow still works
      return next();
    }
  }
  if (!features.isEnabled(feature)) {
    return next({ path: "/disabled", query: { feature, from: to.fullPath } });
  }
  return next();
});

app.mount("#app");
