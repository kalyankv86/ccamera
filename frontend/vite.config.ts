import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev mode proxies /api to FastAPI on :8000 (SDD 3.7 "no Nginx" deviation:
// FastAPI can optionally serve frontend/dist directly for a closer-to-prod
// local run, but day-to-day dev keeps Vite's hot reload).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        ws: true,
      },
    },
  },
});
