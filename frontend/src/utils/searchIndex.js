// Search index for LEAGUES + COUNTRIES for the search box next to the date strip.
// All filtering runs on the CLIENT over an array loaded once -> results appear instantly, no network calls.
import api from '../services/api'
import { COUNTRY_VI } from './countryNames'
import { LEAGUE_VI } from './leagueNames'

// Remove Vietnamese accents + lowercase (same as _norm_key in the backend) -> input with or without accents matches.
// e.g. 'tây ban nha' and 'tay ban nha' both become 'tay ban nha'.
export function norm(s) {
  return (s || '')
    .toLowerCase()
    .replace(/đ/g, 'd')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
}

// Popular competitions -> always ranked first when several results match equally.
const POPULAR = new Set([39, 140, 135, 78, 61, 2, 3, 848, 45, 143, 307, 253, 340, 1, 15, 10, 88, 94, 71, 128, 71, 197, 203])

let _promise = null
let _leagues = []
let _countries = []

function buildCountries(leagues) {
  const map = new Map() // key = norm(country name) -> {name, vi, flag, count}
  for (const l of leagues) {
    const c = l.country
    if (!c || norm(c) === 'world') continue
    const key = norm(c)
    if (!map.has(key)) {
      map.set(key, { name: c, vi: COUNTRY_VI[c] || c, flag: l.flag || null, count: 0 })
    }
    map.get(key).count++
  }
  return [...map.values()].sort((a, b) => a.name.localeCompare(b.name))
}

// Load the league list ONLY ONCE (module-level cache + 24h backend cache).
export async function ensureIndex() {
  if (_promise) return _promise
  _promise = api
    .get('/leagues/all')
    .then(({ data }) => {
      _leagues = (data.response || []).map((l) => ({
        ...l,
        _n: norm(l.name),
        _nvi: norm(LEAGUE_VI[l.id] || ''),
        _c: norm(l.country || ''),
        _cvi: norm(COUNTRY_VI[l.country] || ''),
        popular: POPULAR.has(l.id),
      }))
      _countries = buildCountries(_leagues).map((c) => ({
        ...c,
        _n: norm(c.name),
        _vi: norm(c.vi),
      }))
      return true
    })
    .catch(() => {
      _promise = null // allow retrying next time if there was a network error
      return false
    })
  return _promise
}

// All competitions in one country (matched by normalised country name). Used for the 'Domestic leagues' tab.
// Popular competitions first, the rest alphabetically.
export function leaguesByCountry(country) {
  const key = norm(country)
  return _leagues
    .filter((l) => l._c === key)
    .sort((a, b) => b.popular - a.popular || a._n.localeCompare(b._n))
}

// Match score: lower is better (0 = exact match, 99 = no match).
function scoreName(n, q) {
  if (!n) return 99
  if (n === q) return 0
  if (n.startsWith(q)) return 1
  if (n.includes(' ' + q)) return 2 // match the start of a word in the middle of the name
  if (n.includes(q)) return 3
  return 99
}

export function searchIndex(query, limit = 12) {
  const q = norm(query)
  if (!q) return { leagues: [], countries: [] }

  // Countries: match by English OR Vietnamese name.
  const countries = _countries
    .map((c) => ({ c, s: Math.min(scoreName(c._n, q), scoreName(c._vi, q)) }))
    .filter((x) => x.s < 99)
    .sort((a, b) => a.s - b.s || b.c.count - a.c.count)
    .slice(0, 6)
    .map((x) => x.c)

  // Leagues: match by LEAGUE NAME, or by COUNTRY NAME (EN/VI) -> typing 'Anh' (England) returns Premier League...
  // (+1 so a direct league-name match always ranks above an indirect match via country name.)
  const leagues = _leagues
    .map((l) => ({
      l,
      s: Math.min(scoreName(l._n, q), scoreName(l._nvi, q), scoreName(l._c, q) + 1, scoreName(l._cvi, q) + 1),
    }))
    .filter((x) => x.s < 99)
    .sort((a, b) => a.s - b.s || b.l.popular - a.l.popular || a.l._n.localeCompare(b.l._n))
    .slice(0, limit)
    .map((x) => x.l)

  return { leagues, countries }
}

// Find a NATIONAL TEAM from what the user typed (EN or VI) -> returns {name, vi} or null.
// Used to show the normalised/translated team name in the "A vs B" suggestion.
export function resolveCountry(term) {
  const q = norm(term)
  if (!q) return null
  let best = null
  let bestScore = 99
  for (const c of _countries) {
    const s = Math.min(scoreName(c._n, q), scoreName(c._vi, q))
    if (s < bestScore) { bestScore = s; best = c }
  }
  return bestScore < 99 ? best : null
}
