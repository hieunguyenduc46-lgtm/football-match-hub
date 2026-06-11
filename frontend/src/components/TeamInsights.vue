<script setup>
import { computed } from 'vue'
import { imgFallback } from '../utils/format'
import { injuryName } from '../utils/injuryNames'

// statistics = object /teams/statistics (đã trim, kèm _league). injuries = [{name, reason, photo}]
const props = defineProps({
  statistics: { type: Object, default: () => ({}) },
  injuries: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const s = computed(() => props.statistics || {})
const hasStats = computed(() => !!(s.value && s.value.fixtures))
const lg = computed(() => s.value._league || null)

const fx = computed(() => s.value.fixtures || {})
const goals = computed(() => s.value.goals || {})
const biggest = computed(() => s.value.biggest || {})

function n(v) { return v != null ? v : 0 }

const injuries = computed(() => (props.injuries || []).slice(0, 16))
const hasAny = computed(() => hasStats.value || injuries.value.length)
</script>

<template>
  <div v-if="loading" class="skeleton" style="height:110px; margin-top:16px"></div>

  <template v-else-if="hasAny">
    <!-- THỐNG KÊ MÙA -->
    <div v-if="hasStats">
      <h2 class="page-title" style="font-size:16px; display:flex; align-items:center; gap:8px;">
        {{ $t('teamStatsH') }}
        <span v-if="lg" class="ti-lg"><img v-if="lg.logo" :src="lg.logo" @error="imgFallback" />{{ lg.name }}</span>
      </h2>
      <div class="ti-grid">
        <div class="ti-cell"><div class="ti-num">{{ n(fx.played?.total) }}</div><div class="ti-lab">{{ $t('ts_played') }}</div></div>
        <div class="ti-cell"><div class="ti-num">{{ n(fx.wins?.total) }}-{{ n(fx.draws?.total) }}-{{ n(fx.loses?.total) }}</div><div class="ti-lab">{{ $t('ts_wdl') }}</div></div>
        <div class="ti-cell"><div class="ti-num">{{ n(goals.for?.total?.total) }}</div><div class="ti-lab">{{ $t('ts_gf') }} · {{ goals.for?.average?.total ?? '—' }}</div></div>
        <div class="ti-cell"><div class="ti-num">{{ n(goals.against?.total?.total) }}</div><div class="ti-lab">{{ $t('ts_ga') }} · {{ goals.against?.average?.total ?? '—' }}</div></div>
        <div class="ti-cell"><div class="ti-num">{{ n(s.clean_sheet?.total) }}</div><div class="ti-lab">{{ $t('ts_clean') }}</div></div>
        <div class="ti-cell"><div class="ti-num">{{ n(biggest.streak?.wins) }}</div><div class="ti-lab">{{ $t('ts_streak') }}</div></div>
      </div>
      <div v-if="biggest.wins?.home || biggest.wins?.away" class="ti-biggest muted">
        {{ $t('ts_biggestWin') }}:
        <span v-if="biggest.wins?.home"> {{ biggest.wins.home }} ({{ $t('homeShort') }})</span>
        <span v-if="biggest.wins?.away"> · {{ biggest.wins.away }} ({{ $t('awayShort') }})</span>
      </div>
    </div>

    <!-- CHẤN THƯƠNG / TREO GIÒ -->
    <div v-if="injuries.length">
      <h2 class="page-title" style="font-size:16px">{{ $t('teamInjuriesH') }}</h2>
      <div class="ti-inj">
        <div v-for="p in injuries" :key="p.id" class="ti-inj-item">
          <img loading="lazy" :src="p.photo" @error="imgFallback" />
          <div class="ti-inj-txt">
            <div class="ti-inj-name">{{ p.name }}</div>
            <div class="ti-inj-reason muted">{{ injuryName(p.reason || p.type) }}</div>
          </div>
        </div>
      </div>
    </div>
  </template>
</template>

<style scoped>
.ti-lg {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 11px; font-weight: 600; color: var(--text-dim);
  border: 1px solid var(--border); border-radius: 6px; padding: 1px 7px;
}
.ti-lg img { width: 14px; height: 14px; object-fit: contain; }

.ti-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.ti-cell {
  border: 1px solid var(--border); border-radius: 12px; background: var(--surface);
  padding: 12px 10px; text-align: center;
}
.ti-num { font-size: 22px; font-weight: 800; color: var(--accent); line-height: 1.1; }
.ti-lab { font-size: 11px; color: var(--text-dim); margin-top: 4px; }
.ti-biggest { margin-top: 10px; font-size: 13px; }

.ti-inj { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.ti-inj-item {
  display: flex; align-items: center; gap: 10px;
  border: 1px solid var(--border); border-radius: 12px; background: var(--surface);
  padding: 8px 12px;
}
.ti-inj-item img { width: 34px; height: 34px; border-radius: 50%; object-fit: cover; flex: none; }
.ti-inj-name { font-weight: 600; font-size: 14px; }
.ti-inj-reason { font-size: 12px; }

@media (max-width: 560px) {
  .ti-grid { grid-template-columns: repeat(2, 1fr); }
  .ti-inj { grid-template-columns: 1fr; }
}
</style>
