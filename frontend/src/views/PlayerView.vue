<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '../services/api'
import { imgFallback } from '../utils/format'
import FavButton from '../components/FavButton.vue'

const route = useRoute()
const data = ref(null)
const loading = ref(true)
const career = ref(null)        // tổng bàn sự nghiệp (tải riêng, có thể chậm)
const motm = ref(null)          // số lần hay nhất trận mùa này (tải riêng, quét fixtures)

const player = computed(() => data.value?.player || null)

// ===== Tách thống kê CLB vs ĐTQG, KHÔNG gộp — hiển thị theo TỪNG GIẢI =====
// API-Football trả `statistics` = mảng, mỗi ĐỘI + mỗi GIẢI một phần tử
// (vd Al-Nassr / Saudi Pro League, Al-Nassr / AFC Champions League Two,
//  Portugal / Nations League...). Ta giữ nguyên từng phần tử = từng giải.

// Bỏ dấu, thường hoá để so tên đội với quốc tịch ("Pháp"/"France"...).
function norm(s) {
  return (s || '').toLowerCase().normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').replace(/[^a-z]/g, '')
}

// Giải cấp ĐỘI TUYỂN (để bắt cả khi tên đội != quốc tịch, vd "Korea Republic").
// LƯU Ý: dùng \beuro(?!pa) để KHÔNG dính "Europa League" (cúp CLB).
const INTL_LEAGUE = /world cup|nations league|friendl|\beuro(?!pa)|copa am|africa cup|afcon|asian cup|gold cup|olympic|qualification|qualifying|confederations cup/i

// Giải cấp CLB (cúp châu lục + cúp QG) — KHÔNG bao giờ là ĐTQG, dù tên có
// "champions"/"concacaf"... (vd "CONCACAF Champions League", "UEFA Europa League",
// "CONMEBOL Libertadores" đều là CLB). Đây là nguồn gây nhầm lẫn chính.
const CLUB_LEAGUE = /club world cup|champions league|champions cup|europa|conference league|libertadores|sudamericana|recopa|leagues cup|super cup|intercontinental|fa cup|copa del rey|coppa|dfb|carabao|community shield|supercopa|supercoppa/i

function isNational(s, nationality) {
  const team = s.team?.name || ''
  const league = s.league?.name || ''
  // Cúp CLB (gồm "FIFA Club World Cup", "Club Friendlies", cúp châu lục CLB...) -> KHÔNG phải ĐTQG.
  if (/club/i.test(league) || CLUB_LEAGUE.test(league)) return false
  // Tin cậy nhất: tên đội trùng quốc tịch cầu thủ ("France", "Argentina").
  if (nationality && norm(team) === norm(nationality)) return true
  // Dự phòng: tên giải thuộc nhóm đội tuyển (bắt cả khi tên đội khác quốc tịch).
  return INTL_LEAGUE.test(league)
}

// Giao hữu (không tính vào thống kê "chính thức").
function isFriendly(s) {
  return /friendl/i.test(s.league?.name || '')
}

// Chuẩn hoá % chuyền chính xác từ field `passes.accuracy`.
// API-Football: ở endpoint /players (gộp cả mùa) field này đôi khi là phần trăm
// (<=100), đôi khi là TỔNG CỘNG phần trăm các trận (>100) -> chia cho số trận.
function passPct(acc, apps) {
  if (acc == null || acc === '') return null
  const n = parseFloat(acc)
  if (isNaN(n)) return null
  return n <= 100 ? Math.round(n) : Math.round(n / Math.max(apps, 1))
}

// Chuẩn hoá 1 phần tử statistics -> 1 dòng giải đấu.
function mapEntry(s) {
  const r = parseFloat(s.games?.rating)
  const apps = s.games?.appearences || 0
  return {
    key: `${s.team?.id || ''}-${s.league?.id || s.league?.name || ''}`,
    league: s.league?.name || '—',
    logo: s.league?.logo,
    team: s.team?.name || '',
    goals: s.goals?.total || 0,
    assists: s.goals?.assists || 0,
    apps,
    minutes: s.games?.minutes || 0,
    shots: s.shots?.total || 0,
    passAcc: passPct(s.passes?.accuracy, apps),
    yellow: s.cards?.yellow || 0,
    red: s.cards?.red || 0,
    rating: r ? +r.toFixed(1) : null,
    position: s.games?.position,
  }
}

