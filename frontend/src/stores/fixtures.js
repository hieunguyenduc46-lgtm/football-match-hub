import { defineStore } from 'pinia'
import api from '../services/api'
import { t } from '../i18n'

// Store holding the fixture list + loading/error state.
// Logic: call the backend once, then filter by tab on the UI side (HomeView).
export const useFixturesStore = defineStore('fixtures', {
  state: () => ({
    fixtures: [],
    loading: false,
    error: null,
    _seq: 0,            // prevent race conditions: only accept results from the latest call
  }),
  actions: {
    // opts.silent = true: background refresh (auto-refresh) without showing the skeleton.
    async fetchFixtures(params = {}, opts = {}) {
      const seq = ++this._seq
      if (!opts.silent) this.loading = true
      this.error = null
      try {
        const { data } = await api.get('/fixtures', { params })
        if (seq !== this._seq) return        // date/league changed -> discard old results
        this.fixtures = data.response || []
      } catch (e) {
        if (seq !== this._seq) return
        this.error = e?.message || t('loadFixturesErr')
        if (!opts.silent) this.fixtures = []
      } finally {
        if (seq === this._seq && !opts.silent) this.loading = false
      }
    },
  },
})
