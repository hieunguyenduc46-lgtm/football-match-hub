<script setup>
import { computed } from 'vue'
import { matchDay, imgFallback } from '../utils/format'
import { teamName } from '../utils/countryNames'

const props = defineProps({
  matches: { type: Array, required: true },
  homeTeamId: { type: Number, required: true },
})

// Tổng kết: số trận thắng của đội nhà (trận hiện tại) / hòa / thua, xét theo homeTeamId.
const summary = computed(() => {
  let w = 0, d = 0, l = 0
  for (const m of (props.matches || [])) {
    const gh = m?.goals?.home, ga = m?.goals?.away
    if (gh == null || ga == null) continue
    if (gh === ga) { d++; continue }
    const homeWon = gh > ga
    const meIsHome = m?.teams?.home?.id === props.homeTeamId
    if ((homeWon && meIsHome) || (!homeWon && !meIsHome)) w++
    else l++
  }
  return { w, d, l }
})
</script>

<template>
  <div v-if="matches.length">
    <div class="h2h-sum">
      <div><strong>{{ summary.w }}</strong><span>{{ $t('win') }}</span></div>
      <div><strong>{{ summary.d }}</strong><span>{{ $t('draw') }}</span></div>
      <div><strong>{{ summary.l }}</strong><span>{{ $t('lose') }}</span></div>
    </div>
    <div v-for="m in matches" :key="m.fixture.id" class="h2h-row">
      <span class="dt">{{ matchDay(m.fixture.date) }}</span>
      <span class="side">
        <img loading="lazy" :src="m.teams.home.logo" @error="imgFallback" />{{ teamName(m.teams.home.name) }}
      </span>
      <span class="sc">{{ m.goals.home }} - {{ m.goals.away }}</span>
      <span class="side right">
        {{ teamName(m.teams.away.name) }}<img loading="lazy" :src="m.teams.away.logo" @error="imgFallback" />
      </span>
    </div>
  </div>
  <div v-else class="muted">{{ $t('noH2H') }}</div>
</template>

<style scoped>
.h2h-sum { display: flex; justify-content: center; gap: 28px; padding: 10px 0 16px; text-align: center; }
.h2h-sum strong { display: block; font-size: 22px; }
.h2h-sum span { font-size: 12px; color: var(--text-dim); }
.h2h-row { display: grid; grid-template-columns: 56px 1fr auto 1fr; align-items: center; gap: 8px; padding: 8px 0; border-top: 1px solid var(--border); font-size: 13px; }
.dt { color: var(--text-dim); font-size: 12px; }
.side { display: flex; align-items: center; gap: 6px; min-width: 0; }
.side.right { justify-content: flex-end; }
.side img { width: 18px; height: 18px; object-fit: contain; }
.side .nm { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sc { font-weight: 800; }
</style>
