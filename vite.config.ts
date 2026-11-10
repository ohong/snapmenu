import { defineConfig } from "vite";
export default defineConfig({
  root: "frontend",
  publicDir: "../static",
  build: { outDir: "../dist", emptyOutDir: true, target: "es2022" },
  server: { proxy: { "/api": "http://127.0.0.1:8787" } },
});
