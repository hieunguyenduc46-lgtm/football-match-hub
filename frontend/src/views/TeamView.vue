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
// teamId phải REACTIVE: khi đổi đội (đổi :id) thì các computed phụ thuộc cũng cập nhật.
const teamId = computed(() => Number(route.params.id))
const team = ref(null)
const recent = ref([])
const upcoming = ref([])
const loading = ref(true)
const insights = ref(null)          // thống kê mùa + chấn thương (tải lười)
const insightsLoading = ref(false)

// Kết quả 1 trận xét theo đội đang xem: W / D / L.
function resultFor(m) {
  const gh = m.goals.home, ga = m.goals.away
  if (gh === ga) return 'D'
  const homeWon = gh > ga
  const isHome = m.teams.home.id === teamId.value
  return (homeWon && isHome) || (!homeWon && !isHome) ? 'W' : 'L'
}
const form = computed(() => recent.value.map(resultFor))

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
  if (seq !== loadSeq) return                    // đã chuyển sang đội khác
  if (tRes.status === 'fulfilled') team.value = tRes.value.data.response?.[0] || null
  setTitle(team.value ? teamName(team.value.team.name) : null)   // tiêu đề tab = tên đội
  if (fRes.status === 'fulfilled') recent.value = fRes.value.data.response || []
  if (uRes.status === 'fulfilled') upcoming.value = uRes.value.data.response || []
  loading.value = false
  // Thống kê mùa + chấn thương: tải sau, không chặn trang (backend dò giải + gọi thêm).
  try {
    const ins = await api.get(`/teams/${id}/insights`, { timeout: 60000 })
    if (seq === loadSeq) insights.value = ins.data
  } catch (e) { /* bỏ qua */ }
  finally { if (seq === loadSeq) insightsLoading.value = false }
}

// keep-alive: component bị cache, KHÔNG remount. Chỉ tải lại khi đây đúng là trang đang
// xem (route.name === 'team') VÀ là đội khác đội đã tải -> tránh tải nhầm khi bị cache,
// và tránh tải lại (mất vị trí cuộn) khi back về đúng đội cũ.
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

// Tỉ số luân lưu (nếu có) -> hiện thêm cạnh tỉ số để biết đội nào thắng khi hoà.
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

    <!-- Phong độ -->
    <div v-if="form.length" class="form-row">
      <span class="muted" style="font-size:13px">{{ $t('form') }}</span>
      <span v-for="(r, i) in form" :key="i" class="form-b" :class="'f-' + r">{{ r }}</span>
    </div>

    <!-- Thống kê mùa + chấn thương (tải lười) -->
    <TeamInsights
      :statistics="insights?.statistics || {}"
      :injuries="insights?.injuries || []"
      :loading="insightsLoading"
    />

    <!-- Trận sắp đá -->
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

    <!-- Trận gần đây -->
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

    <!-- Đội hình -->
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
