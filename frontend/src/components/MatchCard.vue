<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { isFinished, isLiveFixture, isStaleLive, isOff, offStatusKey, matchTime, matchDay, imgFallback } from '../utils/format'
import { teamName } from '../utils/countryNames'

const props = defineProps({
  fixture: { type: Object, required: true },
  // Bật để hiện thêm NGÀY (cho các tab lịch đấu trải nhiều ngày: giải, quốc gia).
  // Trang chủ gom theo 1 ngày nên không cần -> mặc định tắt.
  showDate: { type: Boolean, default: false },
})
const router = useRouter()

// QUAN TRỌNG: dùng computed (đọc props.fixture mỗi lần) thay vì "snapshot" lúc setup.
// HomeView auto-refresh 15s gán lại mảng fixtures (object MỚI nhưng cùng :key) -> nếu
// snapshot bằng `const f = props.fixture` thì tỉ số/phút trận live bị "đóng băng".
// computed cập nhật được mỗi khi prop đổi -> card live tự lên điểm.
const f = computed(() => props.fixture)
// "Live treo" (status kẹt đang đá nhiều giờ) -> coi như đã kết thúc, không hiện badge LIVE.
const live = computed(() => isLiveFixture(props.fixture))
const finished = computed(() => isFinished(props.fixture.fixture.status.short) || isStaleLive(props.fixture))
// Trận bị huỷ/hoãn -> hiện nhãn riêng thay vì giờ đá (tránh tưởng nhầm "sắp đá").
const off = computed(() => isOff(props.fixture.fixture.status.short))
const offLabel = computed(() => offStatusKey(props.fixture.fixture.status.short))
// Tỉ số luân lưu (nếu trận đá penalty) -> hiện số nhỏ cạnh tỉ số mỗi đội để biết ai thắng khi hoà.
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
    <!-- Cột trạng thái: LIVE + phút, hoặc FT, hoặc giờ đá -->
    <div class="match-card__status">
      <div v-if="showDate" class="mc-date">{{ matchDay(f.fixture.date) }}</div>
      <template v-if="live">
        <div class="live">● LIVE</div>
        <div>{{ f.fixture.status.elapsed }}{{ f.fixture.status.extra ? '+' + f.fixture.status.extra : '' }}'</div>
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

    <!-- Hai đội -->
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

    <!-- Tỉ số (ẩn nếu chưa đá) -->
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
