<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ensureIndex, searchIndex, resolveCountry } from '../utils/searchIndex'
import { state, t } from '../i18n'
import { imgFallback } from '../utils/format'
import { teamName } from '../utils/countryNames'
import { leagueName } from '../utils/leagueNames'

const router = useRouter()
const q = ref('')
const open = ref(false)
const ready = ref(false)
const results = ref({ leagues: [], countries: [] })
const active = ref(-1) // chỉ số trong danh sách phẳng (quốc gia trước, giải sau)
const boxRef = ref(null)

// Tải chỉ mục 1 lần khi gắn component (không chặn gõ — gõ trước khi tải xong vẫn ổn).
onMounted(async () => { ready.value = await ensureIndex() })

// Debounce nhẹ 110ms: tránh tính/lọc lại liên tục khi gõ nhanh (dù lọc client rất nhanh).
let timer = null
function onInput() {
  clearTimeout(timer)
  timer = setTimeout(() => {
    results.value = searchIndex(q.value)
    active.value = -1
    open.value = true
  }, 110)
}

// Gộp thành 1 danh sách phẳng để điều hướng bằng phím mũi tên.
const flat = computed(() => [
  ...results.value.countries.map((c) => ({ type: 'country', data: c })),
  ...results.value.leagues.map((l) => ({ type: 'league', data: l })),
])
const hasResults = computed(() => flat.value.length > 0)
const nc = computed(() => results.value.countries.length)

// ----- Tìm trận "A vs B" -----
// Cùng bộ ngăn cách như backend (_VS_RE): vs / versus / v / x / - / – / "đấu với" / "gặp".
const VS_RE = /\s+(?:vs|versus|v|x|-|–|đấu với|gặp)\s+/i
// Nếu gõ đúng dạng "A <sep> B" (mỗi vế không rỗng) -> trả [A, B], ngược lại null.
const vsParts = computed(() => {
  const parts = q.value.split(VS_RE)
  if (parts.length === 2 && parts[0].trim() && parts[1].trim()) {
    return [parts[0].trim(), parts[1].trim()]
  }
  return null
})
// Tên 1 vế: ưu tiên tên đội tuyển đã dịch (EN/VI), không khớp thì viết hoa chữ cái đầu.
function sideLabel(term) {
  const c = resolveCountry(term)
  if (c) return state.locale === 'en' ? c.name : c.vi || c.name
  return term.replace(/\b\w/g, (ch) => ch.toUpperCase())
}
const matchLabel = computed(() =>
  vsParts.value ? `${sideLabel(vsParts.value[0])} vs ${sideLabel(vsParts.value[1])}` : ''
)
const findMatchLabel = computed(() => t('findMatches'))

// Mở trang đối đầu. Nếu cả 2 vế là đội tuyển -> gửi tên tiếng Anh chuẩn (chắc khớp);
// còn lại gửi nguyên chuỗi để backend tự suy (xử lý được cả CLB lẫn tên tiếng Việt).
function goMatch() {
  if (!vsParts.value) return
  const ca = resolveCountry(vsParts.value[0])
  const cb = resolveCountry(vsParts.value[1])
  const term = ca && cb ? `${ca.name} vs ${cb.name}` : q.value.trim()
  open.value = false
  q.value = ''
  results.value = { leagues: [], countries: [] }
  router.push({ name: 'matches', query: { q: term } })
}

const placeholder = computed(() =>
  state.locale === 'en' ? 'Search leagues, countries, country A vs B…' : 'Tìm giải, quốc gia, ĐTQG A vs B…'
)
const secCountries = computed(() => (state.locale === 'en' ? 'Countries' : 'Quốc gia'))
const secLeagues = computed(() => (state.locale === 'en' ? 'Leagues' : 'Giải đấu'))
const wordLeagues = computed(() => (state.locale === 'en' ? 'leagues' : 'giải'))
const noResults = computed(() => (state.locale === 'en' ? 'No matches' : 'Không có kết quả'))
function countryLabel(c) {
  return state.locale === 'en' ? c.name : c.vi || c.name
}

