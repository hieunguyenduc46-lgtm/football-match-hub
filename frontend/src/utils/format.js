import { state } from '../i18n'

// Các nhóm trạng thái của API-Football
export const LIVE_STATUSES = ['1H', '2H', 'HT', 'ET', 'BT', 'P', 'LIVE']
// WO=walkover, AWD=xử thắng: tuy bất thường nhưng ĐÃ CÓ kết quả/tỉ số -> tính là "đã xong".
export const FINISHED_STATUSES = ['FT', 'AET', 'PEN', 'WO', 'AWD']

// Map locale của app -> mã BCP-47 cho Intl. Đọc state.locale (reactive)
// nên khi đổi ngôn ngữ, template gọi các hàm này sẽ tự re-render.
function localeTag() {
  return state.locale === 'en' ? 'en-GB' : 'vi-VN'
}

// Trận KHÔNG diễn ra theo lịch (API-Football), KHÔNG có kết quả bình thường:
//   PST=hoãn, SUSP=tạm dừng, INT=gián đoạn, TBD=chưa định giờ  -> nhóm "hoãn"
//   CANC=huỷ, ABD=bỏ dở                                        -> nhóm "huỷ"
export const POSTPONED_STATUSES = ['PST', 'SUSP', 'INT', 'TBD']
export const CANCELLED_STATUSES = ['CANC', 'ABD']

export function isLive(short) {
  return LIVE_STATUSES.includes(short)
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
// Trận bị huỷ/hoãn (không đá đúng lịch) -> KHÔNG được hiện "Chưa đá".
export function isOff(short) {
  return isPostponed(short) || isCancelled(short)
}
// Khoá i18n cho nhãn trạng thái "không đá": 'cancelled' hoặc 'postponed'.
export function offStatusKey(short) {
  return isCancelled(short) ? 'cancelled' : 'postponed'
}

// ===== "LIVE treo" (stale live) =====
// API-Football đôi khi để 1 trận kẹt ở trạng thái đang đá (vd '2H 82'') hàng GIỜ vì feed
// dữ liệu của trận hạng thấp ngừng cập nhật (không bao giờ chuyển sang FT). Nếu chỉ dựa vào
// status thì app hiện "LIVE 82'" sai và poll API mãi không ngừng -> phí quota.
// Cách nhận biết: so SỐ PHÚT THỰC TẾ kể từ giờ bóng lăn với mức tối đa hợp lý của từng pha.
// Hiệp 2 thực tế kết thúc trong ~2h từ kickoff; hiệp phụ/luân lưu thì rộng tay hơn.
const STALE_LIMIT_MIN = { '1H': 75, 'HT': 95, '2H': 150, 'ET': 210, 'BT': 210, 'P': 220, 'LIVE': 220 }

export function isStaleLive(fx) {
  const s = fx?.fixture?.status?.short
  if (!isLive(s)) return false
  const ts = fx?.fixture?.timestamp ?? (fx?.fixture?.date ? Date.parse(fx.fixture.date) / 1000 : null)
  if (!ts || Number.isNaN(ts)) return false
  const mins = (Date.now() / 1000 - ts) / 60
  return mins > (STALE_LIMIT_MIN[s] ?? 200)
}

// "Đang đá THẬT" = status live VÀ không phải live treo. Dùng ở mọi nơi cần biết trận có
// thực sự đang diễn ra (hiện badge LIVE, quyết định có poll tiếp không, xếp thứ tự).
export function isLiveFixture(fx) {
  return isLive(fx?.fixture?.status?.short) && !isStaleLive(fx)
}

// Giờ hiển thị theo múi giờ máy người dùng (Phase 5 sẽ cho chọn timezone).
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

// Như matchDay nhưng KÈM NĂM (vd "11 thg 12, 2022"). Dùng ở trang chi tiết trận để biết
// trận thuộc năm/kỳ giải nào (quan trọng với World Cup, các giải cũ...).
export function matchDayYear(iso) {
  try {
    return new Date(iso).toLocaleDateString(localeTag(), { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return ''
  }
}

// Dữ liệu ĐỘI HÌNH của API-Football KHÔNG kèm 'photo' cho cầu thủ (chỉ có id, name,
// number, pos, grid). Vì vậy tự dựng URL ảnh từ id theo đúng CDN của API-Football.
// (Nếu object đã có sẵn 'photo' từ endpoint khác thì ưu tiên dùng luôn.)
export function playerPhoto(p) {
  if (p?.photo) return p.photo
  return p?.id ? `https://media.api-sports.io/football/players/${p.id}.png` : ''
}

// Ảnh lỗi -> thay bằng placeholder để không vỡ layout.
export function imgFallback(e) {
  e.target.src =
    'data:image/svg+xml;utf8,' +
    encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect width="40" height="40" rx="8" fill="#1c232d"/><text x="50%" y="55%" font-size="16" fill="#8b949e" text-anchor="middle">?</text></svg>'
    )
}
