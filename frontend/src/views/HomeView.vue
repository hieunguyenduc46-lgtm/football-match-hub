<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useFixturesStore } from '../stores/fixtures'
import api from '../services/api'
import MatchCard from '../components/MatchCard.vue'
import { t, state } from '../i18n'

const store = useFixturesStore()
const { fixtures, loading, error } = storeToRefs(store)

// Múi giờ của người đang xem (vd "Asia/Ho_Chi_Minh", "Australia/Sydney").
const tz = Intl.DateTimeFormat().resolvedOptions().timeZone

// ---- Dải ngày theo GIỜ ĐỊA PHƯƠNG của người xem ----
function localISO(dt) {
  const y = dt.getFullYear()
  const m = String(dt.getMonth() + 1).padStart(2, '0')
  const d = String(dt.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}
function buildDates() {
  const out = []
  const base = new Date()
  for (let d = -2; d <= 4; d++) {
    const dt = new Date(base.getFullYear(), base.getMonth(), base.getDate() + d) // nửa đêm giờ địa phương
    out.push({ iso: localISO(dt), dt, today: d === 0 })
  }
  return out
}
const dates = ref(buildDates())
const selectedDate = ref(dates.value.find((d) => d.today).iso)
// Gói PRO: xem được mọi ngày (quá khứ + tương lai) -> không giới hạn ô chọn ngày nữa.

function todayIso() {
  return localISO(new Date())
}
// Nếu đã sang ngày mới (để tab mở qua đêm) -> dựng lại dải ngày, đẩy "Hôm nay" sang đúng ngày.
function maybeRollDate() {
  const stripToday = dates.value.find((d) => d.today)?.iso
  if (stripToday && stripToday !== todayIso()) {
    const wasOnToday = selectedDate.value === stripToday
    dates.value = buildDates()
    if (wasOnToday) selectedDate.value = dates.value.find((d) => d.today).iso
  }
}
function onVisible() {
  if (!document.hidden) maybeRollDate()
}

function locale() {
  return state.locale === 'en' ? 'en-US' : 'vi-VN'
}
function dayLabel(d) {
  if (d.today) return t('today')
  return new Intl.DateTimeFormat(locale(), { weekday: 'short' }).format(d.dt)
}
function dayNum(d) {
  return new Intl.DateTimeFormat(locale(), { day: 'numeric', month: 'numeric' }).format(d.dt)
}

// ---- Lọc giải ----
const leagues = ref([])
const selectedLeague = ref('') // '' = tất cả

async function load(silent = false) {
  const params = { date: selectedDate.value, tz } // tz = múi giờ người xem
  if (selectedLeague.value) params.league = selectedLeague.value
  await store.fetchFixtures(params, { silent })
}

// Gom theo giải
const grouped = computed(() => {
  const map = {}
  for (const f of fixtures.value) {
    const key = f.league.id
    if (!map[key]) map[key] = { league: f.league, matches: [] }
    map[key].matches.push(f)
  }
  return Object.values(map)
})

watch([selectedDate, selectedLeague], () => load())

// Auto-refresh: làm mới ngầm mỗi 30s để cập nhật tỉ số trận đang đá.
let timer = null
onMounted(async () => {
  try {
    const { data } = await api.get('/leagues')
    leagues.value = data.response || []
  } catch (e) { /* không sao, vẫn dùng bộ lọc 'Tất cả' */ }
  load()
  // Mỗi 15s: kiểm tra đã sang ngày mới + làm mới tỉ số ngầm.
  // 15s = nhịp làm tươi của API-Football (poll nhanh hơn cũng không có dữ liệu mới).
  // Tiết kiệm request: CHỈ poll khi (1) tab đang hiển thị VÀ (2) đang xem NGÀY HÔM NAY
  // — chỉ trận hôm nay mới có tỉ số thay đổi; ngày quá khứ/tương lai không cần poll.
  // Backend cache (LIVE_TTL=15s, dùng chung) đảm bảo dù 100 user cùng poll thì
  // API-Football vẫn chỉ bị gọi tối đa 1 lần mỗi 15s cho mỗi cache key.
  timer = setInterval(() => {
    maybeRollDate()
    if (!document.hidden && selectedDate.value === todayIso()) load(true)
  }, 15000)
  document.addEventListener('visibilitychange', onVisible)
})
onUnmounted(() => {
  clearInterval(timer)
  document.removeEventListener('visibilitychange', onVisible)
})
</script>

<template>
  <!-- Dải ngày -->
  <div class="date-strip">
    <button
      v-for="d in dates"
      :key="d.iso"
      class="date-chip"
      :class="{ active: selectedDate === d.iso }"
      @click="selectedDate = d.iso"
    >
      <span class="dl">{{ dayLabel(d) }}</span>
      <span class="dn" v-if="!d.today">{{ dayNum(d) }}</span>
    </button>
  </div>

  <!-- Lọc giải -->
  <div class="filter-row">
    <label class="muted" style="font-size:13px">{{ $t('league') }}</label>
    <select v-model="selectedLeague" class="league-select">
      <option value="">{{ $t('all') }}</option>
      <option v-for="l in leagues" :key="l.id" :value="l.id">{{ l.name }}</option>
    </select>
    <input type="date" v-model="selectedDate" class="league-select" />
  </div>

  <div v-if="error" class="error-box">{{ error }} {{ $t('backendErr') }}</div>

  <div v-if="loading">
    <div class="skeleton" v-for="n in 4" :key="n"></div>
  </div>

  <div v-else-if="grouped.length === 0" class="center">{{ $t('noMatches') }}</div>

  <div v-else>
    <section class="league-group" v-for="g in grouped" :key="g.league.id">
      <router-link class="league-group__head" :to="{ name: 'league', params: { id: g.league.id } }">
        <img :src="g.league.logo" :alt="g.league.name" />
        <span class="lg-name">{{ g.league.name }}</span>
        <span class="lg-hint">{{ $t('standingsHint') }} <span class="chev">›</span></span>
      </router-link>
      <MatchCard v-for="m in g.matches" :key="m.fixture.id" :fixture="m" />
    </section>
  </div>
</template>
