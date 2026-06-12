<script setup>
import { computed } from 'vue'
import { t } from '../i18n'
import { teamName } from '../utils/countryNames'

// data = object dự đoán API trả về (predictions + comparison + teams). {} nếu không có.
const props = defineProps({
  data: { type: Object, default: () => ({}) },
  home: { type: Object, default: () => ({}) },
  away: { type: Object, default: () => ({}) },
})

const pred = computed(() => props.data?.predictions || null)

// "45%" -> 45 (số). Lỗi/thiếu -> 0.
function pct(v) {
  const n = parseInt(String(v ?? '').replace('%', ''), 10)
  return Number.isNaN(n) ? 0 : n
}

// Xác suất Thắng/Hòa/Thua.
// API trả `percent` khá THÔ cho trận ít dữ liệu (hay gom về 10/45/45...). Ta tính lại từ
// `comparison` (phong độ/tấn công/phòng thủ/poisson/đối đầu — các số này MỊN và thật hơn)
// để ra con số sát thực tế hơn. Không có comparison -> mới dùng percent gốc của API.
const percent = computed(() => {
  const c = props.data?.comparison || {}
  const fields = ['form', 'att', 'def', 'poisson_distribution', 'h2h', 'total']
  let hs = 0, as = 0, n = 0
  for (const f of fields) {
    const cell = c[f]
    if (cell && (cell.home != null || cell.away != null)) {
      hs += pct(cell.home); as += pct(cell.away); n++
    }
  }
  // Không có ô so sánh, HOẶC mọi ô đều 0% (trận mô phỏng/chưa có dữ liệu) -> dùng số gốc API.
  // (Nếu vẫn chia khi tổng = 0 sẽ ra số vô lý kiểu 0/30/70 dù đội đó thắng.)
  if (n === 0 || hs + as === 0) {
    const p = pred.value?.percent || {}
    return { home: pct(p.home), draw: pct(p.draw), away: pct(p.away) }
  }
  const total = hs + as
  const h = hs / total, a = as / total            // tỉ trọng sức mạnh 2 đội (cộng = 1)
  const diff = Math.abs(h - a)
  let draw = Math.round(30 * (1 - diff))           // hòa CAO khi cân tài (tối đa ~30%), thấp khi lệch
  if (draw < 5) draw = 5
  const rem = 100 - draw
  let home = Math.round(rem * h)
  let away = 100 - draw - home
  if (away < 0) { away = 0; home = 100 - draw }
  return { home, draw, away }
})

const advice = computed(() => pred.value?.advice || '')

// Các hàng so sánh 2 đội (mỗi giá trị là "x%"). Bỏ hàng nào API không có.
const rows = computed(() => {
  const c = props.data?.comparison || {}
  const meta = [
    { key: 'form', label: 'cmp_form' },
    { key: 'att', label: 'cmp_att' },
    { key: 'def', label: 'cmp_def' },
    { key: 'h2h', label: 'cmp_h2h' },
  ]
  return meta
    .filter((m) => c[m.key] && (c[m.key].home != null || c[m.key].away != null))
    .map((m) => ({ label: m.label, home: pct(c[m.key].home), away: pct(c[m.key].away) }))
    .filter((r) => r.home || r.away)   // bỏ hàng 0%/0% (không có dữ liệu thật) cho gọn
})
</script>

<template>
  <div v-if="!pred" class="center">{{ $t('noPrediction') }}</div>
  <div v-else class="pred">
    <!-- Thanh xác suất Thắng / Hòa / Thua -->
    <div class="pred-bar">
      <span class="seg home" :style="{ width: percent.home + '%' }"></span>
      <span class="seg draw" :style="{ width: percent.draw + '%' }"></span>
      <span class="seg away" :style="{ width: percent.away + '%' }"></span>
    </div>
    <div class="pred-legend">
      <div class="pl home">
        <div class="pl-val">{{ percent.home }}%</div>
        <div class="pl-name">{{ teamName(home.name || '') }}</div>
      </div>
      <div class="pl draw">
        <div class="pl-val">{{ percent.draw }}%</div>
        <div class="pl-name">{{ $t('predDraw') }}</div>
      </div>
      <div class="pl away">
        <div class="pl-val">{{ percent.away }}%</div>
        <div class="pl-name">{{ teamName(away.name || '') }}</div>
      </div>
    </div>

    <!-- Lời khuyên -->
    <div v-if="advice" class="pred-advice">
      <span class="muted">{{ $t('predAdvice') }}:</span> {{ advice }}
    </div>

    <!-- So sánh phong độ / tấn công / phòng thủ / đối đầu -->
    <div v-if="rows.length" class="pred-compare">
      <div class="pc-title muted">{{ $t('predCompare') }}</div>
      <div v-for="r in rows" :key="r.label" class="pc-row">
        <span class="pc-num">{{ r.home }}%</span>
        <span class="pc-bar">
          <span class="pc-h" :style="{ width: r.home + '%' }"></span>
          <span class="pc-a" :style="{ width: r.away + '%' }"></span>
        </span>
        <span class="pc-num right">{{ r.away }}%</span>
      </div>
      <div class="pc-label muted">{{ $t('cmp_form') }} · {{ $t('cmp_att') }} · {{ $t('cmp_def') }} · {{ $t('cmp_h2h') }}</div>
    </div>
  </div>
</template>

<style scoped>
.pred { padding: 6px 0 4px; }
.pred-bar { display: flex; height: 14px; border-radius: 7px; overflow: hidden; background: var(--surface-2); }
.seg { display: block; height: 100%; }
.seg.home { background: var(--accent); }
.seg.draw { background: #9aa3ad; }
.seg.away { background: var(--accent-2); }
.pred-legend { display: flex; justify-content: space-between; margin-top: 8px; }
.pl { text-align: center; flex: 1; }
.pl.home { text-align: left; }
.pl.away { text-align: right; }
.pl-val { font-weight: 800; font-size: 16px; }
.pl-name { font-size: 12px; color: var(--text-dim); }
.pred-advice { margin-top: 14px; font-size: 14px; line-height: 1.5; background: var(--surface-2); border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; }
.pred-compare { margin-top: 16px; }
.pc-title { font-size: 13px; margin-bottom: 8px; }
.pc-row { display: grid; grid-template-columns: 38px 1fr 38px; align-items: center; gap: 8px; margin-bottom: 8px; }
.pc-num { font-size: 12px; font-weight: 700; }
.pc-num.right { text-align: right; }
.pc-bar { display: flex; height: 8px; border-radius: 4px; overflow: hidden; background: var(--surface-2); }
.pc-h { background: var(--accent); height: 100%; }
.pc-a { background: var(--accent-2); height: 100%; }
.pc-label { font-size: 11px; text-align: center; margin-top: 2px; }
</style>
