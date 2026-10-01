import { state } from '../i18n'

// API-Football status groups
export const LIVE_STATUSES = ['1H', '2H', 'HT', 'ET', 'BT', 'P', 'LIVE']
// WO=walkover, AWD=awarded: unusual, but there IS a result/score -> counted as 'finished'.
export const FINISHED_STATUSES = ['FT', 'AET', 'PEN', 'WO', 'AWD']

// Map the app locale -> BCP-47 code for Intl. Reads state.locale (reactive)
// so when the language changes, templates calling these functions re-render automatically.
function localeTag() {
  return state.locale === 'en' ? 'en-GB' : 'vi-VN'
}

// Matches NOT played as scheduled (API-Football) with NO normal result:
//   PST=postponed, SUSP=suspended, INT=interrupted, TBD=time to be defined  -> 'postponed' group
//   CANC=cancelled, ABD=abandoned                                        -> 'cancelled' group
export const POSTPONED_STATUSES = ['PST', 'SUSP', 'INT', 'TBD']
export const CANCELLED_STATUSES = ['CANC', 'ABD']

export function isLive(short) {
  return LIVE_STATUSES.includes(short)
}

// BREAK statuses between phases (players NOT playing): HT=half-time, BT=break before extra time,
// P=penalty shoot-out. For these statuses show a LABEL instead of the minute (45+6') so it is not mistaken
// for live play. Other live statuses (1H/2H/ET) still show the minute as before.
export const BREAK_STATUSES = ['HT', 'BT', 'P']
export function isBreak(short) {
  return BREAK_STATUSES.includes(short)
}
// i18n key for each kind of break.
export function breakStatusKey(short) {
  if (short === 'HT') return 'halftime'
  if (short === 'BT') return 'breakTime'
  return 'penalties' // P
}
export function isFinished(short) {
  return FINISHED_STATUSES.includes(short)
}
export function isPostponed(short) {
  return POSTPONED_STATUSES.includes(short)
}
export function isCancelled(short) {
  return CANCELLED_STATUSES.includes(short)
}
// Cancelled/postponed match (not played as scheduled) -> must NOT show 'Not started'.
export function isOff(short) {
  return isPostponed(short) || isCancelled(short)
}
// i18n key for the 'not played' status label: 'cancelled' or 'postponed'.
export function offStatusKey(short) {
  return isCancelled(short) ? 'cancelled' : 'postponed'
}

// ===== "LIVE treo" (stale live) =====
// API-Football sometimes leaves a match stuck in a live status (e.g. '2H 82'') for HOURS because the
// data feed for lower-league matches stops updating (never moves to FT). If we relied only on
// status, the app would wrongly show "LIVE 82'" and keep polling the API forever -> wasted quota.
// How to detect it: compare the ACTUAL minutes since kick-off with a reasonable maximum for each phase.
// The second half realistically ends within ~2h of kick-off; extra time/penalties get more slack.
const STALE_LIMIT_MIN = { '1H': 75, 'HT': 95, '2H': 150, 'ET': 210, 'BT': 210, 'P': 220, 'LIVE': 220 }

export function isStaleLive(fx) {
  const s = fx?.fixture?.status?.short
  if (!isLive(s)) return false
  const ts = fx?.fixture?.timestamp ?? (fx?.fixture?.date ? Date.parse(fx.fixture.date) / 1000 : null)
  if (!ts || Number.isNaN(ts)) return false
  const mins = (Date.now() / 1000 - ts) / 60
  return mins > (STALE_LIMIT_MIN[s] ?? 200)
}

// 'REALLY live' = live status AND not stuck-live. Used wherever we need to know whether the match is
// actually in progress (show the LIVE badge, decide whether to keep polling, sort order).
export function isLiveFixture(fx) {
  return isLive(fx?.fixture?.status?.short) && !isStaleLive(fx)
}

// Time shown in the user's device timezone (Phase 5 will allow choosing a timezone).
export function matchTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString(localeTag(), { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

export function matchDay(iso) {
  try {
    return new Date(iso).toLocaleDateString(localeTag(), { day: '2-digit', month: 'short' })
  } catch {
    return ''
  }
}

// Like matchDay but WITH THE YEAR (e.g. "11 Dec 2022"). Used on the match detail page to show
// which year/edition the match belongs to (important for the World Cup and older competitions...).
export function matchDayYear(iso) {
  try {
    return new Date(iso).toLocaleDateString(localeTag(), { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return ''
  }
}

// API-Football LINE-UP data does NOT include a 'photo' for players (only id, name,
// number, pos, grid). So we build the photo URL from the id using API-Football's CDN.
// (If the object already has a 'photo' from another endpoint, use that first.)
export function playerPhoto(p) {
  if (p?.photo) return p.photo
  return p?.id ? `https://media.api-sports.io/football/players/${p.id}.png` : ''
}

// Broken image -> replace with a placeholder so the layout does not break.
export function imgFallback(e) {
  e.target.src =
    'data:image/svg+xml;utf8,' +
    encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect width="40" height="40" rx="8" fill="#1c232d"/><text x="50%" y="55%" font-size="16" fill="#8b949e" text-anchor="middle">?</text></svg>'
    )
}
