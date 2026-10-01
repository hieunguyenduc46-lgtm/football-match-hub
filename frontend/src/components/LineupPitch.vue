<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { imgFallback, playerPhoto } from '../utils/format'
import { teamName } from '../utils/countryNames'

// Takes the lineups array (2 teams) in API-Football's shape.
const props = defineProps({ lineups: { type: Array, required: true } })
const router = useRouter()

const home = computed(() => props.lineups[0] || null)
const away = computed(() => props.lineups[1] || null)

// Is there real line-up data to show (starters OR substitutes) -> if not,
// show 'no line-up yet' instead of an empty pitch.
const hasData = computed(() => {
  const n = (t) => (t?.startXI?.length || 0) + (t?.substitutes?.length || 0)
  return n(home.value) + n(away.value) > 0
})

// Calculate % coordinates for each player from the "row:col" grid.
// row 1 = goalkeeper -> higher row = forwards. Home team in the bottom half, away team in the top half (flipped).
function positioned(team, side) {
  // The API sometimes returns a line-up WITHOUT startXI (e.g. friendlies / lower leagues) -> guard against it
  // so 'startXI is not iterable' does not crash the whole page.
  if (!team || !Array.isArray(team.startXI)) return []
  const players = team.startXI.filter((e) => e && e.player).map((e) => e.player)
  // The API sometimes does NOT return 'grid' (friendlies / lower leagues) -> every player becomes '1:1' and
  // they all stack on one row. If the grid is missing, lay them out ourselves: goalkeeper on one row,
  // the rest at most 4 per row -> no overlapping.
  const hasGrid = players.some((p) => p.grid && p.grid.includes(':'))
  const byRow = {}
  if (hasGrid) {
    for (const p of players) {
      const [r, c] = (p.grid || '1:1').split(':').map(Number)
      ;(byRow[r] = byRow[r] || []).push({ ...p, _c: c })
    }
  } else {
    const gk = players[0]
    const rest = players.slice(1)
    if (gk) byRow[1] = [{ ...gk, _c: 1 }]
    let r = 2, c = 1
    for (const p of rest) {
      ;(byRow[r] = byRow[r] || []).push({ ...p, _c: c })
      if (++c > 4) { r++; c = 1 }
    }
  }
  const rowNums = Object.keys(byRow).map(Number).sort((a, b) => a - b)
  const nRows = Math.max(...rowNums, 1)
  const out = []
  for (const r of rowNums) {
    const players = byRow[r].sort((a, b) => a._c - b._c)
    const k = players.length
    players.forEach((p, i) => {
      const x = ((i + 1) / (k + 1)) * 100
      const t = nRows === 1 ? 0 : (r - 1) / (nRows - 1) // 0 = GK, 1 = forward
      const y = side === 'home' ? 96 - t * 40 : 4 + t * 40
      out.push({ ...p, x, y })
    })
  }
  return out
}

const homePlayers = computed(() => positioned(home.value, 'home'))
const awayPlayers = computed(() => positioned(away.value, 'away'))

function goPlayer(id) {
  if (id) router.push({ name: 'player', params: { id } })
}
</script>

<template>
  <div v-if="hasData">
    <div class="pitch">
      <!-- pitch markings -->
      <div class="pitch__line"></div>
      <div class="pitch__circle"></div>
      <div class="pitch__box pitch__box--top"></div>
      <div class="pitch__box pitch__box--bottom"></div>

      <div class="pitch__label pitch__label--top" v-if="away">
        <img loading="lazy" :src="away.team?.logo" @error="imgFallback" /> {{ teamName(away.team?.name) }}<span v-if="away.formation"> · {{ away.formation }}</span>
      </div>
      <div class="pitch__label pitch__label--bottom" v-if="home">
        {{ teamName(home.team?.name) }}<span v-if="home.formation"> · {{ home.formation }}</span> <img loading="lazy" :src="home.team?.logo" @error="imgFallback" />
      </div>

      <!-- away players (top) -->
      <div v-for="p in awayPlayers" :key="'a' + p.id" class="pp" :style="{ left: p.x + '%', top: p.y + '%' }" @click="goPlayer(p.id)">
        <img loading="lazy" :src="playerPhoto(p)" @error="imgFallback" />
        <span class="num">{{ p.number }}</span>
        <span class="nm">{{ p.name }}</span>
      </div>
      <!-- home players (bottom) -->
      <div v-for="p in homePlayers" :key="'h' + p.id" class="pp" :style="{ left: p.x + '%', top: p.y + '%' }" @click="goPlayer(p.id)">
        <img loading="lazy" :src="playerPhoto(p)" @error="imgFallback" />
        <span class="num">{{ p.number }}</span>
        <span class="nm">{{ p.name }}</span>
      </div>
    </div>

    <!-- substitutes' bench + coach -->
    <div class="subs-wrap">
      <div v-for="(t, idx) in lineups" :key="idx" class="subs-col">
        <div class="subs-title"><img loading="lazy" :src="t.team?.logo" @error="imgFallback" /> {{ $t('subs') }}</div>
        <div v-for="s in (t.substitutes || [])" :key="s.player?.id" class="sub-row" @click="goPlayer(s.player?.id)">
          <span class="muted">#{{ s.player?.number }}</span> {{ s.player?.name }}
        </div>
        <div class="muted" style="margin-top:8px;font-size:13px" v-if="t.coach">{{ $t('coach') }}: {{ t.coach.name }}</div>
      </div>
    </div>
  </div>
  <div v-else class="muted">{{ $t('noLineup') }}</div>