// Cộng dồn các dòng -> dòng TỔNG (rating: trung bình có trọng số theo số trận).
function totalsOf(rows) {
  const sum = (k) => rows.reduce((t, r) => t + (r[k] || 0), 0)
  let rW = 0, rA = 0   // rating: trung bình có trọng số theo số trận
  let pW = 0, pA = 0   // pass%: trung bình có trọng số theo số trận
  for (const r of rows) {
    if (r.rating && r.apps) { rW += r.rating * r.apps; rA += r.apps }
    if (r.passAcc != null && r.apps) { pW += r.passAcc * r.apps; pA += r.apps }
  }
  return {
    goals: sum('goals'), assists: sum('assists'), apps: sum('apps'),
    minutes: sum('minutes'), shots: sum('shots'),
    yellow: sum('yellow'), red: sum('red'),
    passAcc: pA ? Math.round(pW / pA) : null,
    rating: rA ? +(rW / rA).toFixed(1) : null,
  }
}

const split = computed(() => {
  const arr = data.value?.statistics || []
  const nat = player.value?.nationality
  const club = [], national = []
  for (const s of arr) {
    if (isFriendly(s)) continue            // bỏ trận giao hữu khỏi mọi bảng
    ;(isNational(s, nat) ? national : club).push(mapEntry(s))
  }
  // Sắp xếp giải nhiều trận lên trước cho dễ nhìn.
  const byApps = (a, b) => b.apps - a.apps
  return { club: club.sort(byApps), national: national.sort(byApps) }
})

const clubRows = computed(() => split.value.club)
const nationalRows = computed(() => split.value.national)
const clubTotal = computed(() => totalsOf(clubRows.value))
const nationalTotal = computed(() => totalsOf(nationalRows.value))

// Tên CLB hiển thị ở tiêu đề: lấy đội đá nhiều trận nhất.
const clubTeamName = computed(() => {
  const rows = clubRows.value
  if (!rows.length) return ''
  return rows.reduce((b, r) => (r.apps > b.apps ? r : b), rows[0]).team
})

function hideImg(e) { e.target.style.display = 'none' }

// Thêm đơn vị cho chiều cao / cân nặng nếu API trả về số trần (vd "187" -> "187 cm").
const heightStr = computed(() => {
  const h = player.value?.height
  return h ? (/[a-z]/i.test(h) ? h : `${h} cm`) : ''
})
const weightStr = computed(() => {
  const w = player.value?.weight
  return w ? (/[a-z]/i.test(w) ? w : `${w} kg`) : ''
})

// Mỗi lần đổi cầu thủ tăng seq -> bỏ kết quả của request cũ về muộn (chống "race"
// khi bấm liên tiếp nhiều cầu thủ, vì career/motm tải chậm).
let loadSeq = 0

async function loadPlayer(id) {
  const seq = ++loadSeq
  // Reset trạng thái để không thấy dữ liệu cầu thủ cũ lúc đang tải cầu thủ mới.
  loading.value = true
  data.value = null
  career.value = null
  motm.value = null
  try {
    const res = await api.get(`/players/${id}`)
    if (seq !== loadSeq) return                  // đã chuyển sang cầu thủ khác
    data.value = res.data.response?.[0] || null
  } finally {
    if (seq === loadSeq) loading.value = false
  }
  // Tổng bàn sự nghiệp: gọi sau, không chặn trang (backend phải quét nhiều mùa).
  try {
    const c = await api.get(`/players/${id}/career`)
    if (seq === loadSeq) career.value = c.data
  } catch (e) { /* bỏ qua */ }
  // POTM mùa này: backend quét fixtures -> chậm, tải sau cùng, không chặn trang.
  try {
    const m = await api.get(`/players/${id}/motm`)
    if (seq === loadSeq) motm.value = m.data
  } catch (e) { /* bỏ qua */ }
}

onMounted(() => loadPlayer(route.params.id))

