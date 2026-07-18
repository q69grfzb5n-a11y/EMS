import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      // "localhost" only resolves to the backend when running bare-metal; inside the
      // dockerized dev stack the backend is a separate container reachable by its
      // compose service name — see VITE_API_PROXY_TARGET in docker-compose.dev.yml.
      "/api": process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: true,
  },
});
