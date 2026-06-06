import { defineStore } from 'pinia'
import api from '../services/api'

// Store giữ danh sách trận + trạng thái loading/error.
// Logic: gọi backend 1 lần, rồi lọc theo tab ở phía giao diện (HomeView).
export const useFixturesStore = defineStore('fixtures', {
  state: () => ({
    fixtures: [],
    loading: false,
    error: null,
    _seq: 0,            // chống race: chỉ nhận kết quả của lần gọi mới nhất
  }),
  actions: {
    // opts.silent = true: làm mới ngầm (auto-refresh) không hiện skeleton.
    async fetchFixtures(params = {}, opts = {}) {
      const seq = ++this._seq
      if (!opts.silent) this.loading = true
      this.error = null
      try {
        const { data } = await api.get('/fixtures', { params })
        if (seq !== this._seq) return        // đã đổi ngày/giải -> bỏ kết quả cũ
        this.fixtures = data.response || []
      } catch (e) {
        if (seq !== this._seq) return
        this.error = e?.message || 'Không tải được dữ liệu trận đấu'
        if (!opts.silent) this.fixtures = []
      } finally {
        if (seq === this._seq && !opts.silent) this.loading = false
      }
    },
  },
})
