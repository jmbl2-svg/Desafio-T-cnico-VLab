import { defineConfig } from "vite";

export default defineConfig({
  build: {
    modulePreload: false,
    cssCodeSplit: false,
    rollupOptions: {
      input: "src/comparacao.tsx",
      output: {
        entryFileNames: "comparacao.js",
        assetFileNames: "comparacao[extname]",
      },
    },
  },
  esbuild: { jsx: "automatic" },
});
