import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      // Proxy API requests to local Azure Functions backend in dev mode
      "/api": {
        target: "http://localhost:7071",
        changeOrigin: true,
      },
      // Dev file upload goes to separate simple server (Azure Functions has issues with large bodies)
      "/dd-file-upload-dev": {
        target: "http://localhost:7072",
        changeOrigin: true,
      },
      // DD-specific endpoints
      "/dd-": {
        target: "http://localhost:7071/api",
        changeOrigin: true,
        rewrite: (path) => path,
      },
    },
  },
});
