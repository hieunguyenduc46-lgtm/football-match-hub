<script setup>
import { useRouter } from 'vue-router'
import { isLive, isFinished, matchTime, imgFallback } from '../utils/format'

const props = defineProps({ fixture: { type: Object, required: true } })
const router = useRouter()

const f = props.fixture
const status = f.fixture.status.short
const live = isLive(status)
const finished = isFinished(status)

function open() {
  router.push({ name: 'match', params: { id: f.fixture.id } })
}
</script>

<template>
  <div class="match-card" @click="open">
    <!-- Cột trạng thái: LIVE + phút, hoặc FT, hoặc giờ đá -->
    <div class="match-card__status">
      <template v-if="live">
        <div class="live">● LIVE</div>
        <div>{{ f.fixture.status.elapsed }}'</div>
      </template>
      <template v-else-if="finished">
        <div class="ft">FT</div>
      </template>
      <template v-else>
        <div>{{ matchTime(f.fixture.date) }}</div>
      </template>
    </div>

    <!-- Hai đội -->
    <div class="match-card__teams">
      <div class="team-row" :class="{ winner: f.teams.home.winner, loser: finished && !f.teams.home.winner && f.teams.home.winner !== null }">
        <img :src="f.teams.home.logo" :alt="f.teams.home.name" @error="imgFallback" />
        <span class="name">{{ f.teams.home.name }}</span>
      </div>
      <div class="team-row" :class="{ winner: f.teams.away.winner, loser: finished && !f.teams.away.winner && f.teams.away.winner !== null }">
        <img :src="f.teams.away.logo" :alt="f.teams.away.name" @error="imgFallback" />
        <span class="name">{{ f.teams.away.name }}</span>
      </div>
    </div>

    <!-- Tỉ số (ẩn nếu chưa đá) -->
    <div class="match-card__score" v-if="f.goals.home !== null">
      <div class="g">{{ f.goals.home }}</div>
      <div class="g">{{ f.goals.away }}</div>
    </div>
  </div>
</template>
