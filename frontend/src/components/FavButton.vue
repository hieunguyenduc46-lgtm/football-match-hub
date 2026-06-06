<script setup>
import { computed } from 'vue'
import { useFavoritesStore } from '../stores/favorites'

const props = defineProps({
  type: { type: String, required: true }, // 'team' | 'player'
  item: { type: Object, required: true }, // { id, name, logo | photo }
})

const fav = useFavoritesStore()
const active = computed(() =>
  props.type === 'team' ? fav.isTeamFav(props.item.id) : fav.isPlayerFav(props.item.id)
)

function toggle() {
  if (props.type === 'team') fav.toggleTeam(props.item)
  else fav.togglePlayer(props.item)
}
</script>

<template>
  <button
    class="fav-btn"
    :class="{ active }"
    @click.stop.prevent="toggle"
    :title="active ? $t('followingShort') : $t('follow')"
  >
    <span class="star">{{ active ? '★' : '☆' }}</span>
    <span class="lbl">{{ active ? $t('followingShort') : $t('follow') }}</span>
  </button>
</template>

<style scoped>
.fav-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--surface); border: 1px solid var(--border); color: var(--text-dim);
  border-radius: 999px; padding: 6px 12px; font-size: 13px; font-weight: 600;
  cursor: pointer; font-family: inherit;
}
.fav-btn:hover { border-color: var(--accent); }
.fav-btn.active { color: #f5b301; border-color: #f5b301; }
.star { font-size: 15px; }
</style>
