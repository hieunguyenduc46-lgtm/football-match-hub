<script setup>
import { ref, computed, onMounted, onUnmounted, onActivated, onDeactivated, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '../services/api'
import { isFinished, isLiveFixture, isStaleLive, isOff, offStatusKey, isBreak, breakStatusKey, matchTime, matchDayYear, imgFallback } from '../utils/format'
import { roundLabel } from '../utils/roundNames'
import { leagueName } from '../utils/leagueNames'
import { setTitle } from '../utils/title'
import { t } from '../i18n'
import LineupPitch from '../components/LineupPitch.vue'
import MatchTimeline from '../components/MatchTimeline.vue'
import MatchStats from '../components/MatchStats.vue'
import PlayerRatings from '../components/PlayerRatings.vue'
import H2HList from '../components/H2HList.vue'
import MatchPrediction from '../components/MatchPrediction.vue'
import FavButton from '../components/FavButton.vue'
import { teamName } from '../utils/countryNames'

const route = useRoute()
let id = route.params.id   // reassigned when the match changes (see the watch below)
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

// Goal minute: include stoppage time if any (e.g. 90+3).
function minuteLabel(time) {
  if (!time) return ''
  return time.extra ? `${time.elapsed}+${time.extra}` : `${time.elapsed}`
}

// Goal summary split by side, read straight from the loaded "events".
// Note: an own goal counts for the OPPOSING TEAM, so the side must be swapped.
const goalSummary = computed(() => {
  const out = { home: [], away: [] }
  if (!fixture.value) return out
  const homeId = fixture.value.teams.home.id
  for (const e of events.value) {
    if (e.type !== 'Goal' || e.detail === 'Missed Penalty') continue
    // Skip the penalty shootout: each kick is a Goal event but does NOT
    // count towards the main score -> adding them would make the summary's goal count wrong.
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

// League position: merge all groups (regular league = 1 group) then look up by team id.
const standingRows = computed(() => (standings.value?.[0]?.league?.standings || []).flat())
function rankOf(teamId) {
  const r = standingRows.value.find((x) => x.team?.id === teamId)
  return r ? r.rank : null
}
const homeRank = computed(() => rankOf(fixture.value?.teams.home.id))
const awayRank = computed(() => rankOf(fixture.value?.teams.away.id))

// Info line above the match: League · Round · Date (with year) · Time.
// Skip empty parts (e.g. a league with no 'round') so no extra '·' is shown.
const headerLine = computed(() => {
  if (!fixture.value) return ''
  return [
    leagueName(fixture.value.league?.name, fixture.value.league?.id),
    roundLabel(fixture.value.league?.round),
    matchDayYear(fixture.value.fixture?.date),
    matchTime(fixture.value.fixture?.date),
  ].filter(Boolean).join(' · ')
})

// Data for FOLLOWING the match (2 teams + date + league name) -> shown again on the Following page, linked to /match/:id.
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

// PENALTY SHOOTOUT score (if the match was decided on penalties). API-Football puts it in
// score.penalty = {home, away}; only has values when there really was a shootout -> used to
// show who won when the main score is a draw (e.g. UCL final 1-1 then 4-5 on pens). None -> null.
const penaltyScore = computed(() => {
  const p = fixture.value?.score?.penalty
  return (p && p.home != null && p.away != null) ? `${p.home} - ${p.away}` : null
})

// ===== 2-LEG ties (UCL knockouts...) =====
// API-Football does NOT label first/second legs. How we infer it: both legs of a tie share the SAME league +
// season + round, the same 2 teams (venues swapped), on different dates. Matched via H2H data, then:
//  - leg = by date order (earlier = 1st leg, later = 2nd leg),
//  - aggregate = goals summed per team across both legs (only shown on a finished 2nd leg).
// Can't be paired (e.g. single-leg final, single-leg domestic cup semi) -> legInfo = null -> nothing shown.
const legInfo = ref(null)   // { leg: 1|2, agg: {home, away} | null }

async function detectLeg(seq) {
  const fx = fixture.value
  if (!fx) return
  const round = fx.league?.round || ''
  // Only consider knockout rounds; skip group stage / league to avoid unnecessary H2H calls.
  if (!/round of|quarter|semi|final|play-?off|last \d+/i.test(round)) return
  const homeId = fx.teams.home.id, awayId = fx.teams.away.id
  let list = []
  try {
    const { data } = await api.get(`/fixtures/${id}/h2h`, { params: { home: homeId, away: awayId } })
    list = data.response || []
  } catch (e) { return }
  if (seq !== loadSeq) return
  // The other leg: same league + season + round, different fixture from the current one.
  const other = list.find((m) =>
    m.fixture?.id !== fx.fixture.id &&
    m.league?.id === fx.league?.id &&
    m.league?.season === fx.league?.season &&
    (m.league?.round || '') === round
  )
  if (!other) return                                   // not a 2-leg tie -> skip
  const isSecond = (fx.fixture?.date || '') >= (other.fixture?.date || '')
  // Sum goals by team id (because venues swap between legs).
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
  clearInterval(timer)          // stop the previous match's timer
  // Reset all state + tab cache so data from the previous match doesn't mix in.
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
  if (seq !== loadSeq) return                     // already switched to another match
  if (fRes.status === 'fulfilled') fixture.value = fRes.value.data.response?.[0] || null
  else error.value = fRes.reason?.message || t('loadMatchErr')
  if (fixture.value) setTitle(`${teamName(fixture.value.teams.home.name)} - ${teamName(fixture.value.teams.away.name)}`)
  if (fixture.value) detectLeg(seq)   // infer 1st/2nd leg + compute aggregate (knockout rounds only)
  if (lRes.status === 'fulfilled') lineups.value = lRes.value.data.response || []
  if (eRes.status === 'fulfilled') events.value = eRes.value.data.response || []
  loading.value = false

  // Load standings to show the position under each team name (the match's own league + season).
  if (fixture.value?.league) {
    api.get('/standings', { params: { league: fixture.value.league.id, season: fixture.value.league.season } })
      .then(({ data }) => { if (seq === loadSeq) standings.value = data.response || [] })
      .catch(() => {})
  }

  // Live match -> update every 15s (the API refresh rate), only while the tab is open.
  startTimer()
}

// Kept separate so onActivated (returning to a cached page) can restart polling too.
function startTimer() {
  clearInterval(timer)
  timer = setInterval(() => {
    // Only poll when the match is REALLY LIVE (ignore 'stale live' so we don't call the API forever for a dead match).
    if (!document.hidden && fixture.value && isLiveFixture(fixture.value)) refresh()
  }, 15000)
}

// keep-alive: the component is NOT remounted when changing match/going back. Only reload when this really is
// the page being viewed (route.name === 'match') AND it's a different match from the one loaded -> avoids:
//  (1) loading by mistake while on another page with the component still cached,
//  (2) reloading (losing scroll position) when going back to the same match.
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
    startTimer()                                           // coming back -> restart polling if needed
    setTitle(`${teamName(fixture.value.teams.home.name)} - ${teamName(fixture.value.teams.away.name)}`)
  }
})
onDeactivated(() => clearInterval(timer))                // leaving the page (still cached) -> stop polling

async function refresh() {
  const seq = loadSeq                              // capture seq at call time
  const [fRes, eRes] = await Promise.allSettled([
    api.get(`/fixtures/${id}`),
    api.get(`/fixtures/${id}/events`),
  ])
  if (seq !== loadSeq) return                      // already switched to another match -> drop the stale result
  if (fRes.status === 'fulfilled') fixture.value = fRes.value.data.response?.[0] || fixture.value
  if (eRes.status === 'fulfilled') events.value = eRes.value.data.response || events.value
}

// Lazy-load tab data on first open (saves requests when using the real API).
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
    fetched[name] = false // allow retry
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

    <!-- 1st/2nd leg tag for 2-leg ties (only shown when the tie could be paired) -->
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
        <!-- AGGREGATE score (only shown on a finished 2nd leg) -->
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
        <!-- Penalty shootout score (only shown when the match went to penalties) -> shows who won a draw. -->
        <div v-if="penaltyScore" class="pen-score">{{ $t('penalties') }} {{ penaltyScore }}</div>
      </div>

      <router-link :to="{ name: 'team', params: { id: fixture.teams.away.id } }" style="text-align:center; width:38%;">
        <img loading="lazy" :src="fixture.teams.away.logo" @error="imgFallback" style="width:56px;height:56px;object-fit:contain" />
        <div style="margin-top:8px;font-weight:600">{{ teamName(fixture.teams.away.name) }}</div>
        <div v-if="awayRank" class="rank-badge">#{{ awayRank }}</div>
      </router-link>
    </div>

    <!-- Goal summary: player name + minute, right under the score -->
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
