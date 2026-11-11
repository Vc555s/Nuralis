import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// The dev server proxies /api to the Nuralis backend, so the browser only ever
// talks to one origin. start.sh writes the backend URL to .env.local; override it
// there with VITE_API_PROXY_TARGET=http://localhost:<port>.
const DEFAULT_API_TARGET = "http://localhost:8010";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget = env.VITE_API_PROXY_TARGET || DEFAULT_API_TARGET;

  return {
    server: {
      host: "0.0.0.0",
      port: 5050,
      strictPort: true,
      proxy: {
        "/api": {
          target: apiTarget,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  };
});
