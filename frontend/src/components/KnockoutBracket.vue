<script setup>
import { computed } from 'vue'
import { imgFallback } from '../utils/format'
import { teamName } from '../utils/countryNames'
import { roundLabel } from '../utils/roundNames'

// Takes an array of KNOCKOUT matches (from /leagues/:id/bracket) -> builds the bracket tree.
const props = defineProps({ matches: { type: Array, required: true } })

const FINISHED = ['FT', 'AET', 'PEN', 'WO', 'AWD']

// Depth of a round (small = early, large = later). Check semi/quarter/r16 BEFORE final because those names
// also contain the word "final". 3rd place -> -1 (excluded from the tree).
function roundRank(r) {
  const s = (r || '').toLowerCase()
  if (/3rd place|third place|play-off for/.test(s)) return -1
  if (/semi|1\/2/.test(s)) return 6
  if (/quarter|1\/4|last 8/.test(s)) return 5
  // "8th Finals" = round of 16 (R16); "16th Finals" = round of 32 (R32); the World Cup API often uses this style.
  if (/round of 16|1\/8|last 16|8th final/.test(s)) return 4
  if (/round of 32|1\/16|16th final/.test(s)) return 3
  if (/round of 64|1\/32|32nd final/.test(s)) return 2
  // Knockout play-off round of the new league-phase format (UCL/UEL/UECL); checked BEFORE the generic play-off.
  if (/knockout round play|knockout play/.test(s)) return 2
  if (/\bfinal\b/.test(s)) return 7
  if (/play-?off/.test(s)) return 1
  return 0
}

// Build one 'tie' from the legs (1 or 2 matches) between the same two teams.
function buildTie(key, legsIn) {
  const legs = legsIn.slice().sort((a, b) => (a.fixture.date || '').localeCompare(b.fixture.date || ''))
  const first = legs[0]
  const teamA = { id: first.teams.home.id, name: first.teams.home.name, logo: first.teams.home.logo }
  const teamB = { id: first.teams.away.id, name: first.teams.away.name, logo: first.teams.away.logo }
  const aScores = [], bScores = []
  let aggA = 0, aggB = 0, hasGoals = true
  for (const m of legs) {
    const hg = m.goals?.home, ag = m.goals?.away
    if (hg == null || ag == null) { hasGoals = false; aScores.push(null); bScores.push(null); continue }
    if (m.teams.home.id === teamA.id) { aScores.push(hg); bScores.push(ag); aggA += hg; aggB += ag }
    else { aScores.push(ag); bScores.push(hg); aggA += ag; aggB += hg }
  }
  // Penalty shoot-out taken from the last leg (if any).
  let penA = null, penB = null
  const last = legs[legs.length - 1]
  const p = last.score?.penalty
  if (p && p.home != null && p.away != null) {
    if (last.teams.home.id === teamA.id) { penA = p.home; penB = p.away } else { penA = p.away; penB = p.home }
  }
  let winnerId = null
  if (hasGoals) {
    if (aggA > aggB) winnerId = teamA.id
    else if (aggB > aggA) winnerId = teamB.id
    else if (penA != null && penB != null) winnerId = penA > penB ? teamA.id : (penB > penA ? teamB.id : null)
  }
  const finished = legs.every((m) => FINISHED.includes(m.fixture.status.short))
  return { key, teamA, teamB, aScores, bScores, aggA, aggB, penA, penB, winnerId, twoLegs: legs.length > 1, finished, fixtureId: last.fixture.id }
}

const columns = computed(() => {
  const ms = (props.matches || []).filter((m) => roundRank(m.league?.round) > 0)
  // Group by round name.
  const byRound = {}
  for (const m of ms) { const r = m.league.round; (byRound[r] = byRound[r] || []).push(m) }
  // Each round -> ties (grouped by team pair).
  const tiesByRank = {}, nameByRank = {}
  for (const rname of Object.keys(byRound)) {
    const rank = roundRank(rname)
    const pairs = {}
    for (const m of byRound[rname]) {
      const a = m.teams.home.id, b = m.teams.away.id
      const k = [Math.min(a, b), Math.max(a, b)].join('-')
      ;(pairs[k] = pairs[k] || []).push(m)
    }
    const ties = Object.keys(pairs).map((k) => buildTie(k, pairs[k]))
    // Skip rounds that are too large (>16 ties, e.g. FA Cup round of 128) to keep the tree compact.
    if (ties.length > 16) continue
    nameByRank[rank] = rname
    tiesByRank[rank] = (tiesByRank[rank] || []).concat(ties)
  }
  const ranks = Object.keys(tiesByRank).map(Number).sort((a, b) => a - b)
  if (!ranks.length) return []

  // Order the ties so the tree lines up: recurse FROM the deepest round (final) backwards.
  const ordered = {}
  const pushOrd = (rank, tie) => { (ordered[rank] = ordered[rank] || []); if (!ordered[rank].includes(tie)) ordered[rank].push(tie) }
  const lowerRank = (rank) => { const lr = ranks.filter((r) => r < rank); return lr.length ? Math.max(...lr) : null }
  function place(tie, rank) {
    pushOrd(rank, tie)
    const pr = lowerRank(rank)
    if (pr == null) return
    const prev = tiesByRank[pr] || []
    for (const tid of [tie.teamA.id, tie.teamB.id]) {
      const feeder = prev.find((t) => t.winnerId === tid && !(ordered[pr] || []).includes(t))
      if (feeder) place(feeder, pr)
    }
  }
  for (const t of (tiesByRank[ranks[ranks.length - 1]] || [])) place(t, ranks[ranks.length - 1])
  // Add any ties not reached by the recursion (in case of missing data).
  for (const rank of ranks) for (const t of tiesByRank[rank]) pushOrd(rank, t)

  return ranks.map((rank) => ({ rank, name: nameByRank[rank], ties: ordered[rank] || tiesByRank[rank] }))
})

