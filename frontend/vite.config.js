import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from "path"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        // Inside Docker, use the service name. Outside Docker (local dev), falls back to localhost.
        target: process.env.VITE_PROXY_TARGET || 'http://backend:8000',
        changeOrigin: true,
      },
    },
  }
})
