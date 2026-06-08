<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '../services/api'
import { state } from '../i18n'
import { imgFallback } from '../utils/format'
import { COUNTRY_VI, teamName } from '../utils/countryNames'
import { leagueName } from '../utils/leagueNames'
import { ensureIndex, leaguesByCountry } from '../utils/searchIndex'
import MatchCard from '../components/MatchCard.vue'

const route = useRoute()
const tab = ref('national') // 'national' | 'domestic'

// Tên nước canon (tiếng Anh) lấy từ URL; hiển thị tiếng Việt nếu đang chế độ vi.
const countryEn = computed(() => route.params.name || '')
const title = computed(() =>
  state.locale === 'vi' ? COUNTRY_VI[countryEn.value] || countryEn.value : countryEn.value
)

// ---- Tab ĐỘI TUYỂN: trận gần đây + sắp tới ----
const nat = ref({ team: null, recent: [], upcoming: [] })
const natLoading = ref(false)
let natLoadedFor = null
async function loadNational(name) {
  if (!name || natLoadedFor === name) return
  natLoadedFor = name
  natLoading.value = true
  nat.value = { team: null, recent: [], upcoming: [] }
  try {
    const { data } = await api.get(`/country/${encodeURIComponent(name)}/fixtures`)
    if (natLoadedFor === name) nat.value = { team: data.team, recent: data.recent || [], upcoming: data.upcoming || [] }
  } finally {
    if (natLoadedFor === name) natLoading.value = false
  }
}
const hasNat = computed(() => nat.value.recent.length || nat.value.upcoming.length)

// ---- Tab GIẢI TRONG NƯỚC: lọc từ chỉ mục đã tải sẵn (không gọi thêm API) ----
const leagues = ref([])
const idxReady = ref(false)
async function loadDomestic(name) {
  await ensureIndex()
  idxReady.value = true
  leagues.value = leaguesByCountry(name)
}

function sync() {
  const name = countryEn.value
  loadDomestic(name)
  if (tab.value === 'national') loadNational(name)
}
onMounted(sync)
watch(() => route.params.name, () => {
  natLoadedFor = null
  tab.value = 'national'
  sync()
})
watch(tab, (v) => { if (v === 'national') loadNational(countryEn.value) })
</script>

<template>
  <a href="#" class="back" @click.prevent="$router.back()">{{ $t('backHome') }}</a>
  <h1 class="page-title">{{ title }}</h1>

  <div class="tabs">
    <button class="tab" :class="{ active: tab === 'national' }" @click="tab = 'national'">{{ $t('tab_national') }}</button>
    <button class="tab" :class="{ active: tab === 'domestic' }" @click="tab = 'domestic'">{{ $t('tab_domestic') }}</button>
  </div>

  <!-- Đội tuyển quốc gia -->
  <div v-if="tab === 'national'">
    <div v-if="natLoading">
      <div class="skeleton" v-for="n in 4" :key="n"></div>
    </div>
    <div v-else-if="!nat.team" class="center">{{ $t('countryNotFound') }}</div>
    <template v-else>
      <div class="country-team" v-if="nat.team">
        <img :src="nat.team.logo" @error="imgFallback" />
        <span>{{ teamName(nat.team.name) }}</span>
      </div>
      <div v-if="!hasNat" class="center">{{ $t('noRecent') }}</div>
      <template v-else>
        <template v-if="nat.upcoming.length">
          <h3 class="group-name">{{ $t('upcomingMatches') }}</h3>
          <MatchCard v-for="m in nat.upcoming" :key="'u' + m.fixture.id" :fixture="m" show-date />
        </template>
        <template v-if="nat.recent.length">
          <h3 class="group-name">{{ $t('results_h') }}</h3>
          <MatchCard v-for="m in nat.recent" :key="'r' + m.fixture.id" :fixture="m" show-date />
        </template>
      </template>
    </template>
  </div>

  <!-- Giải trong nước -->
  <div v-else>
    <div v-if="idxReady && leagues.length === 0" class="center">{{ $t('noLeaguesCountry') }}</div>
    <div v-else>
      <router-link
        v-for="l in leagues"
        :key="l.id"
        class="match-card country-league"
        :to="{ name: 'league', params: { id: l.id } }"
      >
        <img :src="l.logo" @error="imgFallback" />
        <span class="cl-name">{{ leagueName(l.name, l.id) }}</span>
        <span class="cl-type">{{ l.type }}</span>
      </router-link>
    </div>
  </div>
</template>

<style scoped>
.country-team { display: flex; align-items: center; gap: 10px; font-size: 18px; font-weight: 700; margin: 4px 0 14px; }
.country-team img { width: 34px; height: 34px; object-fit: contain; }
.country-league { display: flex; align-items: center; gap: 12px; }
.country-league img { width: 28px; height: 28px; object-fit: contain; flex: 0 0 auto; }
.cl-name { flex: 1; font-weight: 600; }
.cl-type { color: var(--text-dim); font-size: 12px; }
</style>
