import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget = env.VITE_API_TARGET || "http://127.0.0.1:8000";
  const devHost = env.VITE_DEV_HOST || "0.0.0.0";
  const devPort = Number(env.VITE_DEV_PORT || "5173");

  return {
    plugins: [vue()],
    server: {
      host: devHost,
      port: devPort,
      strictPort: true,
      proxy: {
        "/api": { target: apiTarget, changeOrigin: true },
      },
    },
  };
});
