import { defineStore } from 'pinia'

// Đọc/ghi localStorage an toàn (bọc try/catch phòng trình duyệt chặn).
function load(key) {
  try { return JSON.parse(localStorage.getItem(key) || '[]') } catch (e) { return [] }
}
function save(key, val) {
  try { localStorage.setItem(key, JSON.stringify(val)) } catch (e) { /* bỏ qua */ }
}

// Lưu đội + cầu thủ yêu thích ngay trên máy (localStorage).
// Phase sau có thể đồng bộ lên Supabase mà giữ nguyên interface này.
export const useFavoritesStore = defineStore('favorites', {
  state: () => ({
    teams: load('fav_teams'),
    players: load('fav_players'),
  }),
  getters: {
    isTeamFav: (s) => (id) => s.teams.some((t) => t.id === id),
    isPlayerFav: (s) => (id) => s.players.some((p) => p.id === id),
  },
  actions: {
    toggleTeam(team) {
      const i = this.teams.findIndex((t) => t.id === team.id)
      if (i >= 0) this.teams.splice(i, 1)
      else this.teams.push({ id: team.id, name: team.name, logo: team.logo })
      save('fav_teams', this.teams)
    },
    togglePlayer(player) {
      const i = this.players.findIndex((p) => p.id === player.id)
      if (i >= 0) this.players.splice(i, 1)
      else this.players.push({ id: player.id, name: player.name, photo: player.photo })
      save('fav_players', this.players)
    },
  },
})