function go(item) {
  open.value = false
  q.value = ''
  results.value = { leagues: [], countries: [] }
  if (item.type === 'league') router.push({ name: 'league', params: { id: item.data.id } })
  else router.push({ name: 'country', params: { name: item.data.name } })
}

function onKey(e) {
  if (e.key === 'Escape') { open.value = false; return }
  // Gõ "A vs B" rồi Enter (chưa chọn mục nào trong danh sách) -> mở luôn trang đối đầu.
  if (e.key === 'Enter' && vsParts.value && active.value < 0) {
    e.preventDefault(); goMatch(); return
  }
  if (!hasResults.value) return
  if (e.key === 'ArrowDown') {
    e.preventDefault(); open.value = true
    active.value = (active.value + 1) % flat.value.length
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    active.value = (active.value - 1 + flat.value.length) % flat.value.length
  } else if (e.key === 'Enter') {
    e.preventDefault()
    go(flat.value[active.value >= 0 ? active.value : 0])
  }
}

function onFocus() {
  if (q.value) { results.value = searchIndex(q.value); open.value = true }
}

function onClickOutside(e) {
  if (boxRef.value && !boxRef.value.contains(e.target)) open.value = false
}
onMounted(() => document.addEventListener('click', onClickOutside))
onBeforeUnmount(() => { document.removeEventListener('click', onClickOutside); clearTimeout(timer) })
</script>

<template>
  <div class="sbox" ref="boxRef">
    <input
      class="search sbox-input"
      :placeholder="placeholder"
      v-model="q"
      @input="onInput"
      @focus="onFocus"
      @keydown="onKey"
      autocomplete="off"
      spellcheck="false"
    />

    <div class="search-dd" v-if="open && (vsParts || hasResults)">
      <!-- Gợi ý tìm trận đối đầu "A vs B" (đội tuyển: tên đã dịch theo ngôn ngữ). -->
      <div v-if="vsParts" class="dd-item dd-action" @pointerdown.prevent="goMatch">
        ⚽ {{ findMatchLabel }}: <strong style="margin-left:4px">{{ matchLabel }}</strong>
      </div>

      <template v-if="results.countries.length">
        <div class="dd-label">{{ secCountries }}</div>
        <div
          v-for="(c, i) in results.countries"
          :key="'c' + c.name"
          class="dd-item"
          :class="{ active: active === i }"
          @pointerdown.prevent="go({ type: 'country', data: c })"
          @mousemove="active = i"
        >
          <img v-if="c.flag" :src="c.flag" class="round" @error="imgFallback" />
          <span v-else class="sbox-flag">🏳️</span>
          <span class="sbox-name">{{ countryLabel(c) }}</span>
          <span class="sbox-meta">{{ c.count }} {{ wordLeagues }}</span>
        </div>
      </template>

      <template v-if="results.leagues.length">
        <div class="dd-label">{{ secLeagues }}</div>
        <div
          v-for="(l, j) in results.leagues"
          :key="'l' + l.id"
          class="dd-item"
          :class="{ active: active === nc + j }"
          @pointerdown.prevent="go({ type: 'league', data: l })"
          @mousemove="active = nc + j"
        >
          <img :src="l.logo" @error="imgFallback" />
          <span class="sbox-name">{{ leagueName(l.name, l.id) }}</span>
          <span class="sbox-meta">{{ teamName(l.country) }}</span>
        </div>
      </template>
    </div>

    <div class="search-dd" v-else-if="open && q && ready">
      <div class="sbox-empty">{{ noResults }}</div>
    </div>
  </div>
</template>

<style scoped>
.sbox { position: relative; flex: 1 1 200px; min-width: 180px; }
.sbox-input { width: 100%; }
.dd-item.active { background: var(--surface-2); }
.dd-action { font-size: 13px; color: var(--accent); border-bottom: 1px solid var(--border); cursor: pointer; }
.dd-action strong { color: var(--text); }
.sbox-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sbox-meta { color: var(--text-dim); font-size: 12px; flex: 0 0 auto; max-width: 40%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sbox-flag { width: 24px; text-align: center; flex: 0 0 auto; }
.sbox-empty { padding: 10px 8px; color: var(--text-dim); font-size: 14px; text-align: center; }
</style>
