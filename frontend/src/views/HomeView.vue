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

// Viewer's time zone (e.g. "Asia/Ho_Chi_Minh", "Australia/Sydney").
const tz = Intl.DateTimeFormat().resolvedOptions().timeZone

// ---- Date strip in the viewer's LOCAL TIME ----
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
    const dt = new Date(base.getFullYear(), base.getMonth(), base.getDate() + d) // local midnight
    out.push({ iso: localISO(dt), dt, today: d === 0 })
  }
  return out
}
const dates = ref(buildDates())
const selectedDate = ref(dates.value.find((d) => d.today).iso)
// PRO plan: any date is available (past + future) -> no limit on the date picker any more.

// Displayed date label: formatted OURSELVES by the site language (VI/EN) instead of letting <input type=date>
// follow the OPERATING SYSTEM language (e.g. a Vietnamese iPhone shows "ngày 12 thg 6" even when the site is in EN).
// toLocaleDateString with an explicit locale -> always matches the site language whatever the device is set to.
const dateInput = ref(null)
const dateLabel = computed(() => {
  const parts = String(selectedDate.value || '').split('-')
  if (parts.length !== 3) return selectedDate.value
  const [y, m, d] = parts.map(Number)
  const dt = new Date(y, m - 1, d)
  if (isNaN(dt.getTime())) return selectedDate.value
  const loc = state.locale === 'vi' ? 'vi-VN' : 'en-GB'
  return dt.toLocaleDateString(loc, { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })
})
// Desktop: clicking the date area must call showPicker() to open the calendar (mobile opens it on tap).
function openDatePicker() {
  try { dateInput.value?.showPicker?.() } catch (e) { /* older browsers / mobile already open it */ }
}
// Touch device (phone/tablet)? -> use the self-formatted label (because iOS ignores `lang`).
// Computer (mouse/trackpad) -> use the NATIVE date input so the date can be TYPED; the native input on
// desktop respects `lang`, so it still shows the right VI/EN format.
// '(pointer: coarse)' = the PRIMARY pointer is touch (phone/tablet). A laptop with
// a touchscreen still has trackpad/mouse as primary -> 'fine' -> uses the typeable input.
const isTouch = typeof window !== 'undefined' && !!window.matchMedia?.('(pointer: coarse)')?.matches
const dateLang = computed(() => (state.locale === 'vi' ? 'vi' : 'en-GB'))

function todayIso() {
  return localISO(new Date())
}
// If the day has rolled over (tab left open overnight) -> rebuild the date strip and move "Today" to the right date.
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
  // Back on the tab: if there are live/upcoming matches, refresh now (instead of waiting up to 15s).
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

// ---- League filter ----
const leagues = ref([])
const selectedLeague = ref('') // '' = all

async function load(silent = false) {
  // ALWAYS load every match of the day (by date + tz only), do NOT filter by league in the backend.
  // Reason: filtering by league in the API requires a "season", and the right season can't be guessed for every
  // league (South America/Nordics run on the calendar year, Europe spans 2 years, World Cup is pinned to a year...).
  // -> League filtering is done ON THE CLIENT from this full list (see computed `grouped`) so it works for every league.
  await store.fetchFixtures({ date: selectedDate.value, tz }, { silent })
}

// Priority within each league: live (0) -> upcoming (1) -> finished (2).
function matchRank(f) {
  const s = f.fixture?.status?.short
  if (isLiveFixture(f)) return 0                    // REALLY live -> to the top
  if (isFinished(s) || isStaleLive(f)) return 2     // finished (including 'stale live') -> to the bottom
  return 1
}

