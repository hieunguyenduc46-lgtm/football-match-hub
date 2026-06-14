<script setup>
// Trang 404: hiện khi vào URL không khớp route nào (gõ sai, link cũ/chết, link PWA cũ).
// Route bắt-tất-cả ('/:pathMatch(.*)*') ở cuối router/index.js trỏ tới đây.
import { onMounted } from 'vue'
import { setTitle } from '../utils/title'
import { t } from '../i18n'

onMounted(() => setTitle(t('notFoundTitle')))
</script>

<template>
  <div class="nf">
    <div class="nf-ball">⚽</div>
    <div class="nf-code">404</div>
    <h1 class="nf-title">{{ $t('notFoundTitle') }}</h1>
    <p class="nf-desc">{{ $t('notFoundDesc') }}</p>
    <router-link class="nf-btn" :to="{ name: 'home' }">← {{ $t('goHome') }}</router-link>
  </div>
</template>

<style scoped>
.nf {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 64px 20px;
  gap: 8px;
}
.nf-ball { font-size: 44px; }
.nf-code { font-size: 64px; font-weight: 800; color: var(--accent); line-height: 1; }
.nf-title { font-size: 22px; font-weight: 700; margin: 6px 0 0; color: var(--text); }
.nf-desc { color: var(--text-dim); margin: 0 0 18px; max-width: 360px; }
.nf-btn {
  display: inline-block;
  padding: 10px 18px;
  border-radius: var(--radius);
  background: var(--accent);
  color: #fff;
  text-decoration: none;
  font-weight: 700;
}
.nf-btn:hover { opacity: 0.9; }
</style>