const hasData = computed(() => columns.value.length > 0)
</script>

<template>
  <div v-if="hasData" class="kb-wrap">
    <div class="kb">
      <div v-for="col in columns" :key="col.rank" class="kb-round">
        <div class="kb-round__title">{{ roundLabel(col.name) }}</div>
        <div class="kb-round__ties">
          <div v-for="tie in col.ties" :key="tie.key" class="kb-cell">
            <router-link class="kb-tie" :to="{ name: 'match', params: { id: tie.fixtureId } }">
              <div class="kb-team" :class="{ win: tie.winnerId === tie.teamA.id }">
                <img loading="lazy" :src="tie.teamA.logo" @error="imgFallback" />
                <span class="kb-nm">{{ teamName(tie.teamA.name) }}</span>
                <span class="kb-sc"><b v-for="(s, i) in tie.aScores" :key="i">{{ s == null ? '–' : s }}</b></span>
              </div>
              <div class="kb-team" :class="{ win: tie.winnerId === tie.teamB.id }">
                <img loading="lazy" :src="tie.teamB.logo" @error="imgFallback" />
                <span class="kb-nm">{{ teamName(tie.teamB.name) }}</span>
                <span class="kb-sc"><b v-for="(s, i) in tie.bScores" :key="i">{{ s == null ? '–' : s }}</b></span>
              </div>
              <div v-if="(tie.twoLegs && tie.finished) || tie.penA != null" class="kb-agg">
                <template v-if="tie.twoLegs">{{ $t('aggregate') }} {{ tie.aggA }}-{{ tie.aggB }}<span v-if="tie.penA != null"> · p {{ tie.penA }}-{{ tie.penB }}</span></template>
                <template v-else>p {{ tie.penA }}-{{ tie.penB }}</template>
              </div>
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="muted center">{{ $t('noBracket') }}</div>
</template>

<style scoped>
.kb-wrap { overflow-x: auto; padding: 8px 2px 18px; }
.kb { display: flex; min-width: max-content; }
.kb-round { display: flex; flex-direction: column; min-width: 184px; }
.kb-round__title { font-size: 12px; font-weight: 700; color: var(--text-dim); text-transform: uppercase; letter-spacing: .3px; text-align: center; padding-bottom: 6px; }
.kb-round__ties { display: flex; flex-direction: column; justify-content: space-around; flex: 1; }
.kb-cell { display: flex; flex-direction: column; justify-content: center; flex: 1; position: relative; padding: 0 18px; }

/* Connector lines: horizontal line to the right + vertical line joining each pair. */
.kb-round:not(:last-child) .kb-cell::after {
  content: ''; position: absolute; right: 0; top: 50%; width: 18px; height: 2px; background: var(--border);
}
.kb-round:not(:last-child) .kb-cell:nth-child(odd)::before {
  content: ''; position: absolute; right: 0; top: 50%; height: 50%; width: 2px; background: var(--border);
}
.kb-round:not(:last-child) .kb-cell:nth-child(even)::before {
  content: ''; position: absolute; right: 0; bottom: 50%; height: 50%; width: 2px; background: var(--border);
}
.kb-tie {
  display: block; background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
  padding: 7px 9px; text-decoration: none; color: inherit; margin: 6px 0;
}
.kb-tie:hover { border-color: var(--accent); }
.kb-team { display: flex; align-items: center; gap: 7px; padding: 2px 0; color: var(--text-dim); }
.kb-team.win { color: var(--text); font-weight: 700; }
.kb-team img { width: 18px; height: 18px; object-fit: contain; flex: 0 0 auto; }
.kb-nm { flex: 1; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.kb-sc { display: flex; gap: 6px; flex: 0 0 auto; }
.kb-sc b { font-size: 13px; min-width: 10px; text-align: center; font-weight: inherit; }
.kb-agg { font-size: 10px; color: var(--text-dim); text-align: right; margin-top: 3px; }

/* Mobile: narrower columns + smaller text so it scrolls horizontally without overflowing the page. */
@media (max-width: 560px) {
  .kb-round { min-width: 150px; }
  .kb-cell { padding: 0 12px; }
  .kb-nm { font-size: 12px; }
  .kb-sc b { font-size: 12px; }
  .kb-round:not(:last-child) .kb-cell::after { width: 12px; }
}
</style>
