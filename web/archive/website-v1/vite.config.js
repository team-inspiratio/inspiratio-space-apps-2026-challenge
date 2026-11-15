import { defineConfig } from "vite";

// Two pages: the atlas (index.html) and the standalone, linkable method page.
export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        main: "index.html",
        methods: "methods.html",
      },
    },
  },
});
