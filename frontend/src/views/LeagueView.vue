<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../services/api'
import { imgFallback } from '../utils/format'
import { t } from '../i18n'

const route = useRoute()
const router = useRouter()
const raw = ref(null)
const scorers = ref([])
const loading = ref(true)
const tab = ref('standings') // 'standings' | 'scorers'

// standings = mảng các "bảng" (giải thường: 1 bảng; World Cup: 8 bảng A–H).
const groups = computed(() => raw.value?.league?.standings || [])
const leagueName = computed(() => raw.value?.league?.name || t('league_default'))

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

onMounted(() => loadLeague(route.params.id))
// Đổi giải mà không remount -> watch để tải lại.
watch(() => route.params.id, (id) => { if (id) loadLeague(id) })

function goPlayer(id) {
  if (id) router.push({ name: 'player', params: { id } })
}
</script>

<template>
  <router-link to="/" class="back">{{ $t('backHome') }}</router-link>
  <h1 class="page-title">{{ leagueName }}</h1>

  <div class="tabs">
    <button class="tab" :class="{ active: tab === 'standings' }" @click="tab = 'standings'">{{ $t('tab_standings') }}</button>
    <button class="tab" :class="{ active: tab === 'scorers' }" @click="tab = 'scorers'">{{ $t('tab_scorers') }}</button>
  </div>

  <div v-if="loading" class="skeleton" style="height:200px"></div>

  <!-- Bảng xếp hạng (1 bảng cho giải thường, nhiều bảng cho World Cup) -->
  <div v-else-if="tab === 'standings'">
    <div v-if="groups.length === 0" class="center">{{ $t('noStandings') }}</div>
    <template v-else>
      <div v-for="(g, gi) in groups" :key="gi" class="group-block">
        <h3 v-if="g[0] && g[0].group" class="group-name">{{ g[0].group }}</h3>
        <div class="table-wrap">
          <table class="standings">
            <thead>
              <tr><th>#</th><th class="team-cell">{{ $t('th_team') }}</th><th>{{ $t('th_played') }}</th><th>{{ $t('th_w') }}</th><th>{{ $t('th_d') }}</th><th>{{ $t('th_l') }}</th><th>{{ $t('th_gd') }}</th><th>{{ $t('th_pts') }}</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in g" :key="row.team.id" :class="zone(row, g)">
                <td>{{ row.rank }}</td>
                <td class="team-cell">
                  <router-link :to="{ name: 'team', params: { id: row.team.id } }" class="team-cell">
                    <img :src="row.team.logo" @error="imgFallback" />{{ row.team.name }}
                  </router-link>
                </td>
                <td>{{ row.all.played }}</td>
                <td>{{ row.all.win }}</td>
                <td>{{ row.all.draw }}</td>
                <td>{{ row.all.lose }}</td>
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
          <div class="muted" style="font-size:12px">{{ s.statistics[0].team.name }}</div>
        </span>
        <span style="text-align:right">
          <strong style="font-size:18px">{{ s.statistics[0].goals.total }}</strong>
          <div class="muted" style="font-size:12px">{{ s.statistics[0].goals.assists ?? 0 }} {{ $t('assistsShort') }}</div>
        </span>
      </div>
    </div>
  </div>
</template>
