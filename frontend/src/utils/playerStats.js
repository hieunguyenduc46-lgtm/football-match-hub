// ===== Logic gộp thống kê cầu thủ DÙNG CHUNG cho mọi trang =====
// Trước đây PlayerView và CompareView mỗi nơi tự gộp một kiểu -> số liệu lệch nhau
// (compare cộng cả ĐTQG + giao hữu, profile thì tách CLB/ĐTQG và bỏ giao hữu).
// Đưa hết về một chỗ để hai trang luôn tính GIỐNG HỆT nhau.

// Bỏ dấu, thường hoá để so tên đội với quốc tịch ("Pháp"/"France"...).
export function norm(s) {
  return (s || '').toLowerCase().normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').replace(/[^a-z]/g, '')
}

// Giải cấp ĐỘI TUYỂN (bắt cả khi tên đội != quốc tịch, vd "Korea Republic").
// LƯU Ý: dùng \beuro(?!pa) để KHÔNG dính "Europa League" (cúp CLB).
export const INTL_LEAGUE = /world cup|nations league|friendl|\beuro(?!pa)|copa am|africa cup|afcon|asian cup|gold cup|olympic|qualification|qualifying|confederations cup/i

// Giải cấp CLB (cúp châu lục + cúp QG) — KHÔNG bao giờ là ĐTQG, dù tên có
// "champions"/"concacaf"... (vd "CONCACAF Champions League", "UEFA Europa League",
// "CONMEBOL Libertadores" đều là CLB). Đây là nguồn gây nhầm lẫn chính.
export const CLUB_LEAGUE = /club world cup|champions league|champions cup|europa|conference league|libertadores|sudamericana|recopa|leagues cup|super cup|intercontinental|fa cup|copa del rey|coppa|dfb|carabao|community shield|supercopa|supercoppa/i

export function isNational(s, nationality) {
  const team = s.team?.name || ''
  const league = s.league?.name || ''
  // Cúp CLB (gồm "FIFA Club World Cup", "Club Friendlies", cúp châu lục CLB...) -> KHÔNG phải ĐTQG.
  if (/club/i.test(league) || CLUB_LEAGUE.test(league)) return false
  // Tin cậy nhất: tên đội trùng quốc tịch cầu thủ ("France", "Argentina").
  if (nationality && norm(team) === norm(nationality)) return true
  // Dự phòng: tên giải thuộc nhóm đội tuyển (bắt cả khi tên đội khác quốc tịch).
  return INTL_LEAGUE.test(league)
}

// Giao hữu (không tính vào thống kê "chính thức").
export function isFriendly(s) {
  return /friendl/i.test(s.league?.name || '')
}

// Chuẩn hoá % chuyền chính xác từ field `passes.accuracy`.
// API-Football: ở endpoint /players (gộp cả mùa) field này đôi khi là phần trăm
// (<=100), đôi khi là TỔNG CỘNG phần trăm các trận (>100) -> chia cho số trận.
export function passPct(acc, apps) {
  if (acc == null || acc === '') return null
  const n = parseFloat(acc)
  if (isNaN(n)) return null
  return n <= 100 ? Math.round(n) : Math.round(n / Math.max(apps, 1))
}

// Chuẩn hoá 1 phần tử statistics -> 1 dòng giải đấu.
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

// Cộng dồn các dòng -> dòng TỔNG (rating & pass%: trung bình có trọng số theo số trận).
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

// Tách 1 object cầu thủ ({ player, statistics }) thành { club, national }
// (đã bỏ giao hữu). Dùng cho trang hồ sơ hiển thị 2 bảng riêng.
export function splitStats(p) {
  const arr = p?.statistics || []
  const nat = p?.player?.nationality
  const club = [], national = []
  for (const s of arr) {
    if (isFriendly(s)) continue            // bỏ giao hữu khỏi mọi bảng
    ;(isNational(s, nat) ? national : club).push(mapEntry(s))
  }
  const byApps = (a, b) => b.apps - a.apps
  return { club: club.sort(byApps), national: national.sort(byApps) }
}

// Tổng CHÍNH THỨC = CLB + ĐTQG, ĐÃ loại giao hữu. Dùng cho trang so sánh
// để con số nhất quán với cách phân loại ở trang hồ sơ.
export function aggregateOfficial(p) {
  const { club, national } = splitStats(p)
  const rows = [...club, ...national]
  if (!rows.length) return null
  return totalsOf(rows)
}
