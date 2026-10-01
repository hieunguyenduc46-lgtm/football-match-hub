import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Proxy: every /api/* request is forwarded to the FastAPI backend (port 8000).
// So the frontend calls "/api/fixtures" without worrying about CORS or exposing the backend address.
export default defineConfig({
  plugins: [vue()],
  server: {
    host: true, // listen on the LAN -> can be opened from a phone on the same WiFi
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