// Group by league, then sort each league: live first, then not-started matches (by kick-off time),
// finished matches last. Within a group, sort by kick-off time ascending.
const grouped = computed(() => {
  const lf = selectedLeague.value ? Number(selectedLeague.value) : null   // league being filtered (if any)
  const map = {}
  for (const f of fixtures.value) {
    if (!f?.league?.id) continue          // skip fixtures missing a league -> avoid crashes
    if (lf && f.league.id !== lf) continue // filter by the selected league (client-side, correct for every league)
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

// Only changing the DATE needs an API reload; changing the LEAGUE just re-filters `grouped` (no extra API call).
watch(selectedDate, () => load())

// Auto-refresh: silent refresh (every 15s) to update scores of live matches.
// 15s = API-Football's refresh rate (polling faster gives no new data).
// The backend cache (LIVE_TTL=15s, shared) ensures that even if 100 users poll at once,
// API-Football is still called at most once every 15s per cache key.
let timer = null

// Polling window around kick-off: start 15 min early, and keep polling until 30 min after kick-off
// (in case the status updates a few minutes after the match actually starts).
const POLL_LEAD_MS = 15 * 60 * 1000
const POLL_GRACE_MS = 30 * 60 * 1000
// Only matches that have REALLY not started (NS/TBD) count as "upcoming". Do NOT count
// postponed/cancelled/abandoned matches (PST/CANC/ABD/SUSP...) — they have a kick-off time in the past but never
// go live; counting them would keep polling forever for nothing.
const SCHEDULED = ['NS', 'TBD']

// Is any match WORTH polling? = live, OR upcoming (NS/TBD with kick-off in
// [now-30m, now+15m]). No such match -> skip the API call and save quota
// (e.g. 3am with no matches, or a day where every match is finished -> fully quiet).
function hasLiveOrImminent() {
  const now = Date.now()
  for (const f of fixtures.value) {
    const s = f.fixture?.status?.short
    if (isLiveFixture(f)) return true   // ONLY really-live matches are worth polling (ignore 'stale live')
    if (SCHEDULED.includes(s)) {
      const kickoff = new Date(f.fixture.date).getTime()
      if (!Number.isNaN(kickoff) && kickoff <= now + POLL_LEAD_MS && kickoff >= now - POLL_GRACE_MS) return true
    }
  }
  return false
}

// The interval still ticks every 15s but ONLY calls the API when: tab visible + viewing today +
// there are live/upcoming matches. setInterval itself costs no requests; only load(true) does.
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
  } catch (e) { /* no problem, the 'All' filter is still used */ }
  load()
})
// keep-alive: leaving Home (to a detail page) -> stop polling; coming back -> start again.
// (onActivated also runs on the first mount, so no need to call it in onMounted.)
onActivated(startPolling)
onDeactivated(stopPolling)
onUnmounted(stopPolling)
</script>

<template>
  <!-- Date strip -->
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

  <!-- Search league / country -->
  <div class="filter-row">
    <SearchBox />
  </div>

  <!-- League filter -->
  <div class="filter-row">
    <label for="league-filter" class="muted" style="font-size:13px">{{ $t('league') }}</label>
    <select id="league-filter" v-model="selectedLeague" class="league-select">
      <option value="">{{ $t('all') }}</option>
      <option v-for="l in leagues" :key="l.id" :value="l.id">{{ leagueName(l.name, l.id) }}</option>
    </select>
    <!-- Computer: NATIVE date input so the date can be typed (lang -> correct VI/EN format) -->
    <label v-if="!isTouch" for="date-filter" class="sr-only">{{ dateLabel }}</label>
    <input v-if="!isTouch" id="date-filter" type="date" v-model="selectedDate" class="league-select" :lang="dateLang" />
    <!-- Phone/touch: self-formatted VI/EN label, with a transparent native input on top to open the calendar -->
    <span v-else class="league-select date-pick" @click="openDatePicker">
      <span class="date-pick-text">{{ dateLabel }}</span>
      <label for="date-filter-touch" class="sr-only">{{ dateLabel }}</label>
      <input id="date-filter-touch" ref="dateInput" type="date" v-model="selectedDate" class="date-pick-native" :aria-label="dateLabel" />
    </span>
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

<style scoped>
/* Date picker: text label (self-formatted VI/EN) + transparent native input layered on top to open the calendar */
.date-pick { position: relative; display: inline-flex; align-items: center; white-space: nowrap; }
.date-pick-native {
  position: absolute; inset: 0; width: 100%; height: 100%;
  opacity: 0; border: 0; margin: 0; padding: 0; cursor: pointer;
}
</style>
