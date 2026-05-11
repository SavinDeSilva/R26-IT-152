import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiProxy = {
  "/api": {
    target: "http://127.0.0.1:5005",
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ""),
  },
};

// Dev + preview: browser calls same-origin /api → forwarded to Flask (avoids connection issues).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: apiProxy,
  },
  preview: {
    proxy: apiProxy,
  },
});