</template>

<style scoped>
.pitch {
  position: relative;
  width: 100%;
  aspect-ratio: 2 / 3;
  background: repeating-linear-gradient(180deg, #1f7a44 0 8%, #1c6f3e 8% 16%);
  border: 2px solid rgba(255, 255, 255, 0.25);
  border-radius: 12px;
  overflow: hidden;
  margin: 8px 0;
}
.pitch__line { position: absolute; top: 50%; left: 0; right: 0; height: 2px; background: rgba(255, 255, 255, 0.35); }
.pitch__circle {
  position: absolute; top: 50%; left: 50%; width: 22%; aspect-ratio: 1;
  transform: translate(-50%, -50%); border: 2px solid rgba(255, 255, 255, 0.35); border-radius: 50%;
}
.pitch__box { position: absolute; left: 50%; transform: translateX(-50%); width: 52%; height: 13%; border: 2px solid rgba(255, 255, 255, 0.3); }
.pitch__box--top { top: 0; border-top: none; border-radius: 0 0 8px 8px; }
.pitch__box--bottom { bottom: 0; border-bottom: none; border-radius: 8px 8px 0 0; }

.pitch__label {
  position: absolute; z-index: 5; display: flex; align-items: center; gap: 5px;
  font-size: 11px; color: #fff; background: rgba(0, 0, 0, 0.45); padding: 3px 8px; border-radius: 8px;
}
.pitch__label img { width: 15px; height: 15px; object-fit: contain; }
.pitch__label--top { top: 6px; left: 6px; }
.pitch__label--bottom { bottom: 6px; right: 6px; }

.pp { position: absolute; transform: translate(-50%, -50%); display: flex; flex-direction: column; align-items: center; width: 56px; cursor: pointer; }
.pp img { width: 34px; height: 34px; border-radius: 50%; object-fit: cover; border: 2px solid #fff; background: #1c232d; }
.pp .num {
  position: absolute; top: -5px; right: 9px; background: #0e1116; color: #fff;
  font-size: 10px; font-weight: 700; border-radius: 50%; width: 17px; height: 17px;
  display: flex; align-items: center; justify-content: center; border: 1px solid #fff;
}
.pp .nm {
  margin-top: 3px; font-size: 10px; color: #fff; text-shadow: 0 1px 2px rgba(0, 0, 0, 0.9);
  white-space: nowrap; max-width: 62px; overflow: hidden; text-overflow: ellipsis;
}

.subs-wrap { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 14px; }
.subs-title { font-size: 13px; font-weight: 600; color: var(--text-dim); display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.subs-title img { width: 16px; height: 16px; object-fit: contain; }
.sub-row { font-size: 13px; padding: 3px 0; cursor: pointer; }
.sub-row:hover { color: var(--accent-2); }

/* Mobile: shrink players + names so 4-5 per row do not overlap,
   and stack the 2 substitute columns into 1 column for readability. */
@media (max-width: 560px) {
  .pp { width: 44px; }
  .pp img { width: 28px; height: 28px; }
  .pp .num { top: -4px; right: 5px; width: 15px; height: 15px; font-size: 9px; }
  .pp .nm { font-size: 9px; max-width: 50px; margin-top: 2px; }
  .pitch__label { font-size: 10px; padding: 2px 6px; }
  .subs-wrap { grid-template-columns: 1fr; gap: 10px; }
}
</style>