// QUAN TRỌNG: khi chuyển từ cầu thủ này sang cầu thủ khác, Vue Router TÁI SỬ DỤNG
// component (chỉ đổi :id), nên onMounted KHÔNG chạy lại. Phải watch id để tải lại.
watch(() => route.params.id, (id) => { if (id) loadPlayer(id) })
</script>

<template>
  <router-link to="/" class="back">{{ $t('backHome') }}</router-link>

  <div v-if="loading" class="skeleton" style="height:120px"></div>
  <div v-else-if="!player" class="center">{{ $t('playerNoData') }}</div>

  <div v-else>
    <!-- ẢNH MẶT CẦU THỦ -->
    <div class="player-hero">
      <img :src="player.photo" class="photo" @error="imgFallback" />
      <div>
        <h1>{{ player.name }}</h1>
        <div class="meta">
          {{ player.age }} {{ $t('years') }} · {{ player.nationality }}
          <span v-if="clubTeamName"> · {{ clubTeamName }}</span>
        </div>
        <div class="meta" v-if="heightStr || weightStr">{{ heightStr }} · {{ weightStr }}</div>
        <div style="margin-top:8px">
          <FavButton type="player" :item="{ id: player.id, name: player.name, photo: player.photo }" />
        </div>
      </div>
    </div>

    <!-- TỔNG BÀN THẮNG SỰ NGHIỆP (chính thức, mọi CLB + ĐTQG) -->
    <div v-if="career && career.goals" class="career-card">
      <div class="career-num">{{ career.goals }}</div>
      <div class="career-text">
        <div class="career-title">{{ $t('careerGoals') }}</div>
        <div class="career-sub" v-if="career.source === 'official'">{{ $t('careerSubOfficial') }}</div>
        <div class="career-sub" v-else>{{ $t('careerSub') }} · {{ career.seasons }} {{ $t('seasonsWord') }}</div>
      </div>
    </div>

    <!-- CẦU THỦ HAY NHẤT TRẬN (POTM) — tự tính, mùa đang xem -->
    <div v-if="motm && motm.scanned > 0" class="career-card potm-card">
      <div class="career-num">{{ motm.motm }}</div>
      <div class="career-text">
        <div class="career-title">{{ $t('potmTitle') }}</div>
        <div class="career-sub">{{ $t('potmSub') }}</div>
      </div>
    </div>

    <!-- THỐNG KÊ CẤP CLB — tách theo từng giải -->
    <div v-if="clubRows.length">
      <h3 class="stat-group">{{ clubTeamName }}</h3>
      <div class="comp-wrap">
        <table class="comp-table">
          <thead>
            <tr>
              <th class="left">{{ $t('competition') }}</th>
              <th>{{ $t('col_apps') }}</th>
              <th>{{ $t('col_goals') }}</th>
              <th>{{ $t('col_assists') }}</th>
              <th>{{ $t('col_shots') }}</th>
              <th>{{ $t('col_pass') }}</th>
              <th>{{ $t('col_min') }}</th>
              <th>{{ $t('col_yellow') }}</th>
              <th>{{ $t('col_red') }}</th>
              <th>{{ $t('col_rating') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in clubRows" :key="r.key">
              <td class="left comp-name">
                <img v-if="r.logo" :src="r.logo" class="comp-logo" @error="hideImg" />
                <span>{{ r.league }}</span>
              </td>
              <td>{{ r.apps }}</td>
              <td>{{ r.goals }}</td>
              <td>{{ r.assists }}</td>
              <td>{{ r.shots }}</td>
              <td>{{ r.passAcc != null ? r.passAcc + '%' : '—' }}</td>
              <td>{{ r.minutes }}</td>
              <td>{{ r.yellow }}</td>
              <td>{{ r.red }}</td>
              <td>{{ r.rating != null ? r.rating.toFixed(1) : '—' }}</td>
            </tr>
          </tbody>
          <tfoot v-if="clubRows.length > 1">
            <tr class="total-row">
              <td class="left">{{ $t('totalRow') }}</td>
              <td>{{ clubTotal.apps }}</td>
              <td>{{ clubTotal.goals }}</td>
              <td>{{ clubTotal.assists }}</td>
              <td>{{ clubTotal.shots }}</td>
              <td>{{ clubTotal.passAcc != null ? clubTotal.passAcc + '%' : '—' }}</td>
              <td>{{ clubTotal.minutes }}</td>
              <td>{{ clubTotal.yellow }}</td>
              <td>{{ clubTotal.red }}</td>
              <td>{{ clubTotal.rating != null ? clubTotal.rating.toFixed(1) : '—' }}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>

    <!-- THỐNG KÊ CẤP ĐỘI TUYỂN QUỐC GIA — tách theo từng giải (chỉ hiện khi có) -->
    <div v-if="nationalRows.length">
      <h3 class="stat-group">{{ player.nationality }} <span class="natl-tag">{{ $t('nationalTeam') }}</span></h3>
      <div class="comp-wrap">
        <table class="comp-table">
          <thead>
            <tr>
              <th class="left">{{ $t('competition') }}</th>
              <th>{{ $t('col_apps') }}</th>
              <th>{{ $t('col_goals') }}</th>
              <th>{{ $t('col_assists') }}</th>
              <th>{{ $t('col_shots') }}</th>
              <th>{{ $t('col_pass') }}</th>
              <th>{{ $t('col_min') }}</th>
              <th>{{ $t('col_yellow') }}</th>
              <th>{{ $t('col_red') }}</th>
              <th>{{ $t('col_rating') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in nationalRows" :key="r.key">
              <td class="left comp-name">
                <img v-if="r.logo" :src="r.logo" class="comp-logo" @error="hideImg" />
                <span>{{ r.league }}</span>
              </td>
              <td>{{ r.apps }}</td>
              <td>{{ r.goals }}</td>
              <td>{{ r.assists }}</td>
              <td>{{ r.shots }}</td>
              <td>{{ r.passAcc != null ? r.passAcc + '%' : '—' }}</td>
              <td>{{ r.minutes }}</td>
              <td>{{ r.yellow }}</td>
              <td>{{ r.red }}</td>
              <td>{{ r.rating != null ? r.rating.toFixed(1) : '—' }}</td>
            </tr>
          </tbody>
          <tfoot v-if="nationalRows.length > 1">
            <tr class="total-row">
              <td class="left">{{ $t('totalRow') }}</td>
              <td>{{ nationalTotal.apps }}</td>
              <td>{{ nationalTotal.goals }}</td>
              <td>{{ nationalTotal.assists }}</td>
              <td>{{ nationalTotal.shots }}</td>
              <td>{{ nationalTotal.passAcc != null ? nationalTotal.passAcc + '%' : '—' }}</td>
              <td>{{ nationalTotal.minutes }}</td>
              <td>{{ nationalTotal.yellow }}</td>
              <td>{{ nationalTotal.red }}</td>
              <td>{{ nationalTotal.rating != null ? nationalTotal.rating.toFixed(1) : '—' }}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stat-group {
  margin: 18px 0 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-dim);
  display: flex;
  align-items: center;
  gap: 8px;
}
.natl-tag {
  font-size: 11px;
  font-weight: 600;
  color: var(--accent-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 1px 6px;
}

/* Bảng thống kê theo giải */
.comp-wrap {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
}
.comp-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  min-width: 560px;
}
.comp-table th,
.comp-table td {
  padding: 10px 8px;
  text-align: center;
  white-space: nowrap;
}
.comp-table th {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: .3px;
  border-bottom: 1px solid var(--border);
}
.comp-table td { border-bottom: 1px solid var(--border); }
.comp-table tbody tr:last-child td { border-bottom: none; }
.comp-table .left { text-align: left; }
.comp-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}
.comp-logo {
  width: 18px;
  height: 18px;
  object-fit: contain;
  flex: none;
}
.total-row td {
  font-weight: 800;
  border-top: 2px solid var(--border);
  background: var(--bg, transparent);
}

.career-card {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 16px 0 4px;
  padding: 14px 18px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--surface);
}
.career-num {
  font-size: 34px;
  font-weight: 800;
  color: var(--accent);
  line-height: 1;
}
.career-title { font-weight: 700; }
.career-sub { font-size: 12px; color: var(--text-dim); margin-top: 2px; }
.potm-card { margin-top: 8px; }
.potm-card .career-num { color: var(--accent-2); }
</style>
