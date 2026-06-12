<script setup>
const props = defineProps({
  events: { type: Array, required: true },
  homeTeamId: { type: Number, required: true },
})

function isHome(e) {
  return e?.team?.id === props.homeTeamId
}

// Phút sự kiện, KÈM bù giờ nếu có (vd 45+3, 90+2). Khớp cách hiển thị ở tóm tắt bàn thắng.
function minute(e) {
  const tm = e.time || {}
  if (tm.elapsed == null) return ''
  return tm.extra ? `${tm.elapsed}+${tm.extra}` : `${tm.elapsed}`
}

// Icon theo loại sự kiện.
function icon(e) {
  if (e.type === 'Goal') return e.detail === 'Own Goal' ? '⚽(OG)' : '⚽'
  if (e.type === 'Card') return e.detail === 'Red Card' ? '🟥' : '🟨'
  if (e.type === 'subst') return '🔁'
  return '•'
}
</script>

<template>
  <div class="tl" v-if="events.length">
    <div v-for="(e, i) in events" :key="i" class="tl-row">
      <div class="tl-cell left">
        <template v-if="isHome(e)">
          <span class="info">
            <span class="nm">{{ e.player?.name || '—' }}</span>
            <span class="sub" v-if="e.assist && e.assist.name">{{ e.assist.name }}</span>
          </span>
          <span class="ic">{{ icon(e) }}</span>
        </template>
      </div>
      <div class="tl-min">{{ minute(e) }}'</div>
      <div class="tl-cell right">
        <template v-if="!isHome(e)">
          <span class="ic">{{ icon(e) }}</span>
          <span class="info">
            <span class="nm">{{ e.player?.name || '—' }}</span>
            <span class="sub" v-if="e.assist && e.assist.name">{{ e.assist.name }}</span>
          </span>
        </template>
      </div>
    </div>
  </div>
  <div v-else class="muted">{{ $t('noEvents') }}</div>
</template>

<style scoped>
.tl { position: relative; }
.tl::before { content: ''; position: absolute; top: 0; bottom: 0; left: 50%; width: 2px; background: var(--border); transform: translateX(-50%); }
.tl-row { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 10px; padding: 8px 0; position: relative; }
.tl-cell { display: flex; align-items: center; gap: 8px; }
.tl-cell.left { justify-content: flex-end; text-align: right; }
.tl-cell.right { justify-content: flex-start; text-align: left; }
.tl-min {
  background: var(--surface-2); border: 1px solid var(--border); color: var(--text-dim);
  font-size: 12px; font-weight: 700; border-radius: 999px; padding: 3px 9px; z-index: 1; min-width: 38px; text-align: center;
}
.ic { font-size: 16px; }
.info { display: flex; flex-direction: column; }
.nm { font-size: 14px; font-weight: 600; }
.sub { font-size: 12px; color: var(--text-dim); }
</style>
