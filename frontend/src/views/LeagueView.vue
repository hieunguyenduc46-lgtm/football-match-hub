<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../services/api'
import { imgFallback } from '../utils/format'
import { t } from '../i18n'
import { teamName } from '../utils/countryNames'
import { leagueName as translateLeague } from '../utils/leagueNames'
import MatchCard from '../components/MatchCard.vue'

const route = useRoute()
const router = useRouter()
const raw = ref(null)
const scorers = ref([])
const loading = ref(true)
const tab = ref('standings') // 'standings' | 'scorers' | 'fixtures'

// Lịch đấu (tab 'fixtures') — tải LƯỜI: chỉ gọi API khi người dùng mở tab này.
const fixtures = ref({ recent: [], upcoming: [] })
const fxLoading = ref(false)
let fxLoadedId = null
async function loadFixtures(id) {
  if (!id || fxLoadedId === id) return
  fxLoadedId = id
  fxLoading.value = true
  fixtures.value = { recent: [], upcoming: [] }
  try {
    const { data } = await api.get(`/leagues/${id}/fixtures`)
    if (fxLoadedId === id) fixtures.value = { recent: data.recent || [], upcoming: data.upcoming || [] }
  } finally {
    if (fxLoadedId === id) fxLoading.value = false
  }
}
const hasFixtures = computed(() => fixtures.value.recent.length || fixtures.value.upcoming.length)
watch(tab, (v) => { if (v === 'fixtures') loadFixtures(route.params.id) })

// standings = mảng các "bảng" (giải thường: 1 bảng; World Cup: 8 bảng A–H).
const groups = computed(() => raw.value?.league?.standings || [])
const leagueName = computed(() => translateLeague(raw.value?.league?.name, raw.value?.league?.id ?? route.params.id) || t('league_default'))

// Tô màu vùng theo ĐÚNG 'description' mà API trả về cho từng hàng.
// Số suất dự cúp châu Âu khác nhau mỗi giải & mỗi mùa (vd PL 2025/26 có 5 suất C1),
// nên KHÔNG hardcode "top 4" nữa — đọc thẳng mô tả thật để khớp với Google.
function zoneByDesc(desc) {
  const d = (desc || '').toLowerCase()
  if (d.includes('relegation')) return 'zone-rel'
  if (d.includes('champions league')) return 'zone-cl'
  if (d.includes('europa league')) return 'zone-el'
  if (d.includes('conference')) return 'zone-conf'
  return '' // play-off / vòng loại khác -> không tô
}

// Fallback khi API không kèm 'description' (vd dữ liệu mock): top 4 = C1, 3 cuối = rớt hạng.
function zoneByRank(rank, n) {
  if (n < 8) return ''
  if (rank <= 4) return 'zone-cl'
  if (rank > n - 3) return 'zone-rel'
  return ''
}

// Bảng có ít nhất 1 hàng kèm description -> dùng dữ liệu thật; nếu không -> fallback theo thứ hạng.
function zone(row, g) {
  return g.some((r) => r.description) ? zoneByDesc(row.description) : zoneByRank(row.rank, g.length)
}

// Chú thích động: chỉ hiện những vùng thực sự có trong bảng.
const legendZones = computed(() => {
  const set = new Set()
  for (const g of groups.value) for (const r of g) { const z = zone(r, g); if (z) set.add(z) }
  const meta = [
    { z: 'zone-cl', dot: 'cl', label: 'zone_cl' },
    { z: 'zone-el', dot: 'el', label: 'zone_el' },
    { z: 'zone-conf', dot: 'conf', label: 'zone_conf' },
    { z: 'zone-rel', dot: 'rel', label: 'zone_rel' },
  ]
  return meta.filter((m) => set.has(m.z))
})

