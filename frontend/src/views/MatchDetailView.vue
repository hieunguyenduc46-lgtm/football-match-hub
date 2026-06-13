<script setup>
import { ref, computed, onMounted, onUnmounted, onActivated, onDeactivated, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '../services/api'
import { isFinished, isLiveFixture, isStaleLive, isOff, offStatusKey, isBreak, breakStatusKey, matchTime, matchDayYear, imgFallback } from '../utils/format'
import { roundLabel } from '../utils/roundNames'
import { leagueName } from '../utils/leagueNames'
import { setTitle } from '../utils/title'
import LineupPitch from '../components/LineupPitch.vue'
import MatchTimeline from '../components/MatchTimeline.vue'
import MatchStats from '../components/MatchStats.vue'
import PlayerRatings from '../components/PlayerRatings.vue'
import H2HList from '../components/H2HList.vue'
import MatchPrediction from '../components/MatchPrediction.vue'
import FavButton from '../components/FavButton.vue'
import { teamName } from '../utils/countryNames'

const route = useRoute()
let id = route.params.id   // đổi trận sẽ gán lại (xem watch ở dưới)
const fixture = ref(null)
const lineups = ref([])
const events = ref([])
const stats = ref([])
const ratings = ref([])
const h2h = ref([])
const prediction = ref(null)
const standings = ref([])
const loading = ref(true)
const error = ref(null)
const tab = ref('lineup')

let timer = null

// Phút ghi bàn: kèm bù giờ nếu có (vd 90+3).
function minuteLabel(time) {
  if (!time) return ''
  return time.extra ? `${time.elapsed}+${time.extra}` : `${time.elapsed}`
}

// Tóm tắt bàn thắng tách theo 2 bên, đọc thẳng từ "events" đã tải.
// Lưu ý: phản lưới nhà (Own Goal) tính cho ĐỘI ĐỐI PHƯƠNG, nên phải đổi bên.
const goalSummary = computed(() => {
  const out = { home: [], away: [] }
  if (!fixture.value) return out
  const homeId = fixture.value.teams.home.id
  for (const e of events.value) {
    if (e.type !== 'Goal' || e.detail === 'Missed Penalty') continue
    // Bỏ qua loạt sút luân lưu (penalty shootout): mỗi quả là 1 event Goal nhưng KHÔNG
    // tính vào tỉ số chính -> nếu cộng sẽ làm sai số bàn ở tóm tắt.
    if (e.comments === 'Penalty Shootout') continue
    const og = e.detail === 'Own Goal'
    const scoredByHome = e.team?.id === homeId
    const side = og ? (scoredByHome ? 'away' : 'home') : (scoredByHome ? 'home' : 'away')
    out[side].push({
      id: e.player?.id || null,
      name: e.player?.name || '—',
      minute: minuteLabel(e.time),
      pen: e.detail === 'Penalty',
      og,
    })
  }
  return out
})

// Thứ hạng giải: gộp mọi bảng (giải thường 1 bảng) rồi tra theo team id.
const standingRows = computed(() => (standings.value?.[0]?.league?.standings || []).flat())
function rankOf(teamId) {
  const r = standingRows.value.find((x) => x.team?.id === teamId)
  return r ? r.rank : null
}
const homeRank = computed(() => rankOf(fixture.value?.teams.home.id))
const awayRank = computed(() => rankOf(fixture.value?.teams.away.id))

// Dòng thông tin trên đầu trận: Giải · Vòng đấu · Ngày (kèm năm) · Giờ.
// Bỏ qua phần nào rỗng (vd giải không có 'round') để không hiện dấu '·' thừa.
const headerLine = computed(() => {
  if (!fixture.value) return ''
  return [
    leagueName(fixture.value.league?.name, fixture.value.league?.id),
    roundLabel(fixture.value.league?.round),
    matchDayYear(fixture.value.fixture?.date),
    matchTime(fixture.value.fixture?.date),
  ].filter(Boolean).join(' · ')
})

// Dữ liệu để FOLLOW trận (2 đội + ngày + tên giải) -> hiện lại ở trang Theo dõi, link /match/:id.
const matchItem = computed(() => {
  if (!fixture.value) return null
  return {
    id: fixture.value.fixture?.id,
    home: { name: fixture.value.teams.home.name, logo: fixture.value.teams.home.logo },
    away: { name: fixture.value.teams.away.name, logo: fixture.value.teams.away.logo },
    date: fixture.value.fixture?.date,
    league: fixture.value.league?.name,
  }
})

// Tỉ số loạt LUÂN LƯU (nếu trận phân thắng bại bằng penalty). API-Football để ở
// score.penalty = {home, away}; chỉ có giá trị khi thật sự đá luân lưu -> dùng để
// hiện ai thắng khi tỉ số chính hoà (vd Chung kết C1 1-1 rồi pen 4-5). Không có -> null.
const penaltyScore = computed(() => {
  const p = fixture.value?.score?.penalty
  return (p && p.home != null && p.away != null) ? `${p.home} - ${p.away}` : null
})

// ===== Cặp đấu 2 LƯỢT (knockout C1...) =====
// API-Football KHÔNG gắn nhãn lượt đi/về. Cách suy: 2 lượt của cùng cặp có CÙNG giải +
// mùa + vòng, 2 đội giống nhau (đổi sân), khác ngày. Ghép qua dữ liệu H2H rồi:
//  - lượt = theo thứ tự ngày (trước = đi, sau = về),
//  - chung cuộc = cộng bàn theo từng đội qua 2 lượt (chỉ hiện ở lượt VỀ đã kết thúc).
// Không ghép được (vd chung kết 1 lượt, bán kết cúp QG 1 lượt) -> legInfo = null -> không hiện gì.
const legInfo = ref(null)   // { leg: 1|2, agg: {home, away} | null }

async function detectLeg(seq) {
  const fx = fixture.value
  if (!fx) return
  const round = fx.league?.round || ''
  // Chỉ xét vòng knockout; bỏ vòng bảng / VĐQG để khỏi gọi H2H thừa.
  if (!/round of|quarter|semi|final|play-?off|last \d+/i.test(round)) return
  const homeId = fx.teams.home.id, awayId = fx.teams.away.id
  let list = []
  try {
    const { data } = await api.get(`/fixtures/${id}/h2h`, { params: { home: homeId, away: awayId } })
    list = data.response || []
  } catch (e) { return }
  if (seq !== loadSeq) return
  // Lượt còn lại: cùng giải + mùa + vòng, khác fixture hiện tại.
  const other = list.find((m) =>
    m.fixture?.id !== fx.fixture.id &&
    m.league?.id === fx.league?.id &&
    m.league?.season === fx.league?.season &&
    (m.league?.round || '') === round
  )
  if (!other) return                                   // không phải cặp 2 lượt -> bỏ qua
  const isSecond = (fx.fixture?.date || '') >= (other.fixture?.date || '')
  // Cộng tổng bàn theo team id (vì đổi sân giữa 2 lượt).
  const tally = {}
  const add = (m) => {
    const hg = m.goals?.home, ag = m.goals?.away
    if (hg == null || ag == null) return false
    tally[m.teams.home.id] = (tally[m.teams.home.id] || 0) + hg
    tally[m.teams.away.id] = (tally[m.teams.away.id] || 0) + ag
    return true
  }
  const both = add(fx) && add(other)
  const finished = isFinished(fx.fixture.status.short) || isStaleLive(fx)
  const agg = (isSecond && finished && both)
    ? { home: tally[homeId] || 0, away: tally[awayId] || 0 }
    : null
  if (seq === loadSeq) legInfo.value = { leg: isSecond ? 2 : 1, agg }
}

let loadSeq = 0
async function loadMatch() {
  const seq = ++loadSeq
  clearInterval(timer)          // dừng timer của trận cũ
  // Reset toàn bộ trạng thái + cache tab để không lẫn dữ liệu trận trước.
  loading.value = true
  error.value = null
  fixture.value = null
  lineups.value = []
  events.value = []
  stats.value = []
  ratings.value = []
  h2h.value = []
  prediction.value = null
  standings.value = []
  legInfo.value = null
  tab.value = 'lineup'
  fetched = {}

  const [fRes, lRes, eRes] = await Promise.allSettled([
    api.get(`/fixtures/${id}`),
    api.get(`/fixtures/${id}/lineups`),
    api.get(`/fixtures/${id}/events`),
  ])
  if (seq !== loadSeq) return                     // đã chuyển sang trận khác
  if (fRes.status === 'fulfilled') fixture.value = fRes.value.data.response?.[0] || null
  else error.value = fRes.reason?.message || 'Không tải được trận đấu'
  if (fixture.value) setTitle(`${teamName(fixture.value.teams.home.name)} - ${teamName(fixture.value.teams.away.name)}`)
  if (fixture.value) detectLeg(seq)   // suy lượt đi/về + tính chung cuộc (chỉ vòng knockout)
  if (lRes.status === 'fulfilled') lineups.value = lRes.value.data.response || []
  if (eRes.status === 'fulfilled') events.value = eRes.value.data.response || []
  loading.value = false

  // Tải BXH để hiện thứ hạng dưới tên đội (đúng giải + mùa của trận).
  if (fixture.value?.league) {
    api.get('/standings', { params: { league: fixture.value.league.id, season: fixture.value.league.season } })
      .then(({ data }) => { if (seq === loadSeq) standings.value = data.response || [] })
      .catch(() => {})
  }

  // Trận đang đá -> cập nhật mỗi 15s (nhịp làm tươi của API), chỉ khi tab đang mở.
  startTimer()
}

// Tách riêng để onActivated (quay lại trang đã cache) cũng bật lại được polling.
function startTimer() {
  clearInterval(timer)
  timer = setInterval(() => {
    // Chỉ poll khi trận ĐANG ĐÁ THẬT (bỏ 'live treo' để không gọi API mãi cho trận đã chết).
    if (!document.hidden && fixture.value && isLiveFixture(fixture.value)) refresh()
  }, 15000)
}

// keep-alive: component KHÔNG remount khi đổi trận/back. Chỉ tải lại khi đây thực sự là
// trang đang xem (route.name === 'match') VÀ là trận khác trận đã tải -> tránh:
//  (1) tải nhầm khi đang ở trang khác mà component vẫn bị cache,
//  (2) tải lại (mất vị trí cuộn) khi back về đúng trận cũ.
let loadedId = null
function syncMatch() {
  if (route.name !== 'match') return
  const newId = route.params.id
  if (!newId || newId === loadedId) return
  loadedId = newId
  id = newId
  loadMatch()
}
onMounted(syncMatch)
watch(() => route.params.id, syncMatch)
onActivated(() => {
  if (fixture.value) {
    startTimer()                                           // quay lại -> bật lại polling nếu cần
    setTitle(`${teamName(fixture.value.teams.home.name)} - ${teamName(fixture.value.teams.away.name)}`)
  }
})
onDeactivated(() => clearInterval(timer))                // rời trang (vẫn bị cache) -> dừng polling

async function refresh() {
  const seq = loadSeq                              // chốt seq lúc gọi
  const [fRes, eRes] = await Promise.allSettled([
    api.get(`/fixtures/${id}`),
    api.get(`/fixtures/${id}/events`),
  ])
  if (seq !== loadSeq) return                      // đã chuyển sang trận khác -> bỏ kết quả cũ
  if (fRes.status === 'fulfilled') fixture.value = fRes.value.data.response?.[0] || fixture.value
  if (eRes.status === 'fulfilled') events.value = eRes.value.data.response || events.value
}

// Lazy-load dữ liệu tab khi mở lần đầu (tiết kiệm request khi dùng API thật).
let fetched = {}
async function selectTab(name) {
  tab.value = name
  if (fetched[name]) return
  fetched[name] = true
  try {
    if (name === 'stats') {
      const { data } = await api.get(`/fixtures/${id}/statistics`)
      stats.value = data.response || []
    } else if (name === 'ratings') {
      const { data } = await api.get(`/fixtures/${id}/players`)
      ratings.value = data.response || []
    } else if (name === 'h2h') {
      const params = { home: fixture.value?.teams.home.id, away: fixture.value?.teams.away.id }
      const { data } = await api.get(`/fixtures/${id}/h2h`, { params })
      h2h.value = data.response || []
    } else if (name === 'prediction') {
      const { data } = await api.get(`/fixtures/${id}/predictions`)
      prediction.value = data.response || null
    }
  } catch (e) {
    fetched[name] = false // cho phép thử lại
  }
}

onUnmounted(() => clearInterval(timer))
</script>

<template>
  <a href="#" class="back" @click.prevent="$router.back()">{{ $t('backHome') }}</a>

  <div v-if="loading" class="skeleton" style="height:120px"></div>
  <div v-else-if="error" class="error-box">{{ error }}</div>
  <div v-else-if="!fixture" class="center">{{ $t('matchNotFound') }}</div>

  <div v-else>
    <p class="muted" style="text-align:center">{{ headerLine }}</p>

    <!-- Tag lượt đi/về cho cặp đấu 2 lượt (chỉ hiện khi ghép được cặp) -->
    <div v-if="legInfo" style="text-align:center">
      <span class="leg-tag">{{ legInfo.leg === 2 ? $t('secondLeg') : $t('firstLeg') }}</span>
    </div>

    <div v-if="matchItem" style="display:flex; justify-content:center; margin:4px 0 2px;">
      <FavButton type="match" :item="matchItem" />
    </div>

    <div style="display:flex; align-items:center; justify-content:space-around; padding:18px 0;">
      <router-link :to="{ name: 'team', params: { id: fixture.teams.home.id } }" style="text-align:center; width:38%;">
        <img loading="lazy" :src="fixture.teams.home.logo" @error="imgFallback" style="width:56px;height:56px;object-fit:contain" />
        <div style="margin-top:8px;font-weight:600">{{ teamName(fixture.teams.home.name) }}</div>
        <div v-if="homeRank" class="rank-badge">#{{ homeRank }}</div>
      </router-link>

      <div style="text-align:center">
        <!-- Tỉ số CHUNG CUỘC (chỉ hiện ở lượt về đã kết thúc) -->
        <div v-if="legInfo && legInfo.agg" class="agg-score">{{ $t('aggregate') }} {{ legInfo.agg.home }} - {{ legInfo.agg.away }}</div>
        <div style="font-size:34px;font-weight:800" v-if="fixture.goals.home !== null">
          {{ fixture.goals.home }} - {{ fixture.goals.away }}
        </div>
        <div style="font-size:20px;font-weight:700" v-else>vs</div>
        <div class="muted" style="margin-top:4px;font-size:13px">
          <span v-if="isLiveFixture(fixture)" style="color:var(--live)"><template v-if="isBreak(fixture.fixture.status.short)">● {{ $t(breakStatusKey(fixture.fixture.status.short)) }}</template><template v-else>● {{ fixture.fixture.status.elapsed }}{{ fixture.fixture.status.extra ? '+' + fixture.fixture.status.extra : '' }}'</template></span>
          <span v-else-if="isFinished(fixture.fixture.status.short) || isStaleLive(fixture)">{{ $t('finished') }}</span>
          <span v-else-if="isOff(fixture.fixture.status.short)" style="color:var(--live)">{{ $t(offStatusKey(fixture.fixture.status.short)) }}</span>
          <span v-else>{{ $t('notStarted') }}</span>
        </div>
        <!-- Tỉ số luân lưu (chỉ hiện khi trận đá penalty) -> biết đội nào thắng khi hoà. -->
        <div v-if="penaltyScore" class="pen-score">{{ $t('penalties') }} {{ penaltyScore }}</div>
      </div>

      <router-link :to="{ name: 'team', params: { id: fixture.teams.away.id } }" style="text-align:center; width:38%;">
        <img loading="lazy" :src="fixture.teams.away.logo" @error="imgFallback" style="width:56px;height:56px;object-fit:contain" />
        <div style="margin-top:8px;font-weight:600">{{ teamName(fixture.teams.away.name) }}</div>
        <div v-if="awayRank" class="rank-badge">#{{ awayRank }}</div>
      </router-link>
    </div>

    <!-- Tóm tắt bàn thắng: tên cầu thủ + phút, ngay dưới tỉ số -->
    <div v-if="goalSummary.home.length || goalSummary.away.length" class="goal-summary">
      <div class="gs-side">
        <div v-for="(g, i) in goalSummary.home" :key="'h' + i" class="gs-item">
          <router-link v-if="g.id" :to="{ name: 'player', params: { id: g.id } }" class="gs-name link">{{ g.name }}</router-link>
          <span v-else class="gs-name">{{ g.name }}</span>
          <span class="gs-min">{{ g.minute }}'</span>
          <span v-if="g.pen" class="gs-tag">(P)</span>
          <span v-if="g.og" class="gs-tag">(OG)</span>
        </div>
      </div>
      <div class="gs-ball">⚽</div>
      <div class="gs-side right">
        <div v-for="(g, i) in goalSummary.away" :key="'a' + i" class="gs-item">
          <span v-if="g.pen" class="gs-tag">(P)</span>
          <span v-if="g.og" class="gs-tag">(OG)</span>
          <span class="gs-min">{{ g.minute }}'</span>
          <router-link v-if="g.id" :to="{ name: 'player', params: { id: g.id } }" class="gs-name link">{{ g.name }}</router-link>
          <span v-else class="gs-name">{{ g.name }}</span>
        </div>
      </div>
    </div>

    <div class="stat-grid" style="grid-template-columns:repeat(2,1fr)">
      <div class="stat"><div class="num" style="font-size:15px">{{ fixture.fixture.venue?.name || '—' }}</div><div class="label">{{ $t('venue') }}</div></div>
      <div class="stat"><div class="num" style="font-size:15px">{{ fixture.fixture.referee || '—' }}</div><div class="label">{{ $t('referee') }}</div></div>
    </div>

    <!-- Tabs -->
    <div class="tabs" style="margin-top:18px">
      <button class="tab" :class="{ active: tab === 'lineup' }" @click="selectTab('lineup')">{{ $t('tab_lineup') }}</button>
      <button class="tab" :class="{ active: tab === 'timeline' }" @click="selectTab('timeline')">{{ $t('tab_timeline') }}</button>
      <button class="tab" :class="{ active: tab === 'stats' }" @click="selectTab('stats')">{{ $t('tab_stats') }}</button>
      <button class="tab" :class="{ active: tab === 'ratings' }" @click="selectTab('ratings')">{{ $t('tab_ratings') }}</button>
      <button class="tab" :class="{ active: tab === 'h2h' }" @click="selectTab('h2h')">{{ $t('tab_h2h') }}</button>
      <button class="tab" :class="{ active: tab === 'prediction' }" @click="selectTab('prediction')">{{ $t('tab_prediction') }}</button>
    </div>

    <LineupPitch v-if="tab === 'lineup'" :lineups="lineups" />
    <MatchTimeline v-else-if="tab === 'timeline'" :events="events" :home-team-id="fixture.teams.home.id" />
    <MatchStats v-else-if="tab === 'stats'" :stats="stats" />
    <PlayerRatings v-else-if="tab === 'ratings'" :data="ratings" />
    <H2HList v-else-if="tab === 'h2h'" :matches="h2h" :home-team-id="fixture.teams.home.id" />
    <MatchPrediction v-else-if="tab === 'prediction'" :data="prediction || {}" :home="fixture.teams.home" :away="fixture.teams.away" />
  </div>
</template>

<style scoped>
.rank-badge {
  display: inline-block;
  margin-top: 4px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-dim);
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 1px 8px;
}

.goal-summary {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: start;
  gap: 10px;
  padding: 4px 0 14px;
}
.gs-side { display: flex; flex-direction: column; gap: 4px; }
.gs-side.right { align-items: flex-end; }
.gs-ball { font-size: 14px; padding-top: 2px; }
.gs-item { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.gs-side.right .gs-item { flex-direction: row; }
.gs-name { font-weight: 600; }
.gs-name.link { color: inherit; text-decoration: none; }
.gs-name.link:hover { color: var(--accent); text-decoration: underline; }
.gs-min { color: var(--text-dim); font-weight: 700; }
.gs-tag { color: var(--text-dim); font-size: 11px; }
.pen-score { margin-top: 3px; font-size: 13px; font-weight: 700; color: var(--accent-2); }
.leg-tag { display: inline-block; font-size: 12px; font-weight: 700; color: var(--accent-2); background: var(--surface-2); border: 1px solid var(--border); border-radius: 999px; padding: 2px 12px; margin-top: 2px; }
.agg-score { font-size: 13px; font-weight: 700; color: var(--text-dim); margin-bottom: 2px; }
</style>
