<script setup>
import { ref, computed, onMounted, onActivated, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../services/api'
import { imgFallback, matchDay, matchTime } from '../utils/format'
import { setTitle } from '../utils/title'
import FavButton from '../components/FavButton.vue'
import TeamInsights from '../components/TeamInsights.vue'
import { teamName } from '../utils/countryNames'

const route = useRoute()
const router = useRouter()
// teamId must be REACTIVE: when the team changes (:id changes) the dependent computeds update too.
const teamId = computed(() => Number(route.params.id))
const team = ref(null)
const recent = ref([])
const upcoming = ref([])
const loading = ref(true)
const insights = ref(null)          // season stats + injuries (lazy loaded)
const insightsLoading = ref(false)

// Result of one match from the viewed team's perspective: W / D / L.
function resultFor(m) {
  const gh = m.goals.home, ga = m.goals.away
  if (gh === ga) return 'D'
  const homeWon = gh > ga
  const isHome = m.teams.home.id === teamId.value
  return (homeWon && isHome) || (!homeWon && !isHome) ? 'W' : 'L'
}
// recent = newest->oldest; reverse so form shows OLDEST->NEWEST (latest match on the right).
const form = computed(() => recent.value.map(resultFor).reverse())

let loadSeq = 0
async function loadTeam(id) {
  const seq = ++loadSeq
  loading.value = true
  team.value = null
  recent.value = []
  upcoming.value = []
  insights.value = null
  insightsLoading.value = true
  const [tRes, fRes, uRes] = await Promise.allSettled([
    api.get(`/teams/${id}`),
    api.get(`/teams/${id}/fixtures`),
    api.get(`/teams/${id}/upcoming`),
  ])
  if (seq !== loadSeq) return                    // already switched to another team
  if (tRes.status === 'fulfilled') team.value = tRes.value.data.response?.[0] || null
  setTitle(team.value ? teamName(team.value.team.name) : null)   // tab title = team name
  if (fRes.status === 'fulfilled') recent.value = fRes.value.data.response || []
  if (uRes.status === 'fulfilled') upcoming.value = uRes.value.data.response || []
  loading.value = false
  // Season stats + injuries: loaded later, doesn't block the page (backend looks up leagues + makes extra calls).
  try {
    const ins = await api.get(`/teams/${id}/insights`, { timeout: 60000 })
    if (seq === loadSeq) insights.value = ins.data
  } catch (e) { /* ignore */ }
  finally { if (seq === loadSeq) insightsLoading.value = false }
}

// keep-alive: the component is cached, NOT remounted. Only reload when this really is the page being
// viewed (route.name === 'team') AND it's a different team from the one loaded -> avoids loading by mistake while cached,
// and avoids reloading (losing scroll position) when going back to the same team.
let loadedId = null
function syncTeam() {
  if (route.name !== 'team') return
  const id = Number(route.params.id)
  if (!id || id === loadedId) return
  loadedId = id
  loadTeam(id)
}
onMounted(syncTeam)
watch(() => route.params.id, syncTeam)
onActivated(() => { if (route.name === 'team') setTitle(team.value ? teamName(team.value.team.name) : null) })

// Penalty shootout score (if any) -> shown next to the score so you know who won a draw.
function penStr(m) {
  const p = m?.score?.penalty
  return (p && p.home != null && p.away != null) ? `${p.home}-${p.away}` : null
}

function goMatch(id) { router.push({ name: 'match', params: { id } }) }
</script>

<template>
  <a href="#" class="back" @click.prevent="$router.back()">{{ $t('backHome') }}</a>

  <div v-if="loading" class="skeleton" style="height:100px"></div>
  <div v-else-if="!team" class="center">{{ $t('teamNoData') }}</div>

  <div v-else>
    <div class="player-hero">
      <img loading="lazy" :src="team.team.logo" class="photo" style="border-radius:12px" @error="imgFallback" />
      <div>
        <h1>{{ teamName(team.team.name) }}</h1>
        <div class="meta">{{ team.venue?.name }} · {{ team.venue?.capacity?.toLocaleString() }} {{ $t('seats') }} · {{ $t('since') }} {{ team.team.founded }}</div>
        <div style="margin-top:8px">
          <FavButton type="team" :item="{ id: team.team.id, name: team.team.name, logo: team.team.logo }" />
        </div>
      </div>
    </div>

    <!-- Form -->
    <div v-if="form.length" class="form-row">
      <span class="muted" style="font-size:13px">{{ $t('form') }}</span>
      <span v-for="(r, i) in form" :key="i" class="form-b" :class="'f-' + r">{{ r }}</span>
    </div>

    <!-- Season stats + injuries (lazy loaded) -->
    <TeamInsights
      :statistics="insights?.statistics || {}"
      :injuries="insights?.injuries || []"
      :loading="insightsLoading"
    />

    <!-- Upcoming matches -->
    <template v-if="upcoming.length">
      <h2 class="page-title" style="font-size:16px">{{ $t('upcomingMatches') }}</h2>
      <div
        v-for="m in upcoming"
        :key="m.fixture.id"
        class="match-card"
        style="grid-template-columns:54px 1fr auto"
        @click="goMatch(m.fixture.id)"
      >
        <span class="muted" style="font-size:12px">{{ matchDay(m.fixture.date) }}</span>
        <span style="font-size:14px">{{ teamName(m.teams.home.name) }} v {{ teamName(m.teams.away.name) }}</span>
        <span class="muted" style="font-size:13px">{{ matchTime(m.fixture.date) }}</span>
      </div>
    </template>

    <!-- Recent matches -->
    <template v-if="recent.length">
      <h2 class="page-title" style="font-size:16px">{{ $t('recentMatches') }}</h2>
      <div
        v-for="m in recent"
        :key="m.fixture.id"
        class="match-card"
        style="grid-template-columns:54px 1fr auto"
        @click="goMatch(m.fixture.id)"
      >
        <span class="muted" style="font-size:12px">{{ matchDay(m.fixture.date) }}</span>
        <span style="font-size:14px">{{ teamName(m.teams.home.name) }} v {{ teamName(m.teams.away.name) }}</span>
        <strong>{{ m.goals.home }}-{{ m.goals.away }}<span v-if="penStr(m)" style="font-size:11px;font-weight:600;color:var(--text-dim);margin-left:3px">(p {{ penStr(m) }})</span></strong>
      </div>
    </template>

    <!-- Squad -->
    <h2 class="page-title">{{ $t('squad') }}</h2>
    <router-link
      v-for="p in team.squad"
      :key="p.id"
      :to="{ name: 'player', params: { id: p.id } }"
      class="match-card"
      style="grid-template-columns:44px 1fr auto"
    >
      <img loading="lazy" :src="p.photo" @error="imgFallback" style="width:36px;height:36px;border-radius:50%;object-fit:cover" />
      <span style="font-weight:600">{{ p.name }}</span>
      <span class="muted">#{{ p.number }} · {{ p.pos }}</span>
    </router-link>
  </div>
</template>
