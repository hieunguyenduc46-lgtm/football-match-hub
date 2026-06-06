<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '../services/api'
import MatchCard from '../components/MatchCard.vue'
import { imgFallback } from '../utils/format'

const route = useRoute()
const data = ref(null)      // { mode, teamA, teamB, team, recent, upcoming, notFound }
const loading = ref(false)
const error = ref('')

async function load() {
  const q = (route.query.q || '').toString().trim()
  if (!q) { data.value = null; return }
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/match-search', { params: { q } })
    data.value = res.data
  } catch (e) {
    error.value = (e.message || 'error')
  } finally {
    loading.value = false
  }
}

// Đổi từ khoá trên URL (?q=...) -> tải lại. immediate để vào trang là chạy luôn.
// (Đã bỏ onMounted(load) vì immediate:true đã tự gọi 1 lần lúc mount -> tránh gọi API 2 lần.)
watch(() => route.query.q, load, { immediate: true })
</script>

<template>
  <router-link to="/" class="back">{{ $t('backHome') }}</router-link>

  <!-- Tiêu đề: A vs B hoặc 1 đội -->
  <div v-if="data && data.mode === 'h2h' && data.teamA && data.teamB" class="ms-head">
    <span class="ms-team"><img :src="data.teamA.logo" @error="imgFallback" />{{ data.teamA.name }}</span>
    <span class="ms-vs">vs</span>
    <span class="ms-team"><img :src="data.teamB.logo" @error="imgFallback" />{{ data.teamB.name }}</span>
  </div>
  <div v-else-if="data && data.mode === 'team' && data.team" class="ms-head">
    <span class="ms-team"><img :src="data.team.logo" @error="imgFallback" />{{ data.team.name }}</span>
  </div>
  <h1 v-else class="page-title">{{ $t('matchesFor') }}</h1>

  <div v-if="loading" class="center">{{ $t('loadingMatches') }}</div>
  <div v-else-if="error" class="error-box">{{ error }} {{ $t('backendErr') }}</div>

  <!-- Không tìm thấy đội -->
  <div v-else-if="data && data.notFound && data.notFound.length" class="center">
    {{ $t('teamNotFound') }}: "{{ data.notFound.join(', ') }}"
  </div>

  <!-- Chưa nhập gì -->
  <div v-else-if="!data" class="center">{{ $t('searchMatchHint') }}</div>

  <!-- Kết quả -->
  <template v-else>
    <section class="ms-section">
      <h3 class="ms-section__title">{{ $t('upcomingMatches') }}</h3>
      <MatchCard v-for="m in data.upcoming" :key="'u' + m.fixture.id" :fixture="m" />
      <div v-if="!data.upcoming || data.upcoming.length === 0" class="muted ms-empty">{{ $t('noUpcoming') }}</div>
    </section>

    <section class="ms-section">
      <h3 class="ms-section__title">{{ $t('recentMatchesH') }}</h3>
      <MatchCard v-for="m in data.recent" :key="'r' + m.fixture.id" :fixture="m" />
      <div v-if="!data.recent || data.recent.length === 0" class="muted ms-empty">{{ $t('noRecent') }}</div>
    </section>
  </template>
</template>

<style scoped>
.ms-head {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  font-size: 20px; font-weight: 700; margin: 16px 0 8px;
}
.ms-team { display: inline-flex; align-items: center; gap: 8px; }
.ms-team img { width: 28px; height: 28px; object-fit: contain; }
.ms-vs { color: var(--text-dim); font-weight: 600; font-size: 16px; }
.ms-section { margin-top: 18px; }
.ms-section__title { font-size: 14px; font-weight: 700; color: var(--text-dim); margin: 0 0 8px; }
.ms-empty { padding: 8px 2px; font-size: 14px; }
</style>
