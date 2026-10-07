import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const here = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(here, "..");

export default defineConfig({
  root: projectRoot,
  base: "./",
  cacheDir: resolve(here, "node_modules/.vite"),
  plugins: [react()],
  resolve: {
    alias: {
      react: resolve(here, "node_modules/react"),
      "react-dom": resolve(here, "node_modules/react-dom"),
      "lucide-react": resolve(here, "node_modules/lucide-react"),
      "react-simple-maps": resolve(here, "node_modules/react-simple-maps"),
      "world-atlas": resolve(here, "node_modules/world-atlas")
    }
  },
  server: {
    host: "127.0.0.1",
    port: 5173
  },
  build: {
    outDir: resolve(here, "dist"),
    emptyOutDir: true
  }
});
