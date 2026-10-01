<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { isFinished, isLiveFixture, isStaleLive, isOff, offStatusKey, isBreak, breakStatusKey, matchTime, matchDay, imgFallback } from '../utils/format'
import { teamName } from '../utils/countryNames'

const props = defineProps({
  fixture: { type: Object, required: true },
  // Enable to also show the DATE (for fixture tabs spanning many days: league, country).
  // The home page groups by a single day, so it is not needed -> off by default.
  showDate: { type: Boolean, default: false },
})
const router = useRouter()

// IMPORTANT: use computed (reads props.fixture every time) instead of a 'snapshot' taken at setup.
// HomeView auto-refreshes every 15s and reassigns the fixtures array (NEW objects with the same :key) -> if
// we snapshot with `const f = props.fixture`, the live score/minute would be 'frozen'.
// computed updates whenever the prop changes -> live cards update their score automatically.
const f = computed(() => props.fixture)
// 'Stuck live' (status stuck in play for hours) -> treat as finished, do not show the LIVE badge.
const live = computed(() => isLiveFixture(props.fixture))
const finished = computed(() => isFinished(props.fixture.fixture.status.short) || isStaleLive(props.fixture))
// Cancelled/postponed match -> show a separate label instead of the kick-off time (avoids looking 'upcoming').
const off = computed(() => isOff(props.fixture.fixture.status.short))
const offLabel = computed(() => offStatusKey(props.fixture.fixture.status.short))
// At a break (HT/BT/P): show a label such as 'Half-time' instead of the minute.
const onBreak = computed(() => live.value && isBreak(props.fixture.fixture.status.short))
const breakLabel = computed(() => breakStatusKey(props.fixture.fixture.status.short))
// Penalty shoot-out score (if the match went to penalties) -> small number next to each team's score to show who won the draw.
const pen = computed(() => {
  const p = props.fixture?.score?.penalty
  return (p && p.home != null && p.away != null) ? p : null
})

function open() {
  router.push({ name: 'match', params: { id: props.fixture.fixture.id } })
}
</script>

<template>
  <div class="match-card" @click="open">
    <!-- Status column: LIVE + minute, or FT, or kick-off time -->
    <div class="match-card__status">
      <div v-if="showDate" class="mc-date">{{ matchDay(f.fixture.date) }}</div>
      <template v-if="live">
        <div class="live">● LIVE</div>
        <div v-if="onBreak">{{ $t(breakLabel) }}</div>
        <div v-else>{{ f.fixture.status.elapsed }}{{ f.fixture.status.extra ? '+' + f.fixture.status.extra : '' }}'</div>
      </template>
      <template v-else-if="finished">
        <div class="ft">FT</div>
      </template>
      <template v-else-if="off">
        <div class="mc-off">{{ $t(offLabel) }}</div>
      </template>
      <template v-else>
        <div>{{ matchTime(f.fixture.date) }}</div>
      </template>
    </div>

    <!-- The two teams -->
    <div class="match-card__teams">
      <div class="team-row" :class="{ winner: f.teams.home.winner, loser: finished && !f.teams.home.winner && f.teams.home.winner !== null }">
        <img loading="lazy" :src="f.teams.home.logo" :alt="f.teams.home.name" @error="imgFallback" />
        <span class="name">{{ teamName(f.teams.home.name) }}</span>
      </div>
      <div class="team-row" :class="{ winner: f.teams.away.winner, loser: finished && !f.teams.away.winner && f.teams.away.winner !== null }">
        <img loading="lazy" :src="f.teams.away.logo" :alt="f.teams.away.name" @error="imgFallback" />
        <span class="name">{{ teamName(f.teams.away.name) }}</span>
      </div>
    </div>

    <!-- Score (hidden if not played yet) -->
    <div class="match-card__score" v-if="f.goals.home !== null">
      <div class="g">{{ f.goals.home }}<span v-if="pen" class="pmini">({{ pen.home }})</span></div>
      <div class="g">{{ f.goals.away }}<span v-if="pen" class="pmini">({{ pen.away }})</span></div>
    </div>
  </div>
</template>

<style scoped>
.mc-date { font-size: 11px; color: var(--text-dim); margin-bottom: 2px; white-space: nowrap; }
.mc-off { font-size: 12px; font-weight: 700; color: var(--live); white-space: nowrap; }
.pmini { font-size: 11px; font-weight: 600; color: var(--text-dim); margin-left: 2px; }
</style>
