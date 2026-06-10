import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { t } from './i18n'
import { inject as vercelAnalytics } from '@vercel/analytics'
import './assets/main.css'

// Theme: đọc lựa chọn đã lưu và set TRƯỚC khi render để không bị chớp màu.
const savedTheme = (() => { try { return localStorage.getItem('theme') } catch (e) { return null } })()
document.documentElement.setAttribute('data-theme', savedTheme || 'dark')

const app = createApp(App)
app.config.globalProperties.$t = t // dùng $t('key') trong mọi template
app.use(createPinia()).use(router).mount('#app')

// Vercel Web Analytics: đếm lượt truy cập / lượt xem trang (ẩn danh).
// Tự bám theo điều hướng SPA. Ở local script trả 404 -> vô hại; chỉ chạy thật trên Vercel.
// Bọc try/catch để analytics TUYỆT ĐỐI không bao giờ làm ảnh hưởng app (chạy SAU mount).
try { vercelAnalytics() } catch (e) { /* bỏ qua, không để analytics phá app */ }

// PWA: chỉ đăng ký service worker ở bản production (tránh phá HMR khi dev).
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => { /* bỏ qua */ })
  })
}
