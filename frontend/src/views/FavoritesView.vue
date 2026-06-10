<script setup>
import { storeToRefs } from 'pinia'
import { useFavoritesStore } from '../stores/favorites'
import { imgFallback, matchDay } from '../utils/format'
import { leagueName } from '../utils/leagueNames'
import { teamName } from '../utils/countryNames'

const fav = useFavoritesStore()
const { teams, players, leagues, matches } = storeToRefs(fav)
</script>

<template>
  <a href="#" class="back" @click.prevent="$router.back()">{{ $t('backHome') }}</a>
  <h1 class="page-title">{{ $t('following') }}</h1>

  <div v-if="teams.length === 0 && players.length === 0 && leagues.length === 0 && matches.length === 0" class="center">
    {{ $t('emptyFav') }}
  </div>

  <template v-else>
    <template v-if="teams.length">
      <h2 class="page-title" style="font-size:16px">{{ $t('teamsLabel') }} ({{ teams.length }})</h2>
      <router-link
        v-for="t in teams"
        :key="t.id"
        :to="{ name: 'team', params: { id: t.id } }"
        class="match-card"
        style="grid-template-columns:40px 1fr auto"
      >
        <img loading="lazy" :src="t.logo" @error="imgFallback" style="width:30px;height:30px;object-fit:contain" />
        <span style="font-weight:600">{{ t.name }}</span>
        <span class="muted" style="font-size:13px">{{ $t('view') }}</span>
      </router-link>
    </template>

    <template v-if="players.length">
      <h2 class="page-title" style="font-size:16px">{{ $t('playersLabel') }} ({{ players.length }})</h2>
      <router-link
        v-for="p in players"
        :key="p.id"
        :to="{ name: 'player', params: { id: p.id } }"
        class="match-card"
        style="grid-template-columns:40px 1fr auto"
      >
        <img loading="lazy" :src="p.photo" @error="imgFallback" style="width:30px;height:30px;border-radius:50%;object-fit:cover" />
        <span style="font-weight:600">{{ p.name }}</span>
        <span class="muted" style="font-size:13px">{{ $t('view') }}</span>
      </router-link>
    </template>

    <!-- Giải đã follow -->
    <template v-if="leagues.length">
      <h2 class="page-title" style="font-size:16px">{{ $t('leaguesLabel') }} ({{ leagues.length }})</h2>
      <router-link
        v-for="l in leagues"
        :key="l.id"
        :to="{ name: 'league', params: { id: l.id } }"
        class="match-card"
        style="grid-template-columns:40px 1fr auto"
      >
        <img loading="lazy" :src="l.logo" @error="imgFallback" style="width:30px;height:30px;object-fit:contain" />
        <span style="font-weight:600">{{ leagueName(l.name, l.id) }}</span>
        <span class="muted" style="font-size:13px">{{ $t('view') }}</span>
      </router-link>
    </template>

    <!-- Trận đã follow -->
    <template v-if="matches.length">
      <h2 class="page-title" style="font-size:16px">{{ $t('matchesLabel') }} ({{ matches.length }})</h2>
      <router-link
        v-for="m in matches"
        :key="m.id"
        :to="{ name: 'match', params: { id: m.id } }"
        class="match-card"
        style="grid-template-columns:1fr auto"
      >
        <span class="fav-match">
          <span class="fav-match__teams">
            <img loading="lazy" :src="m.home.logo" @error="imgFallback" />{{ teamName(m.home.name) }}
            <span class="muted" style="font-weight:400">vs</span>
            {{ teamName(m.away.name) }}<img loading="lazy" :src="m.away.logo" @error="imgFallback" />
          </span>
          <span class="muted" style="font-size:12px">{{ m.league }}<span v-if="m.date"> · {{ matchDay(m.date) }}</span></span>
        </span>
        <span class="muted" style="font-size:13px">{{ $t('view') }}</span>
      </router-link>
    </template>
  </template>
</template>

<style scoped>
.fav-match { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.fav-match__teams { display: flex; align-items: center; gap: 6px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fav-match__teams img { width: 18px; height: 18px; object-fit: contain; flex: 0 0 auto; }
</style>
