<script setup>
import { ref, computed, onMounted, onActivated, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../services/api'
import { imgFallback } from '../utils/format'
import { setTitle } from '../utils/title'
import { t } from '../i18n'
import { teamName } from '../utils/countryNames'
import { leagueName as translateLeague } from '../utils/leagueNames'
import MatchCard from '../components/MatchCard.vue'
import FavButton from '../components/FavButton.vue'
import KnockoutBracket from '../components/KnockoutBracket.vue'
import { useFavoritesStore } from '../stores/favorites'

const favs = useFavoritesStore()

// Leagues WITH knockout rounds -> show the "Bracket" tab. Uses a curated list so we do NOT
// make a heavy API call (whole season) for regular leagues that have no bracket.
const BRACKET_LEAGUES = new Set([
  1, 2, 3, 848, 4, 9, 15, 5, 13, 11, 16, 6, 7, 17,   // C1/C2/C3, World Cup, Euro, Copa America, Club WC, Nations, Libertadores...
  45, 143, 137, 81, 66, 48,                          // domestic cups: FA Cup, Copa del Rey, Coppa Italia, DFB Pokal, Coupe de France, EFL Cup
])

const route = useRoute()
const router = useRouter()
const raw = ref(null)
const scorers = ref([])
const loading = ref(true)
const tab = ref('standings') // 'standings' | 'scorers' | 'fixtures'

// Fixtures ('fixtures' tab) — LAZY loaded: only calls the API when the user opens this tab.
const fixtures = ref({ recent: [], upcoming: [] })
const fxLoading = ref(false)
let fxLoadedId = null
async function loadFixtures(id, yr) {
  const key = `${id}:${yr || ''}`
  if (!id || fxLoadedId === key) return
  fxLoadedId = key
  fxLoading.value = true
  fixtures.value = { recent: [], upcoming: [] }
  try {
    const { data } = await api.get(`/leagues/${id}/fixtures`, { params: yr ? { season: yr } : {} })
    if (fxLoadedId === key) fixtures.value = { recent: data.recent || [], upcoming: data.upcoming || [] }
  } finally {
    if (fxLoadedId === key) fxLoading.value = false
  }
}
const hasFixtures = computed(() => fixtures.value.recent.length || fixtures.value.upcoming.length)
watch(tab, (v) => { if (v === 'fixtures') loadFixtures(route.params.id, season.value) })

// ===== Choose SEASON / EDITION (WC 2022 vs 2026, UCL 24/25 vs 25/26...) =====
const seasons = ref([])      // [{year, current}] to fill the dropdown
const season = ref(null)     // selected season; null = let the backend pick the default
// National-team / calendar-year competitions -> single-year label ("2022"); others get a split-season label ("2025/26").
const SINGLE_YEAR = new Set([1, 4, 9, 5, 6, 7, 10, 15, 253, 22, 21])
function seasonLabel(yr) {
  if (SINGLE_YEAR.has(Number(route.params.id))) return String(yr)
  return `${yr}/${String(yr + 1).slice(-2)}`
}
function seasonParams(id) {
  const p = { league: id }
  if (season.value) p.season = season.value
  return p
}

// Bracket ('bracket' tab) — only for leagues with knockouts; LAZY loaded when the tab opens.
const showBracketTab = computed(() => BRACKET_LEAGUES.has(Number(route.params.id)))
const bracket = ref([])
const brLoading = ref(false)
let brLoadedId = null
async function loadBracket(id, yr) {
  const key = `${id}:${yr || ''}`
  if (!id || brLoadedId === key) return
  brLoadedId = key
  brLoading.value = true
  bracket.value = []
  try {
    const { data } = await api.get(`/leagues/${id}/bracket`, { params: yr ? { season: yr } : {} })
    if (brLoadedId === key) bracket.value = data.response || []
  } finally {
    if (brLoadedId === key) brLoading.value = false
  }
}
watch(tab, (v) => { if (v === 'bracket') loadBracket(route.params.id, season.value) })

// ===== Other player leaderboards: Assists / Yellow cards / Red cards =====
// LAZY loaded like the Fixtures/Bracket tabs: only calls the API when the user opens that tab.
const BOARD_EP = { assists: '/topassists', ycards: '/topyellowcards', rcards: '/topredcards' }
const boards = ref({ assists: [], ycards: [], rcards: [] })
const boardLoading = ref(false)
const boardKey = { assists: null, ycards: null, rcards: null }
async function loadBoard(kind) {
  const id = route.params.id
  const key = `${id}:${season.value || ''}`
  if (!id || boardKey[kind] === key) return
  boardKey[kind] = key
  boardLoading.value = true
  boards.value[kind] = []
  try {
    const { data } = await api.get(BOARD_EP[kind], { params: seasonParams(id) })
    if (boardKey[kind] === key) boards.value[kind] = data.response || []
  } finally {
    if (boardKey[kind] === key) boardLoading.value = false
  }
}
function resetBoards() { boardKey.assists = boardKey.ycards = boardKey.rcards = null; boards.value = { assists: [], ycards: [], rcards: [] } }
watch(tab, (v) => { if (v in BOARD_EP) loadBoard(v) })

// List + stat shown for the current tab (shares the render block with top scorers).
const activeBoard = computed(() => (tab.value in BOARD_EP ? boards.value[tab.value] : scorers.value))
function mainStat(s) {
  const st = s.statistics?.[0] || {}
  if (tab.value === 'assists') return st.goals?.assists ?? 0
  if (tab.value === 'ycards') return st.cards?.yellow ?? 0
  if (tab.value === 'rcards') return st.cards?.red ?? 0
  return st.goals?.total ?? 0
}
function subStat(s) {
  const st = s.statistics?.[0] || {}
  if (tab.value === 'assists') return `${st.goals?.total ?? 0} ${t('goalsShort')}`
  if (tab.value === 'ycards') return `${st.cards?.red ?? 0} ${t('redShort')}`
  if (tab.value === 'rcards') return `${st.cards?.yellow ?? 0} ${t('yellowShort')}`
  return `${st.goals?.assists ?? 0} ${t('assistsShort')}`
}

// standings = array of "groups" (regular league: 1 table; World Cup: 8 groups A–H).
// DE-DUPLICATE teams in each group by id: the API sometimes returns each team twice (e.g. World Cup
// 2026 -> 8 rows/4 teams). Keep the FIRST row per team so the table isn't duplicated.
const groups = computed(() => {
  const raws = raw.value?.league?.standings || []
  return raws.map((g) => {
    const seen = new Set()
    return (g || []).filter((row) => {
      const id = row?.team?.id
      if (id == null) return true
      if (seen.has(id)) return false
      seen.add(id)
      return true
    })
  })
})
const leagueName = computed(() => translateLeague(raw.value?.league?.name, raw.value?.league?.id ?? route.params.id) || t('league_default'))

// Data for FOLLOWING the league (stores id + original name + logo). Logo comes from standings, else built from the id.
const leagueItem = computed(() => ({
  id: Number(route.params.id),
  name: raw.value?.league?.name || leagueName.value,
  logo: raw.value?.league?.logo || `https://media.api-sports.io/football/leagues/${route.params.id}.png`,
}))

// Colour zones using EXACTLY the 'description' the API returns for each row.
// The number of European spots differs per league & per season (e.g. PL 2025/26 has 5 UCL spots),
// so do NOT hard-code "top 4" any more — read the real description so it matches Google.
function zoneByDesc(desc) {
  const d = (desc || '').toLowerCase()
  if (d.includes('relegation')) return 'zone-rel'
  if (d.includes('champions league')) return 'zone-cl'
  if (d.includes('europa league')) return 'zone-el'
  if (d.includes('conference')) return 'zone-conf'
  return '' // play-off / other qualifiers -> no colour
}

// Only colour UCL/UEL/UECL/relegation zones for Europe's top 5 leagues — where these labels are CORRECT.
// Other leagues (V-League, cups, AFC...) often have descriptions like "Champions League 2"... -> mapping them would
// give wrong/silly European labels, so do NOT colour zones for them (show a plain, clean table).
const ZONE_LEAGUES = new Set([39, 140, 135, 78, 61])

function zone(row, g) {
  if (!ZONE_LEAGUES.has(Number(route.params.id))) return ''
  return zoneByDesc(row.description)
}

// Dynamic legend: only show zones that actually appear in the table.
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

// Load standings + top scorers for the selected season (season.value). Kept separate so changing season can call it again.
async function loadStandingsScorers(id, seq) {
  try {
    const [sRes, tsRes] = await Promise.all([
      api.get('/standings', { params: seasonParams(id) }),
      api.get('/topscorers', { params: seasonParams(id) }),
    ])
    if (seq !== loadSeq) return                   // already switched to another league/season
    raw.value = sRes.data.response?.[0] || null
    scorers.value = tsRes.data.response || []
    // No season chosen yet -> use the backend's default season to show in the dropdown.
    if (!season.value && raw.value?.league?.season) season.value = raw.value.league.season
    setTitle(leagueName.value)
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

async function loadLeague(id) {
  const seq = ++loadSeq
  loading.value = true
  raw.value = null
  scorers.value = []
  fxLoadedId = null
  fixtures.value = { recent: [], upcoming: [] }
  brLoadedId = null
  bracket.value = []
  resetBoards()
  // Initial season: from the URL (?season=...) when coming from a match; otherwise use the backend default.
  season.value = Number(route.query.season) || null
  seasons.value = []
  api.get(`/leagues/${id}/seasons`).then(({ data }) => { if (seq === loadSeq) seasons.value = data.response || [] }).catch(() => {})
  if (tab.value === 'fixtures') loadFixtures(id, season.value)
  if (tab.value === 'bracket') loadBracket(id, season.value)
  if (tab.value in BOARD_EP) loadBoard(tab.value)
  await loadStandingsScorers(id, seq)
}

// Changing season in the dropdown -> reload standings/top scorers/fixtures/bracket for the new season.
function changeSeason(yr) {
  const id = route.params.id
  season.value = Number(yr) || null
  const seq = ++loadSeq
  loading.value = true
  raw.value = null
  scorers.value = []
  loadStandingsScorers(id, seq)
  fxLoadedId = null
  fixtures.value = { recent: [], upcoming: [] }
  if (tab.value === 'fixtures') loadFixtures(id, season.value)
  brLoadedId = null
  bracket.value = []
  if (tab.value === 'bracket') loadBracket(id, season.value)
  resetBoards()
  if (tab.value in BOARD_EP) loadBoard(tab.value)
}

// keep-alive: the component is cached, NOT remounted. Only reload when this really is the page being
// viewed (route.name === 'league') AND it's a different league from the one loaded -> avoids loading by mistake while cached,
// and avoids reloading (losing scroll position) when going back to the same league.
let loadedKey = null
function syncLeague() {
  if (route.name !== 'league') return
  const id = route.params.id
  if (!id) return
  // Keyed on id + season in the URL: change league OR change ?season (coming from a match in another season) -> reload.
  const key = `${id}:${route.query.season || ''}`
  if (key === loadedKey) return
  loadedKey = key
  loadLeague(id)
}
onMounted(syncLeague)
watch(() => [route.params.id, route.query.season], syncLeague)
onActivated(() => { if (route.name === 'league') setTitle(leagueName.value) })

function goPlayer(id) {
  if (id) router.push({ name: 'player', params: { id } })
}
</script>

<template>
  <a href="#" class="back" @click.prevent="$router.back()">{{ $t('backHome') }}</a>
  <div style="display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap;">
    <h1 class="page-title" style="margin:0">{{ leagueName }}</h1>
    <FavButton type="league" :item="leagueItem" />
  </div>

  <div class="tabs">
    <button class="tab" :class="{ active: tab === 'standings' }" @click="tab = 'standings'">{{ $t('tab_standings') }}</button>
    <button class="tab" :class="{ active: tab === 'fixtures' }" @click="tab = 'fixtures'">{{ $t('tab_fixtures') }}</button>
    <button v-if="showBracketTab" class="tab" :class="{ active: tab === 'bracket' }" @click="tab = 'bracket'">{{ $t('tab_bracket') }}</button>
    <button class="tab" :class="{ active: tab === 'scorers' }" @click="tab = 'scorers'">{{ $t('tab_scorers') }}</button>
    <button class="tab" :class="{ active: tab === 'assists' }" @click="tab = 'assists'">{{ $t('tab_assists') }}</button>
    <button class="tab" :class="{ active: tab === 'ycards' }" @click="tab = 'ycards'">{{ $t('tab_ycards') }}</button>
    <button class="tab" :class="{ active: tab === 'rcards' }" @click="tab = 'rcards'">{{ $t('tab_rcards') }}</button>
  </div>

  <!-- Choose season / edition -->
  <div v-if="seasons.length" class="filter-row" style="margin-top:10px">
    <label class="muted" style="font-size:13px">{{ $t('seasonLabel') }}</label>
    <select class="league-select" :value="season" @change="changeSeason($event.target.value)">
      <option v-for="s in seasons" :key="s.year" :value="s.year">{{ seasonLabel(s.year) }}</option>
    </select>
  </div>

  <!-- Bracket (knockout) -->
  <div v-if="tab === 'bracket'">
    <div v-if="brLoading"><div class="skeleton" style="height:240px"></div></div>
    <KnockoutBracket v-else :matches="bracket" />
  </div>

  <div v-else-if="loading && tab !== 'fixtures'" class="skeleton" style="height:200px"></div>

  <!-- Fixtures: recent results + upcoming matches -->
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

  <!-- Standings (1 table for regular leagues, several groups for the World Cup) -->
  <div v-else-if="tab === 'standings'">
    <div v-if="groups.length === 0" class="center">{{ $t('noStandings') }}</div>
    <template v-else>
      <div v-for="(g, gi) in groups" :key="gi" class="group-block">
        <h3 v-if="g[0] && g[0].group" class="group-name">{{ g[0].group }}</h3>
        <div class="table-wrap">
          <table class="standings">
            <thead>
              <tr><th>#</th><th class="team-cell">{{ $t('th_team') }}</th><th>{{ $t('th_played') }}</th><th>{{ $t('th_w') }}</th><th>{{ $t('th_d') }}</th><th>{{ $t('th_l') }}</th><th>{{ $t('th_gf') }}</th><th>{{ $t('th_ga') }}</th><th>{{ $t('th_gd') }}</th><th>{{ $t('th_pts') }}</th><th class="form-th">{{ $t('th_form') }}</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in g" :key="row.team.id" :class="[zone(row, g), { 'fav-team': favs.isTeamFav(row.team.id) }]">
                <td>{{ row.rank }}</td>
                <td class="team-cell">
                  <router-link :to="{ name: 'team', params: { id: row.team.id } }" class="team-cell">
                    <img loading="lazy" :src="row.team.logo" @error="imgFallback" />{{ teamName(row.team.name) }}<span v-if="favs.isTeamFav(row.team.id)" class="fav-star" title="Đang theo dõi">★</span>
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
                <td class="form-td">
                  <span v-if="row.form" class="std-form">
                    <!-- The API returns form NEWEST->OLDEST; reverse it to show OLDEST->NEWEST (latest on the right). -->
                    <span v-for="(r, i) in String(row.form).slice(0, 5).split('').reverse()" :key="i" class="form-b" :class="'f-' + r">{{ r }}</span>
                  </span>
                  <span v-else class="muted">–</span>
                </td>
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

  <!-- Player leaderboards: Top scorers / Assists / Yellow cards / Red cards -->
  <div v-else>
    <div v-if="boardLoading" class="skeleton" style="height:200px"></div>
    <div v-else-if="activeBoard.length === 0" class="center">{{ tab === 'scorers' ? $t('noScorers') : $t('noLeaderboard') }}</div>
    <div v-else>
      <div
        v-for="(s, i) in activeBoard"
        :key="s.player.id"
        class="match-card"
        style="grid-template-columns:28px 40px 1fr auto"
        @click="goPlayer(s.player.id)"
      >
        <span class="muted" style="font-weight:700;text-align:center">{{ i + 1 }}</span>
        <img loading="lazy" :src="s.player.photo" @error="imgFallback" style="width:36px;height:36px;border-radius:50%;object-fit:cover" />
        <span>
          <div style="font-weight:600">{{ s.player.name }}</div>
          <div class="muted" style="font-size:12px">{{ teamName(s.statistics?.[0]?.team?.name || '') }}</div>
        </span>
        <span style="text-align:right">
          <strong style="font-size:18px">{{ mainStat(s) }}</strong>
          <div class="muted" style="font-size:12px">{{ subStat(s) }}</div>
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Form column in the standings: reuses the global .form-b chips but smaller to fit the table */
.std-form { display: inline-flex; gap: 3px; }
.std-form .form-b { width: 17px; height: 17px; font-size: 9px; border-radius: 4px; }
.form-th, .form-td { text-align: center; white-space: nowrap; }
/* Highlight the followed team's row (light yellow background + star, matching the "Follow" button) */
.standings tbody tr.fav-team td { background: rgba(245, 197, 66, 0.18); }
.fav-star { color: #f5c542; margin-left: 5px; font-size: 12px; }
</style>
