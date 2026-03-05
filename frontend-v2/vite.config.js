import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// Allow backend port override (e.g. VITE_BACKEND_URL=http://localhost:8000)
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  const backendUrl = env.VITE_BACKEND_URL || "http://localhost:8000";
  const wsBackend = backendUrl.replace(/^http/, "ws");

  return {
    plugins: [react()],
    server: {
      host: true,
      port: 3000,
      proxy: {
        "/api": {
          target: backendUrl,
          changeOrigin: true,
        },
        "/ws": {
          target: wsBackend,
          ws: true,
        },
      },
    },
    build: {
      outDir: "dist",
      sourcemap: false,
      minify: "esbuild",
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ["react", "react-dom", "react-router-dom"],
            charts: ["lightweight-charts", "recharts"],
            flow: ["reactflow"],
          },
        },
      },
      chunkSizeWarningLimit: 600,
    },
    resolve: {
      alias: {
        "@": "/src",
      },
    },
  };
});
