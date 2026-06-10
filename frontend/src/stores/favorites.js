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
    leagues: load('fav_leagues'),   // giải đã follow (key localStorage riêng -> không đụng team/player)
    matches: load('fav_matches'),   // trận đã follow
  }),
  getters: {
    isTeamFav: (s) => (id) => s.teams.some((t) => t.id === id),
    isPlayerFav: (s) => (id) => s.players.some((p) => p.id === id),
    isLeagueFav: (s) => (id) => s.leagues.some((l) => l.id === id),
    isMatchFav: (s) => (id) => s.matches.some((m) => m.id === id),
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
    // Giải: lưu id + tên + logo để hiện lại ở trang Theo dõi (link thẳng vào /league/:id).
    toggleLeague(league) {
      const i = this.leagues.findIndex((l) => l.id === league.id)
      if (i >= 0) this.leagues.splice(i, 1)
      else this.leagues.push({ id: league.id, name: league.name, logo: league.logo })
      save('fav_leagues', this.leagues)
    },
    // Trận: lưu 2 đội + ngày + tên giải để hiện lại (link thẳng vào /match/:id).
    toggleMatch(match) {
      const i = this.matches.findIndex((m) => m.id === match.id)
      if (i >= 0) this.matches.splice(i, 1)
      else this.matches.push({
        id: match.id,
        home: { name: match.home?.name, logo: match.home?.logo },
        away: { name: match.away?.name, logo: match.away?.logo },
        date: match.date,
        league: match.league,
      })
      save('fav_matches', this.matches)
    },
  },
})
