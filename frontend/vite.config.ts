import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

// Sprint 7.5 — vendor chunk splitting.
//
// Before: everything that wasn't lazy-imported via `() => import(...)`
// landed in one 664 KB `index.js`. Vite warned on every build and
// first-page-paint shipped 221 KB gzip. After: core framework libs go
// into their own long-cache chunks, so navigating between routes
// doesn't re-download the same vue/router/i18n bytes, and browser
// caching across HubEx upgrades only invalidates whatever actually
// changed.
//
// Rules:
//   * Keep the grouping COARSE (5-6 chunks max) — too many vendor
//     chunks kills the parallel-fetch benefit by adding round-trips.
//   * Heavy optional deps (tiptap, leaflet, chart.js) stay lazy via
//     their consumer routes; they don't need manualChunks because
//     they're already dynamic.
//   * Everything else keeps the default Vite behaviour (code-split
//     by dynamic import, shared chunks auto-extracted).
function vendorChunks(id: string): string | undefined {
  if (!id.includes("node_modules")) return undefined;
  // Match by package name. On Windows the path contains backslashes;
  // normalize them so the same regex works on Linux + Windows.
  const normalized = id.replace(/\\/g, "/");
  if (/node_modules\/(?:@vue|vue)\//.test(normalized)) return "vue";
  if (/node_modules\/vue-router\//.test(normalized)) return "vue-router";
  if (/node_modules\/(?:@intlify|vue-i18n)\//.test(normalized)) return "vue-i18n";
  if (/node_modules\/pinia\//.test(normalized)) return "pinia";
  if (/node_modules\/(?:chart\.js|vue-chartjs|chartjs-adapter-date-fns)\//.test(normalized)) return "charts";
  if (/node_modules\/@tiptap\//.test(normalized)) return "tiptap";
  return undefined;
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget = env.VITE_API_TARGET || "http://127.0.0.1:8000";
  const devHost = env.VITE_DEV_HOST || "0.0.0.0";
  const devPort = Number(env.VITE_DEV_PORT || "5173");

  return {
    plugins: [vue()],
    build: {
      // The warning threshold is a soft signal — raising it to 600 kB
      // lets the Vite-warning noise stop once our manualChunks drop
      // every chunk below that. If a chunk later grows past 600 kB
      // we still see the warning in CI.
      chunkSizeWarningLimit: 600,
      rollupOptions: {
        output: {
          manualChunks: vendorChunks,
        },
      },
    },
    server: {
      host: devHost,
      port: devPort,
      strictPort: true,
      proxy: {
        "/api": { target: apiTarget, changeOrigin: true },
        "/health": { target: apiTarget, changeOrigin: true },
        "/ready": { target: apiTarget, changeOrigin: true },
        "/docs": { target: apiTarget, changeOrigin: true },
        "/redoc": { target: apiTarget, changeOrigin: true },
        "/openapi.json": { target: apiTarget, changeOrigin: true },
      },
    },
  };
});
