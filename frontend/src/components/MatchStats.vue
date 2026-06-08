<script setup>
import { computed } from 'vue'
import { t } from '../i18n'

const props = defineProps({ stats: { type: Array, required: true } })

// Map loại chỉ số (API) -> khoá i18n.
const KEY = {
  'Ball Possession': 'stat_possession',
  'Total Shots': 'stat_shots',
  'Shots on Goal': 'stat_sot',
  'Shots off Goal': 'stat_shots_off',
  'Blocked Shots': 'stat_blocked',
  'Shots insidebox': 'stat_inside',
  'Shots outsidebox': 'stat_outside',
  expected_goals: 'stat_xg',
  goals_prevented: 'stat_goals_prevented',
  'Corner Kicks': 'stat_corners',
  Offsides: 'stat_offsides',
  Fouls: 'stat_fouls',
  'Yellow Cards': 'stat_yellow',
  'Red Cards': 'stat_red',
  'Goalkeeper Saves': 'stat_saves',
  'Total passes': 'stat_total_passes',
  'Passes accurate': 'stat_passes_accurate',
  'Passes %': 'stat_passes',
}

const home = computed(() => props.stats[0] || null)
const away = computed(() => props.stats[1] || null)

function num(v) {
  return parseFloat(String(v).replace('%', '')) || 0
}

// Ghép từng chỉ số: nhãn + giá trị 2 đội + % bề rộng thanh của đội nhà.
const rows = computed(() => {
  if (!home.value || !away.value) return []
  const hs = home.value.statistics || []   // API có thể thiếu mảng statistics
  const as = away.value.statistics || []
  return hs.map((s, i) => {
    const av = as[i] || {}
    const h = num(s.value)
    const a = num(av.value)
    const total = h + a
    return {
      label: KEY[s.type] ? t(KEY[s.type]) : s.type,
      hVal: s.value,
      aVal: av.value,
      hPct: total ? (h / total) * 100 : 50,
    }
  })
})
</script>

<template>
  <div v-if="rows.length">
    <div v-for="(r, i) in rows" :key="i" class="stat-row">
      <div class="stat-row__top">
        <span class="v">{{ r.hVal }}</span>
        <span class="lbl">{{ r.label }}</span>
        <span class="v">{{ r.aVal }}</span>
      </div>
      <div class="bar">
        <div class="bar__home" :style="{ width: r.hPct + '%' }"></div>
      </div>
    </div>
  </div>
  <div v-else class="muted">{{ $t('noStats') }}</div>
</template>

<style scoped>
.stat-row { margin: 12px 0; }
.stat-row__top { display: flex; justify-content: space-between; align-items: center; font-size: 13px; margin-bottom: 4px; }
.stat-row__top .v { font-weight: 700; min-width: 44px; }
.stat-row__top .v:last-child { text-align: right; }
.stat-row__top .lbl { color: var(--text-dim); }
.bar { height: 6px; border-radius: 4px; background: var(--accent-2); overflow: hidden; }
.bar__home { height: 100%; background: var(--accent); }
</style>
