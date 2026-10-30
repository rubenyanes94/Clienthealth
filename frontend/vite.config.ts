import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    port: 5173,
    // Escucha en todas las interfaces: el túnel de Codespaces no siempre llega a 127.0.0.1.
    host: true,
    // Codespaces sirve la web desde *.app.github.dev; sin esto Vite responde 403.
    allowedHosts: [".app.github.dev"],
    // Mismas rutas relativas que en producción: /api va al FastAPI local.
    proxy: { "/api": { target: "http://localhost:8000", changeOrigin: false } },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
