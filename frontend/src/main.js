import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { t } from './i18n'
import './assets/main.css'

// Theme: đọc lựa chọn đã lưu và set TRƯỚC khi render để không bị chớp màu.
const savedTheme = (() => { try { return localStorage.getItem('theme') } catch (e) { return null } })()
document.documentElement.setAttribute('data-theme', savedTheme || 'dark')

const app = createApp(App)
app.config.globalProperties.$t = t // dùng $t('key') trong mọi template
app.use(createPinia()).use(router).mount('#app')

// PWA: chỉ đăng ký service worker ở bản production (tránh phá HMR khi dev).
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => { /* bỏ qua */ })
  })
}
