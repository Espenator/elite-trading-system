import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// Allow backend port override (e.g. VITE_BACKEND_URL=http://localhost:8000)
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  const backendUrl = env.VITE_BACKEND_URL || env.VITE_API_URL || "http://localhost:8000";
  const wsBackend = backendUrl.replace(/^http/, "ws");

  return {
    plugins: [react()],
    server: {
      host: true,
      port: parseInt(env.VITE_PORT || "5173"),
      strictPort: false,
      proxy: {
        "/api": {
          target: backendUrl,
          changeOrigin: true,
          timeout: 120000,       // 2 min — backend can be slow during heavy scans
          proxyTimeout: 120000,
        },
        "/ws": {
          target: wsBackend,
          ws: true,
          timeout: 120000,
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
            recharts: ["recharts"],
            "lightweight-charts": ["lightweight-charts"],
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
