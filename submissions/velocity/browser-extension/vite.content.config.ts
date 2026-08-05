import path from "node:path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

// Content scripts must be classic (non-module) scripts — Chrome refuses to
// run `import` statements inside a content script. Building it separately
// with format: "iife" forces everything to be inlined into one flat file.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: false,
    rollupOptions: {
      input: {
        content: path.resolve(__dirname, "src/content/index.ts"),
      },
      output: {
        entryFileNames: "assets/[name].js",
        assetFileNames: "assets/[name][extname]",
        format: "iife",
      },
    },
  },
})