let loadSeq = 0
async function loadLeague(id) {
  const seq = ++loadSeq
  loading.value = true
  raw.value = null
  scorers.value = []
  fxLoadedId = null
  fixtures.value = { recent: [], upcoming: [] }
  if (tab.value === 'fixtures') loadFixtures(id)
  try {
    // Không cố định season nữa: để backend tự chọn mùa đúng theo giải
    // (vd World Cup -> 2026, VĐQG -> 2025).
    const [sRes, tsRes] = await Promise.all([
      api.get('/standings', { params: { league: id } }),
      api.get('/topscorers', { params: { league: id } }),
    ])
    if (seq !== loadSeq) return                   // đã chuyển sang giải khác
    raw.value = sRes.data.response?.[0] || null
    scorers.value = tsRes.data.response || []
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

// keep-alive: component bị cache, KHÔNG remount. Chỉ tải lại khi đây đúng là trang đang
// xem (route.name === 'league') VÀ là giải khác giải đã tải -> tránh tải nhầm khi bị cache,
// và tránh tải lại (mất vị trí cuộn) khi back về đúng giải cũ.
let loadedId = null
function syncLeague() {
  if (route.name !== 'league') return
  const id = route.params.id
  if (!id || id === loadedId) return
  loadedId = id
  loadLeague(id)
}
onMounted(syncLeague)
watch(() => route.params.id, syncLeague)

function goPlayer(id) {
  if (id) router.push({ name: 'player', params: { id } })
}
</script>

<template>
  <a href="#" class="back" @click.prevent="$router.back()">{{ $t('backHome') }}</a>
  <h1 class="page-title">{{ leagueName }}</h1>

  <div class="tabs">
    <button class="tab" :class="{ active: tab === 'standings' }" @click="tab = 'standings'">{{ $t('tab_standings') }}</button>
    <button class="tab" :class="{ active: tab === 'fixtures' }" @click="tab = 'fixtures'">{{ $t('tab_fixtures') }}</button>
    <button class="tab" :class="{ active: tab === 'scorers' }" @click="tab = 'scorers'">{{ $t('tab_scorers') }}</button>
  </div>

  <div v-if="loading && tab !== 'fixtures'" class="skeleton" style="height:200px"></div>

  <!-- Lịch đấu: kết quả gần đây + trận sắp tới -->
  <div v-else-if="tab === 'fixtures'">
    <div v-if="fxLoading">
      <div class="skeleton" v-for="n in 4" :key="n"></div>
    </div>
    <div v-else-if="!hasFixtures" class="center">{{ $t('noFixtures') }}</div>
    <template v-else>
      <template v-if="fixtures.upcoming.length">
        <h3 class="group-name">{{ $t('upcomingMatches') }}</h3>
        <MatchCard v-for="m in fixtures.upcoming" :key="'u' + m.fixture.id" :fixture="m" show-date />
      </template>
      <template v-if="fixtures.recent.length">
        <h3 class="group-name">{{ $t('results_h') }}</h3>
        <MatchCard v-for="m in fixtures.recent" :key="'r' + m.fixture.id" :fixture="m" show-date />
      </template>
    </template>
  </div>

  <!-- Bảng xếp hạng (1 bảng cho giải thường, nhiều bảng cho World Cup) -->
  <div v-else-if="tab === 'standings'">
    <div v-if="groups.length === 0" class="center">{{ $t('noStandings') }}</div>
    <template v-else>
      <div v-for="(g, gi) in groups" :key="gi" class="group-block">
        <h3 v-if="g[0] && g[0].group" class="group-name">{{ g[0].group }}</h3>
        <div class="table-wrap">
          <table class="standings">
            <thead>
              <tr><th>#</th><th class="team-cell">{{ $t('th_team') }}</th><th>{{ $t('th_played') }}</th><th>{{ $t('th_w') }}</th><th>{{ $t('th_d') }}</th><th>{{ $t('th_l') }}</th><th>{{ $t('th_gf') }}</th><th>{{ $t('th_ga') }}</th><th>{{ $t('th_gd') }}</th><th>{{ $t('th_pts') }}</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in g" :key="row.team.id" :class="zone(row, g)">
                <td>{{ row.rank }}</td>
                <td class="team-cell">
                  <router-link :to="{ name: 'team', params: { id: row.team.id } }" class="team-cell">
                    <img :src="row.team.logo" @error="imgFallback" />{{ teamName(row.team.name) }}
                  </router-link>
                </td>
                <td>{{ row.all.played }}</td>
                <td>{{ row.all.win }}</td>
                <td>{{ row.all.draw }}</td>
                <td>{{ row.all.lose }}</td>
                <td>{{ row.all.goals?.for ?? '-' }}</td>
                <td>{{ row.all.goals?.against ?? '-' }}</td>
                <td>{{ row.goalsDiff > 0 ? '+' : '' }}{{ row.goalsDiff }}</td>
                <td><strong>{{ row.points }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-if="legendZones.length" class="zone-legend">
        <span v-for="m in legendZones" :key="m.z"><i class="dot" :class="m.dot"></i> {{ $t(m.label) }}</span>
      </div>
    </template>
  </div>

  <!-- Vua phá lưới -->
  <div v-else>
    <div v-if="scorers.length === 0" class="center">{{ $t('noScorers') }}</div>
    <div v-else>
      <div
        v-for="(s, i) in scorers"
        :key="s.player.id"
        class="match-card"
        style="grid-template-columns:28px 40px 1fr auto"
        @click="goPlayer(s.player.id)"
      >
        <span class="muted" style="font-weight:700;text-align:center">{{ i + 1 }}</span>
        <img :src="s.player.photo" @error="imgFallback" style="width:36px;height:36px;border-radius:50%;object-fit:cover" />
        <span>
          <div style="font-weight:600">{{ s.player.name }}</div>
          <div class="muted" style="font-size:12px">{{ teamName(s.statistics[0].team.name) }}</div>
        </span>
        <span style="text-align:right">
          <strong style="font-size:18px">{{ s.statistics[0].goals.total }}</strong>
          <div class="muted" style="font-size:12px">{{ s.statistics[0].goals.assists ?? 0 }} {{ $t('assistsShort') }}</div>
        </span>
      </div>
    </div>
  </div>
</template>
