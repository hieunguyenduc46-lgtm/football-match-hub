<script setup>
import { storeToRefs } from 'pinia'
import { useFavoritesStore } from '../stores/favorites'
import { imgFallback } from '../utils/format'

const fav = useFavoritesStore()
const { teams, players } = storeToRefs(fav)
</script>

<template>
  <router-link to="/" class="back">{{ $t('backHome') }}</router-link>
  <h1 class="page-title">{{ $t('following') }}</h1>

  <div v-if="teams.length === 0 && players.length === 0" class="center">
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
        <img :src="t.logo" @error="imgFallback" style="width:30px;height:30px;object-fit:contain" />
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
        <img :src="p.photo" @error="imgFallback" style="width:30px;height:30px;border-radius:50%;object-fit:cover" />
        <span style="font-weight:600">{{ p.name }}</span>
        <span class="muted" style="font-size:13px">{{ $t('view') }}</span>
      </router-link>
    </template>
  </template>
</template>
