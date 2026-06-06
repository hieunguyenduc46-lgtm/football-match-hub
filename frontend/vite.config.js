import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Proxy: mọi request /api/* được chuyển sang backend FastAPI (cổng 8000).
// Nhờ vậy frontend gọi "/api/fixtures" mà không lo CORS hay lộ địa chỉ backend.
export default defineConfig({
  plugins: [vue()],
  server: {
    host: true, // lắng nghe trên LAN -> mở được từ điện thoại cùng WiFi
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
