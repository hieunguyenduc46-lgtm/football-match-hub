// ===== Player statistics aggregation logic SHARED by every page =====
// Previously PlayerView and CompareView each aggregated differently -> inconsistent numbers
// (compare added national team + friendlies, the profile split club/national team and dropped friendlies).
// Everything is now in one place so both pages always calculate EXACTLY the same way.

// Remove accents, lowercase to compare the team name with nationality ("Pháp"/"France"...).
export function norm(s) {
  return (s || '').toLowerCase().normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').replace(/[^a-z]/g, '')
}

// NATIONAL TEAM competitions (catches cases where the team name != nationality, e.g. "Korea Republic").
// NOTE: uses \beuro(?!pa) so it does NOT match "Europa League" (a club cup).
export const INTL_LEAGUE = /world cup|nations league|friendl|\beuro(?!pa)|copa am|africa cup|afcon|asian cup|gold cup|olympic|qualification|qualifying|confederations cup/i

// CLUB competitions (continental cups + domestic cups): NEVER national team, even if the name contains
// "champions"/"concacaf"... (vd "CONCACAF Champions League", "UEFA Europa League",
// "CONMEBOL Libertadores" are clubs). This is the main source of confusion.
export const CLUB_LEAGUE = /club world cup|champions league|champions cup|europa|conference league|libertadores|sudamericana|recopa|leagues cup|super cup|intercontinental|fa cup|copa del rey|coppa|dfb|carabao|community shield|supercopa|supercoppa/i

export function isNational(s, nationality) {
  const team = s.team?.name || ''
  const league = s.league?.name || ''
  // Club cups (including "FIFA Club World Cup", "Club Friendlies", continental club cups...) -> NOT national team.
  if (/club/i.test(league) || CLUB_LEAGUE.test(league)) return false
  // Most reliable: the team name equals the player's nationality ("France", "Argentina").
  if (nationality && norm(team) === norm(nationality)) return true
  // Fallback: the competition name is in the national team group (catches cases where the team name differs from nationality).
  return INTL_LEAGUE.test(league)
}

// Friendlies (not counted in 'official' statistics).
export function isFriendly(s) {
  return /friendl/i.test(s.league?.name || '')
}

// Normalise pass accuracy % from the `passes.accuracy` field.
// API-Football: in the /players endpoint (whole season) this field is sometimes a percentage
// (<=100), sometimes the SUM of per-match percentages (>100) -> divide by the number of matches.
export function passPct(acc, apps) {
  if (acc == null || acc === '') return null
  const n = parseFloat(acc)
  if (isNaN(n)) return null
  return n <= 100 ? Math.round(n) : Math.round(n / Math.max(apps, 1))
}

// Normalise one statistics element -> one competition row.
export function mapEntry(s) {
  const r = parseFloat(s.games?.rating)
  const apps = s.games?.appearences || 0
  return {
    key: `${s.team?.id || ''}-${s.league?.id || s.league?.name || ''}`,
    league: s.league?.name || '—',
    logo: s.league?.logo,
    team: s.team?.name || '',
    goals: s.goals?.total || 0,
    assists: s.goals?.assists || 0,
    apps,
    minutes: s.games?.minutes ?? null,
    shots: s.shots?.total ?? null,
    passAcc: passPct(s.passes?.accuracy, apps),
    yellow: s.cards?.yellow || 0,
    red: s.cards?.red || 0,
    rating: r ? +r.toFixed(1) : null,
    position: s.games?.position,
  }
}

// Sum the rows -> a TOTAL row (rating & pass%: weighted average by appearances).
export function totalsOf(rows) {
  const sum = (k) => rows.reduce((t, r) => t + (r[k] || 0), 0)
  let rW = 0, rA = 0   // rating
  let pW = 0, pA = 0   // pass%
  for (const r of rows) {
    if (r.rating && r.apps) { rW += r.rating * r.apps; rA += r.apps }
    if (r.passAcc != null && r.apps) { pW += r.passAcc * r.apps; pA += r.apps }
  }
  return {
    goals: sum('goals'), assists: sum('assists'), apps: sum('apps'),
    minutes: sum('minutes'), shots: sum('shots'),
    yellow: sum('yellow'), red: sum('red'),
    passAcc: pA ? Math.round(pW / pA) : null,
    rating: rA ? +(rW / rA).toFixed(1) : null,
  }
}

// Split a player object ({ player, statistics }) into { club, national }
// (friendlies already removed). Used by the profile page to show two separate tables.
export function splitStats(p) {
  const arr = p?.statistics || []
  const nat = p?.player?.nationality
  const club = [], national = []
  for (const s of arr) {
    if (isFriendly(s)) continue            // remove friendlies from every table
    ;(isNational(s, nat) ? national : club).push(mapEntry(s))
  }
  const byApps = (a, b) => b.apps - a.apps
  return { club: club.sort(byApps), national: national.sort(byApps) }
}

// OFFICIAL total = club + national team, friendlies EXCLUDED. Used by the compare page
// so the number is consistent with the classification on the profile page.
export function aggregateOfficial(p) {
  const { club, national } = splitStats(p)
  const rows = [...club, ...national]
  if (!rows.length) return null
  return totalsOf(rows)
}
