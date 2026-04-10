import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import { i18n } from "./i18n";
import { injectTourRouter } from "./stores/tour";
import "./style.css";

// Inject the router into the tour store so it can navigate between pages.
// This must happen before the app mounts (useRouter() only works in setup
// context, but Pinia actions run outside of that).
injectTourRouter(router);

const pinia = createPinia();
// Expose the pinia instance globally so dynamically-mounted components
// (e.g. CMS BlockRenderer hydrated HubEx blocks) can share the same store.
try { (window as any).__hubex_pinia = pinia; } catch { /* noop */ }

createApp(App).use(pinia).use(i18n).use(router).mount("#app");
