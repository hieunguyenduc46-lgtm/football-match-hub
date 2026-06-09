// Chỉ mục tìm kiếm GIẢI + QUỐC GIA cho ô search cạnh thanh ngày.
// Toàn bộ việc lọc chạy ở CLIENT trên mảng đã tải sẵn 1 lần -> gõ là ra ngay, không gọi mạng.
import api from '../services/api'
import { COUNTRY_VI } from './countryNames'
import { LEAGUE_VI } from './leagueNames'

// Bỏ dấu tiếng Việt + thường hoá (giống _norm_key ở backend) -> gõ có dấu/không dấu đều khớp.
// vd 'tây ban nha' và 'tay ban nha' đều thành 'tay ban nha'.
export function norm(s) {
  return (s || '')
    .toLowerCase()
    .replace(/đ/g, 'd')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
}

// Giải phổ biến -> luôn xếp lên đầu khi nhiều kết quả cùng độ khớp.
const POPULAR = new Set([39, 140, 135, 78, 61, 2, 3, 848, 45, 143, 307, 253, 340, 1, 15, 10, 88, 94, 71, 128, 71, 197, 203])

let _promise = null
let _leagues = []
let _countries = []

function buildCountries(leagues) {
  const map = new Map() // key = norm(tên nước) -> {name, vi, flag, count}
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

// Tải danh sách giải 1 LẦN duy nhất (cache ở module-level + backend cache 24h).
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
      _promise = null // cho phép thử lại lần sau nếu lỗi mạng
      return false
    })
  return _promise
}

// Mọi giải thuộc 1 quốc gia (khớp tên nước đã chuẩn hoá). Dùng cho tab 'Giải trong nước'.
// Giải phổ biến lên trước, còn lại theo bảng chữ cái.
export function leaguesByCountry(country) {
  const key = norm(country)
  return _leagues
    .filter((l) => l._c === key)
    .sort((a, b) => b.popular - a.popular || a._n.localeCompare(b._n))
}

// Điểm khớp: càng nhỏ càng khớp tốt (0 = trùng khít, 99 = không khớp).
function scoreName(n, q) {
  if (!n) return 99
  if (n === q) return 0
  if (n.startsWith(q)) return 1
  if (n.includes(' ' + q)) return 2 // khớp đầu một từ giữa câu
  if (n.includes(q)) return 3
  return 99
}

export function searchIndex(query, limit = 12) {
  const q = norm(query)
  if (!q) return { leagues: [], countries: [] }

  // Quốc gia: khớp theo tên tiếng Anh HOẶC tiếng Việt.
  const countries = _countries
    .map((c) => ({ c, s: Math.min(scoreName(c._n, q), scoreName(c._vi, q)) }))
    .filter((x) => x.s < 99)
    .sort((a, b) => a.s - b.s || b.c.count - a.c.count)
    .slice(0, 6)
    .map((x) => x.c)

  // Giải: khớp theo TÊN GIẢI, hoặc theo TÊN NƯỚC (EN/VI) -> gõ 'Anh' ra Premier League...
  // (+1 để tên giải khớp trực tiếp luôn được ưu tiên hơn khớp gián tiếp qua tên nước.)
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

// Tìm 1 ĐỘI TUYỂN QUỐC GIA theo tên người dùng gõ (EN hoặc VI) -> trả {name, vi} hoặc null.
// Dùng để hiển thị tên đội đã chuẩn hoá/đã dịch trong gợi ý "A vs B".
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
