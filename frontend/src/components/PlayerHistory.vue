<script setup>
import { computed } from 'vue'
import { t } from '../i18n'
import { teamName } from '../utils/countryNames'
import { injuryName } from '../utils/injuryNames'
import { imgFallback } from '../utils/format'

// history = { trophies, transfers, sidelined, seasons }
const props = defineProps({
  history: { type: Object, default: () => ({}) },
  loading: { type: Boolean, default: false },
})

const trophies = computed(() => props.history?.trophies || [])
const transfers = computed(() => props.history?.transfers || [])
const sidelined = computed(() => props.history?.sidelined || [])
const seasons = computed(() => props.history?.seasons || [])

// ===== Danh hiệu: gộp các lần VÔ ĐỊCH theo từng giải, đếm số lần =====
const titles = computed(() => {
  const won = trophies.value.filter((x) => (x.place || '').toLowerCase() === 'winner')
  const map = new Map() // league -> count
  for (const x of won) {
    const k = x.league || '—'
    map.set(k, (map.get(k) || 0) + 1)
  }
  return [...map.entries()]
    .map(([league, count]) => ({ league, count }))
    .sort((a, b) => b.count - a.count)
})
const titlesTotal = computed(() => trophies.value.filter((x) => (x.place || '').toLowerCase() === 'winner').length)
const runnerUp = computed(() => trophies.value.filter((x) => (x.place || '').toLowerCase() !== 'winner').length)

// ===== Chuyển nhượng: mới nhất trước =====
const moves = computed(() =>
  [...transfers.value]
    .filter((x) => x && x.teams)
    .sort((a, b) => String(b.date).localeCompare(String(a.date)))
)
function yearOf(d) { return d ? String(d).slice(0, 4) : '' }

// ===== Chấn thương / treo giò: mới nhất trước, giới hạn 10 =====
const sidelinedList = computed(() =>
  [...sidelined.value]
    .sort((a, b) => String(b.start).localeCompare(String(a.start)))
    .slice(0, 10)
)

const hasAny = computed(
  () => titles.value.length || moves.value.length || sidelinedList.value.length || seasons.value.length
)
</script>

<template>
  <div v-if="loading" class="skeleton" style="height:120px; margin-top:16px"></div>

  <template v-else-if="hasAny">
    <!-- DANH HIỆU -->
    <div v-if="titlesTotal || runnerUp">
      <h3 class="stat-group">
        {{ $t('histTrophies') }}
        <span class="natl-tag">{{ titlesTotal }} {{ $t('histTitlesWon') }}</span>
      </h3>
      <div class="chips">
        <span v-for="tr in titles" :key="tr.league" class="chip">
          {{ tr.league }}<span v-if="tr.count > 1" class="chip-x"> ×{{ tr.count }}</span>
        </span>
        <span v-if="runnerUp" class="chip chip-muted">{{ runnerUp }} {{ $t('histRunnerUp') }}</span>
      </div>
    </div>

    <!-- THỐNG KÊ THEO MÙA -->
    <div v-if="seasons.length">
      <h3 class="stat-group">{{ $t('histSeasons') }}</h3>
      <div class="comp-wrap">
        <table class="comp-table">
          <thead>
            <tr>
              <th class="left">{{ $t('seasonColH') }}</th>
              <th class="left">{{ $t('teamColH') }}</th>
              <th>{{ $t('col_apps') }}</th>
              <th>{{ $t('col_goals') }}</th>
              <th>{{ $t('col_assists') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in seasons" :key="s.season">
              <td class="left">{{ s.season }}</td>
              <td class="left">{{ teamName(s.team || '—') }}</td>
              <td>{{ s.apps }}</td>
              <td>{{ s.goals }}</td>
              <td>{{ s.assists }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- CHUYỂN NHƯỢNG -->
    <div v-if="moves.length">
      <h3 class="stat-group">{{ $t('histTransfers') }}</h3>
      <div class="tl">
        <div v-for="(m, i) in moves" :key="i" class="tl-row">
          <span class="tl-year">{{ yearOf(m.date) }}</span>
          <span class="tl-move">
            <img v-if="m.teams.out" loading="lazy" :src="m.teams.out.logo" class="tl-logo" @error="imgFallback" />
            {{ teamName(m.teams.out?.name || '—') }}
            <span class="tl-arrow">→</span>
            <img v-if="m.teams.in" loading="lazy" :src="m.teams.in.logo" class="tl-logo" @error="imgFallback" />
            {{ teamName(m.teams.in?.name || '—') }}
          </span>
          <span v-if="m.type" class="tl-fee">{{ m.type }}</span>
        </div>
      </div>
    </div>

    <!-- CHẤN THƯƠNG / TREO GIÒ -->
    <div v-if="sidelinedList.length">
      <h3 class="stat-group">{{ $t('histInjuries') }}</h3>
      <div class="tl">
        <div v-for="(s, i) in sidelinedList" :key="i" class="tl-row">
          <span class="tl-year">{{ yearOf(s.start) }}</span>
          <span class="tl-move">{{ injuryName(s.type) }}</span>
          <span class="tl-fee muted">{{ s.start }} → {{ s.end || '…' }}</span>
        </div>
      </div>
    </div>
  </template>
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
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip {
  font-size: 13px;
  font-weight: 600;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 4px 12px;
}
.chip-x { color: var(--accent); font-weight: 800; }
.chip-muted { color: var(--text-dim); font-weight: 600; }

.comp-wrap {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
}
.comp-table { width: 100%; border-collapse: collapse; font-size: 13px; min-width: 360px; }
.comp-table th, .comp-table td { padding: 9px 10px; text-align: center; white-space: nowrap; }
.comp-table th {
  font-size: 11px; font-weight: 600; color: var(--text-dim);
  text-transform: uppercase; letter-spacing: .3px; border-bottom: 1px solid var(--border);
}
.comp-table td { border-bottom: 1px solid var(--border); }
.comp-table tbody tr:last-child td { border-bottom: none; }
.comp-table .left { text-align: left; }

.tl {
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
  overflow: hidden;
}
.tl-row {
  display: grid;
  grid-template-columns: 52px 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  font-size: 13px;
  border-bottom: 1px solid var(--border);
}
.tl-row:last-child { border-bottom: none; }
.tl-year { font-weight: 800; color: var(--text-dim); }
.tl-move { display: flex; align-items: center; gap: 6px; font-weight: 600; flex-wrap: wrap; }
.tl-logo { width: 18px; height: 18px; object-fit: contain; flex: none; }
.tl-arrow { color: var(--text-dim); }
.tl-fee { font-size: 12px; color: var(--accent-2); font-weight: 700; }
</style>
