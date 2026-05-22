import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy API requests to FastAPI during development
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // Optional: if go2rtc is served separately in dev
      '/go2rtc': {
        target: 'http://localhost:1984',
        changeOrigin: true,
      }
    }
  }
})