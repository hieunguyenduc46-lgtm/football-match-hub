<script setup>
import { ref, computed, onMounted, onUnmounted, onActivated, onDeactivated, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useFixturesStore } from '../stores/fixtures'
import api from '../services/api'
import MatchCard from '../components/MatchCard.vue'
import SearchBox from '../components/SearchBox.vue'
import { leagueName } from '../utils/leagueNames'
import { isFinished, isLiveFixture, isStaleLive } from '../utils/format'
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
  if (document.hidden) return
  maybeRollDate()
  // Quay lại tab: nếu đang có trận live/sắp đá thì làm mới ngay (khỏi đợi tới 15s sau).
  if (selectedDate.value === todayIso() && hasLiveOrImminent()) load(true)
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

// Thứ tự ưu tiên trong mỗi giải: đang đá (0) -> sắp đá (1) -> đã kết thúc (2).
function matchRank(f) {
  const s = f.fixture?.status?.short
  if (isLiveFixture(f)) return 0                    // đang đá THẬT -> lên đầu
  if (isFinished(s) || isStaleLive(f)) return 2     // đã xong (gồm cả 'live treo') -> xuống cuối
  return 1
}

// Gom theo giải, rồi sắp xếp mỗi giải: live lên đầu, kế đến trận chưa đá (theo giờ),
// cuối cùng là trận đã xong. Cùng nhóm thì xếp theo giờ đá tăng dần.
const grouped = computed(() => {
  const map = {}
  for (const f of fixtures.value) {
    if (!f?.league?.id) continue          // bỏ qua fixture thiếu league -> tránh crash
    const key = f.league.id
    if (!map[key]) map[key] = { league: f.league, matches: [] }
    map[key].matches.push(f)
  }
  const groups = Object.values(map)
  for (const g of groups) {
    g.matches.sort((a, b) => {
      const r = matchRank(a) - matchRank(b)
      if (r !== 0) return r
      return new Date(a.fixture.date) - new Date(b.fixture.date)
    })
  }
  return groups
})

watch([selectedDate, selectedLeague], () => load())

// Auto-refresh: làm mới ngầm (nhịp 15s) để cập nhật tỉ số trận đang đá.
// 15s = nhịp làm tươi của API-Football (poll nhanh hơn cũng không có dữ liệu mới).
// Backend cache (LIVE_TTL=15s, dùng chung) đảm bảo dù 100 user cùng poll thì
// API-Football vẫn chỉ bị gọi tối đa 1 lần mỗi 15s cho mỗi cache key.
let timer = null

// Cửa sổ poll quanh giờ bóng lăn: bắt đầu sớm 15p trước, và còn poll tới 30p sau giờ đá
// (phòng trường hợp status cập nhật trễ vài phút sau khi trận thực sự bắt đầu).
const POLL_LEAD_MS = 15 * 60 * 1000
const POLL_GRACE_MS = 30 * 60 * 1000
// Chỉ trận CHƯA ĐÁ thật sự (NS/TBD) mới được tính là "sắp đá". KHÔNG tính các trận
// hoãn/huỷ/bỏ (PST/CANC/ABD/SUSP...) — chúng có giờ đá trong quá khứ nhưng không bao giờ
// chuyển sang live, nếu tính sẽ làm poll chạy hoài vô ích.
const SCHEDULED = ['NS', 'TBD']

// Có trận nào ĐÁNG để poll không? = đang đá, HOẶC sắp đá (NS/TBD và giờ đá nằm trong
// khoảng [now-30p, now+15p]). Không có trận nào như vậy -> khỏi gọi API, tiết kiệm quota
// (vd 3h sáng không trận, hoặc cả ngày toàn trận đã xong -> im hẳn).
function hasLiveOrImminent() {
  const now = Date.now()
  for (const f of fixtures.value) {
    const s = f.fixture?.status?.short
    if (isLiveFixture(f)) return true   // CHỈ trận đang đá thật mới đáng poll (bỏ 'live treo')
    if (SCHEDULED.includes(s)) {
      const kickoff = new Date(f.fixture.date).getTime()
      if (!Number.isNaN(kickoff) && kickoff <= now + POLL_LEAD_MS && kickoff >= now - POLL_GRACE_MS) return true
    }
  }
  return false
}

// Interval vẫn chạy mỗi 15s nhưng CHỈ gọi API khi: tab hiển thị + đang xem hôm nay +
// có trận live/sắp đá. Bản thân setInterval không tốn request; chỉ load(true) mới tốn.
function startPolling() {
  clearInterval(timer)
  timer = setInterval(() => {
    maybeRollDate()
    if (!document.hidden && selectedDate.value === todayIso() && hasLiveOrImminent()) load(true)
  }, 15000)
  document.addEventListener('visibilitychange', onVisible)
}
function stopPolling() {
  clearInterval(timer)
  document.removeEventListener('visibilitychange', onVisible)
}

onMounted(async () => {
  try {
    const { data } = await api.get('/leagues')
    leagues.value = data.response || []
  } catch (e) { /* không sao, vẫn dùng bộ lọc 'Tất cả' */ }
  load()
})
// keep-alive: rời Home (vào chi tiết) -> dừng poll; quay lại -> bật lại.
// (onActivated chạy cả lần mount đầu tiên nên không cần gọi trong onMounted.)
onActivated(startPolling)
onDeactivated(stopPolling)
onUnmounted(stopPolling)
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

  <!-- Tìm giải / quốc gia -->
  <div class="filter-row">
    <SearchBox />
  </div>

  <!-- Lọc giải -->
  <div class="filter-row">
    <label class="muted" style="font-size:13px">{{ $t('league') }}</label>
    <select v-model="selectedLeague" class="league-select">
      <option value="">{{ $t('all') }}</option>
      <option v-for="l in leagues" :key="l.id" :value="l.id">{{ leagueName(l.name, l.id) }}</option>
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
      <router-link class="league-group__head" :to="{ name: 'league', params: { id: g.league.id }, query: g.league.season ? { season: g.league.season } : {} }">
        <img loading="lazy" :src="g.league.logo" :alt="g.league.name" />
        <span class="lg-name">{{ leagueName(g.league.name, g.league.id) }}</span>
        <span class="lg-hint">{{ $t('standingsHint') }} <span class="chev">›</span></span>
      </router-link>
      <MatchCard v-for="m in g.matches" :key="m.fixture.id" :fixture="m" />
    </section>
  </div>
</template>
