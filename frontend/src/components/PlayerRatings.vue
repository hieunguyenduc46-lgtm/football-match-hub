<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { teamName } from '../utils/countryNames'

const props = defineProps({ data: { type: Array, required: true } })
const router = useRouter()

function rating(p) {
  // Bọc optional chaining: API có thể trả cầu thủ thiếu statistics/games.
  return parseFloat(p?.statistics?.[0]?.games?.rating) || 0
}
// Tổng bàn của cầu thủ trong trận (an toàn khi thiếu dữ liệu).
function goalsOf(p) {
  return p?.statistics?.[0]?.goals?.total || 0
}

// MOTM = điểm cao nhất toàn trận. Chỉ tính khi có rating thật (>0); nếu cả trận chưa
// chấm điểm thì KHÔNG gán MOTM (tránh badge nhầm vào cầu thủ đầu danh sách).
const motmId = computed(() => {
  let best = null
  for (const t of props.data) {
    for (const p of (t.players || [])) {
      if (rating(p) > 0 && (!best || rating(p) > rating(best))) best = p
    }
  }
  return best ? best.player?.id : null
})

function ratingClass(p) {
  const r = rating(p)
  if (r >= 7.5) return 'r-high'
  if (r >= 7.0) return 'r-mid'
  return 'r-low'
}

function goPlayer(id) {
  router.push({ name: 'player', params: { id } })
}
</script>

<template>
  <div v-if="data.length" class="ratings">
    <div v-for="t in data" :key="t.team?.id" class="rt-col">
      <div class="rt-team">{{ teamName(t.team?.name) }}</div>
      <div
        v-for="p in (t.players || [])"
        :key="p.player?.id"
        class="rt-row"
        @click="goPlayer(p.player?.id)"
      >
        <span class="nm">
          {{ p.player?.name }}
          <span v-if="p.player?.id === motmId" class="motm">MOTM</span>
          <span v-if="goalsOf(p)" class="goal">⚽</span>
        </span>
        <span class="rt" :class="ratingClass(p)">{{ p?.statistics?.[0]?.games?.rating || '—' }}</span>
      </div>
    </div>
  </div>
  <div v-else class="muted">{{ $t('noRatings') }}</div>
</template>

<style scoped>
.ratings { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.rt-team { font-size: 13px; font-weight: 700; color: var(--text-dim); margin-bottom: 6px; }
.rt-row { display: flex; justify-content: space-between; align-items: center; gap: 6px; padding: 6px 0; border-top: 1px solid var(--border); cursor: pointer; }
.rt-row:hover .nm { color: var(--accent-2); }
.nm { font-size: 13px; display: flex; align-items: center; gap: 5px; min-width: 0; }
.motm { font-size: 9px; font-weight: 800; background: #f5b301; color: #1a1206; padding: 1px 4px; border-radius: 4px; }
.goal { font-size: 11px; }
.rt { font-size: 13px; font-weight: 800; border-radius: 6px; padding: 2px 7px; color: #06140b; }
.r-high { background: var(--accent); }
.r-mid { background: #9acd32; }
.r-low { background: #6b7480; color: #fff; }
</style>
