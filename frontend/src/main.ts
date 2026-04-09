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

createApp(App).use(createPinia()).use(i18n).use(router).mount("#app");
