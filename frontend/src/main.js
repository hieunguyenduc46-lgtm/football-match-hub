import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { t } from './i18n'
import { inject as vercelAnalytics } from '@vercel/analytics'
import './assets/main.css'

// Theme: read the saved choice and apply it BEFORE rendering to avoid a colour flash.
const savedTheme = (() => { try { return localStorage.getItem('theme') } catch (e) { return null } })()
document.documentElement.setAttribute('data-theme', savedTheme || 'dark')

const app = createApp(App)
app.config.globalProperties.$t = t // use $t('key') in every template
app.use(createPinia()).use(router).mount('#app')

// Vercel Web Analytics: counts visits / page views (anonymous).
// Follows SPA navigation automatically. Locally the script returns 404 -> harmless; it only really runs on Vercel.
// Wrapped in try/catch so analytics can NEVER affect the app (runs AFTER mount).
try { vercelAnalytics() } catch (e) { /* ignore, do not let analytics break the app */ }

// PWA: only register the service worker in the production build (avoids breaking HMR in development).
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => { /* ignore */ })
  })
}
