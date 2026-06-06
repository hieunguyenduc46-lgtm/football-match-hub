<script setup>
import { ref, computed } from 'vue'
import api from '../services/api'
import { imgFallback } from '../utils/format'

const qa = ref(''), resa = ref([]), pa = ref(null)
const qb = ref(''), resb = ref([]), pb = ref(null)
let ta = null, tb = null
let seqA = 0, seqB = 0   // chống race: chỉ nhận kết quả của lần gõ mới nhất mỗi bên

function onType(side) {
  const q = side === 'a' ? qa.value : qb.value
  const resRef = side === 'a' ? resa : resb
  clearTimeout(side === 'a' ? ta : tb)
  if (q.trim().length < 2) { resRef.value = []; return }
  const t = setTimeout(async () => {
    const seq = side === 'a' ? ++seqA : ++seqB
    try {
      const { data } = await api.get('/search', { params: { q } })
      if (seq !== (side === 'a' ? seqA : seqB)) return   // đã có lần gõ mới hơn
      resRef.value = data.players || []
    } catch (e) { /* bỏ qua */ }
  }, 250)
  if (side === 'a') ta = t; else tb = t
}

async function pick(side, id) {
  try {
    const { data } = await api.get(`/players/${id}`)
    const p = data.response?.[0] || null
    if (side === 'a') { pa.value = p; resa.value = []; qa.value = '' }
    else { pb.value = p; resb.value = []; qb.value = '' }
  } catch (e) { /* bỏ qua */ }
}

// Cộng dồn mọi giải trong `statistics` (mảng theo từng giải) -> tổng cả mùa.
// Không lấy statistics[0] vì phần tử đầu hay là giải đá 0 trận => mọi số =0.
function aggregate(p) {
  const arr = p?.statistics || []
  if (!arr.length) return null
  const sum = (fn) => arr.reduce((t, s) => t + (fn(s) || 0), 0)
  let rW = 0, rA = 0
  for (const s of arr) {
    const r = parseFloat(s.games?.rating), a = s.games?.appearences || 0
    if (r && a) { rW += r * a; rA += a }
  }
  return {
    goals: sum(s => s.goals?.total),
    assists: sum(s => s.goals?.assists),
    apps: sum(s => s.games?.appearences),
    minutes: sum(s => s.games?.minutes),
    yellow: sum(s => s.cards?.yellow),
    rating: rA ? +(rW / rA).toFixed(2) : 0,
  }
}

const rows = computed(() => {
  if (!pa.value || !pb.value) return []
  const sa = aggregate(pa.value), sb = aggregate(pb.value)
  if (!sa || !sb) return []
  // Dùng KEY i18n thay cho chữ cứng -> đổi ngôn ngữ (VI/EN) nhãn cũng dịch theo.
  return [
    { key: 'goals', a: sa.goals, b: sb.goals },
    { key: 'assists', a: sa.assists, b: sb.assists },
    { key: 'apps', a: sa.apps, b: sb.apps },
    { key: 'minutes', a: sa.minutes, b: sb.minutes },
    { key: 'yellow', a: sa.yellow, b: sb.yellow },
    { key: 'rating', a: sa.rating, b: sb.rating },
  ]
})
</script>

<template>
  <router-link to="/" class="back">{{ $t('backHome') }}</router-link>
  <h1 class="page-title">{{ $t('compareTitle') }}</h1>

  <div class="cmp-pickers">
    <div class="cmp-pick">
      <div v-if="pa" class="cmp-head">
        <img :src="pa.player.photo" @error="imgFallback" />
        <div>{{ pa.player.name }}</div>
        <button class="link" @click="pa = null">{{ $t('change') }}</button>
      </div>
      <div v-else class="cmp-search">
        <input class="search" v-model="qa" @input="onType('a')" :placeholder="$t('playerA')" />
        <div v-if="resa.length" class="search-dd">
          <div v-for="p in resa" :key="p.id" class="dd-item" @click="pick('a', p.id)">
            <img :src="p.photo" @error="imgFallback" class="round" /> {{ p.name }}
          </div>
        </div>
      </div>
    </div>

    <div class="cmp-pick">
      <div v-if="pb" class="cmp-head">
        <img :src="pb.player.photo" @error="imgFallback" />
        <div>{{ pb.player.name }}</div>
        <button class="link" @click="pb = null">{{ $t('change') }}</button>
      </div>
      <div v-else class="cmp-search">
        <input class="search" v-model="qb" @input="onType('b')" :placeholder="$t('playerB')" />
        <div v-if="resb.length" class="search-dd">
          <div v-for="p in resb" :key="p.id" class="dd-item" @click="pick('b', p.id)">
            <img :src="p.photo" @error="imgFallback" class="round" /> {{ p.name }}
          </div>
        </div>
      </div>
    </div>
  </div>

  <div v-if="rows.length" class="cmp-table">
    <div v-for="(r, i) in rows" :key="i" class="cmp-row">
      <span class="val" :class="{ win: r.a > r.b }">{{ r.a }}</span>
      <span class="lbl">{{ $t(r.key) }}</span>
      <span class="val" :class="{ win: r.b > r.a }">{{ r.b }}</span>
    </div>
  </div>
  <div v-else class="center">{{ $t('pickTwo') }}</div>
</template>

<style scoped>
.cmp-pickers { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
.cmp-pick { position: relative; }
.cmp-head { text-align: center; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 12px; }
.cmp-head img { width: 56px; height: 56px; border-radius: 50%; object-fit: cover; }
.cmp-head div { font-weight: 600; margin-top: 6px; }
.link { background: none; border: none; color: var(--accent-2); cursor: pointer; font-size: 12px; }
.cmp-row { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; padding: 10px 0; border-top: 1px solid var(--border); }
.cmp-row .val { font-size: 18px; font-weight: 800; text-align: center; color: var(--text-dim); }
.cmp-row .val.win { color: var(--accent); }
.cmp-row .lbl { font-size: 13px; color: var(--text-dim); padding: 0 14px; }
</style>
