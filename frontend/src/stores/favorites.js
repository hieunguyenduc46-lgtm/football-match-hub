import { defineStore } from 'pinia'

// Safe localStorage read/write (wrapped in try/catch in case the browser blocks it).
function load(key) {
  try { return JSON.parse(localStorage.getItem(key) || '[]') } catch (e) { return [] }
}
function save(key, val) {
  try { localStorage.setItem(key, JSON.stringify(val)) } catch (e) { /* ignore */ }
}

// Store favourite teams + players on the device (localStorage).
// Can later sync to Supabase while keeping this same interface.
export const useFavoritesStore = defineStore('favorites', {
  state: () => ({
    teams: load('fav_teams'),
    players: load('fav_players'),
    leagues: load('fav_leagues'),   // followed leagues (separate localStorage key -> does not touch team/player)
    matches: load('fav_matches'),   // followed matches
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
    // League: store id + name + logo to show on the Following page (links straight to /league/:id).
    toggleLeague(league) {
      const i = this.leagues.findIndex((l) => l.id === league.id)
      if (i >= 0) this.leagues.splice(i, 1)
      else this.leagues.push({ id: league.id, name: league.name, logo: league.logo })
      save('fav_leagues', this.leagues)
    },
    // Match: store both teams + date + league name to show again (links straight to /match/:id).
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
