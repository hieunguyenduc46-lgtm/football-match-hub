<script setup>
import { ref, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'
import { imgFallback } from '../utils/format'
import { state, setLocale } from '../i18n'
import { teamName } from '../utils/countryNames'

const router = useRouter()

function toggleLang() {
  setLocale(state.locale === 'vi' ? 'en' : 'vi')
}

// ---- Tìm kiếm ----
const q = ref('')
const results = ref({ teams: [], players: [] })
const open = ref(false)
const searching = ref(false)
let timer = null
let reqSeq = 0   // chống "race": chỉ nhận kết quả của lần gọi MỚI nhất

// Truy vấn đủ dài để hiện ô gợi ý (ít nhất luôn có hành động "Tìm trận").
const canSearch = computed(() => q.value.trim().length >= 2)

// Bỏ dấu + thường hoá để so khớp tên ("Mbappé" ~ "mbappe").
function norm(s) {
  return (s || '').toLowerCase().normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]/g, '')
}

// Gọi API tìm kiếm, trả kết quả; tự bỏ qua nếu đã có lần gọi mới hơn.
async function fetchSearch(term) {
  const seq = ++reqSeq
  searching.value = true
  try {
    const { data } = await api.get('/search', { params: { q: term } })
    if (seq !== reqSeq) return null            // có lần gõ mới hơn -> bỏ kết quả cũ
    const r = { teams: data.teams || [], players: data.players || [] }
    results.value = r
    return r
  } catch (e) {
    if (seq === reqSeq) results.value = { teams: [], players: [] }
    return null
  } finally {
    if (seq === reqSeq) searching.value = false
  }
}

watch(q, (val) => {
  clearTimeout(timer)
  const term = val.trim()
  if (term.length < 2) {
    results.value = { teams: [], players: [] }
    open.value = false
    searching.value = false
    return
  }
  open.value = true // luôn hiện dropdown để thấy nút "Tìm trận"
  if (term.length < 3) {
    results.value = { teams: [], players: [] }
    return
  }
  // debounce 250ms + tối thiểu 3 ký tự để đỡ gọi API khi đang gõ (tiết kiệm quota).
  timer = setTimeout(() => fetchSearch(term), 250)
})

function hasResults() {
  return results.value.teams.length > 0 || results.value.players.length > 0
}
function goTeam(id) { reset(); router.push({ name: 'team', params: { id } }) }
function goPlayer(id) { reset(); router.push({ name: 'player', params: { id } }) }
// Tìm trận đấu: gõ "A vs B" hoặc 1 đội -> trang /matches.
function goMatches() {
  const term = q.value.trim()
  if (term.length < 2) return
  reset()
  router.push({ name: 'matches', query: { q: term } })
}

// Enter: ƯU TIÊN mở đúng thực thể (cầu thủ/đội), chỉ tìm TRẬN khi gõ kiểu "A vs B"
// hoặc không có kết quả nào. Nếu kết quả chưa kịp về (debounce) thì gọi NGAY rồi mới quyết.
async function onEnter() {
  const term = q.value.trim()
  if (term.length < 2) return
  // "A vs B" / "A v B" -> tìm trận đối đầu.
  if (/\s+vs?\s+/i.test(term)) return goMatches()
  clearTimeout(timer)
  let r = results.value
  // Chưa có kết quả khớp từ khoá hiện tại -> gọi ngay, đừng đợi.
  if (term.length >= 3 && !hasResults()) {
    r = (await fetchSearch(term)) || results.value
  }
  const nt = norm(term)
  const exactP = r.players.find(p => norm(p.name) === nt)
  if (exactP) return goPlayer(exactP.id)
  const exactT = r.teams.find(t => norm(t.name) === nt)
  if (exactT) return goTeam(exactT.id)
  if (r.players.length) return goPlayer(r.players[0].id)
  if (r.teams.length) return goTeam(r.teams[0].id)
  goMatches()   // không có thực thể nào -> thử như tìm trận
}

function reset() { open.value = false; q.value = ''; searching.value = false }
function onBlur() { setTimeout(() => { open.value = false }, 200) } // chờ click item

// ---- Dark / Light ----
const theme = ref(document.documentElement.getAttribute('data-theme') || 'dark')
function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  document.documentElement.setAttribute('data-theme', theme.value)
  try { localStorage.setItem('theme', theme.value) } catch (e) { /* bỏ qua */ }
}
</script>

<template>
  <header class="app-header">
    <div class="app-header__inner">
      <router-link to="/" class="logo">Football <span>Match Hub</span></router-link>

      <div class="search-wrap">
        <input
          class="search"
          type="search"
          v-model="q"
          :placeholder="$t('search_ph')"
          @focus="open = canSearch"
          @blur="onBlur"
          @keyup.enter="onEnter"
        />
        <div v-if="open" class="search-dd">
          <!-- Tìm trận đấu: luôn ở đầu khi có từ khoá -->
          <!-- Dùng pointerdown (chạy cả chuột lẫn cảm ứng) để bấm được trên điện thoại,
               tránh việc input mất focus -> dropdown đóng trước khi 'click' kịp chạy. -->
          <div v-if="canSearch" class="dd-item dd-action" @pointerdown.prevent="goMatches">
            ⚽ {{ $t('findMatches') }}: <strong style="margin-left:4px">{{ q.trim() }}</strong>
          </div>
          <template v-if="results.teams.length">
            <div class="dd-label">{{ $t('teamsLabel') }}</div>
            <div v-for="t in results.teams" :key="'t' + t.id" class="dd-item" @pointerdown.prevent="goTeam(t.id)">
              <img loading="lazy" :src="t.logo" @error="imgFallback" /> {{ teamName(t.name) }}
            </div>
          </template>
          <template v-if="results.players.length">
            <div class="dd-label">{{ $t('playersLabel') }}</div>
            <div v-for="p in results.players" :key="'p' + p.id" class="dd-item" @pointerdown.prevent="goPlayer(p.id)">
              <img loading="lazy" :src="p.photo" @error="imgFallback" class="round" /> {{ p.name }}
            </div>
          </template>
          <!-- Trạng thái: đang tìm / không có gợi ý -->
          <div v-if="searching" class="dd-hint">{{ $t('searching') }}</div>
          <div v-else-if="q.trim().length >= 3 && !hasResults()" class="dd-hint">{{ $t('noResults') }}</div>
        </div>
      </div>

      <button class="theme-btn" @click="toggleLang" :title="state.locale === 'vi' ? 'English' : 'Tiếng Việt'" style="font-size:12px;font-weight:800">
        {{ state.locale === 'vi' ? 'EN' : 'VI' }}
      </button>

      <router-link to="/compare" class="theme-btn" title="So sánh cầu thủ" style="display:flex;align-items:center;justify-content:center;text-decoration:none">
        ⇄
      </router-link>

      <router-link to="/favorites" class="theme-btn" title="Đang theo dõi" style="display:flex;align-items:center;justify-content:center;text-decoration:none">
        ♥
      </router-link>

      <button class="theme-btn" @click="toggleTheme" :title="theme === 'dark' ? 'Chuyển sáng' : 'Chuyển tối'">
        {{ theme === 'dark' ? '☀️' : '🌙' }}
      </button>
    </div>
  </header>
</template>

<style scoped>
.dd-action {
  font-size: 13px;
  color: var(--accent);
  border-bottom: 1px solid var(--border);
  cursor: pointer;
}
.dd-hint {
  padding: 8px 12px;
  font-size: 12px;
  color: var(--text-dim);
}
</style>
