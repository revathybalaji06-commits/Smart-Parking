import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// While developing, forward API calls to the backend on port 8000
const backend = "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/availability": backend,
      "/slots": backend,
      "/reserve": backend,
      "/reservations": backend,
    },
  },
});
