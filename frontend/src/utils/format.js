// Các nhóm trạng thái của API-Football
export const LIVE_STATUSES = ['1H', '2H', 'HT', 'ET', 'BT', 'P', 'LIVE']
export const FINISHED_STATUSES = ['FT', 'AET', 'PEN']

export function isLive(short) {
  return LIVE_STATUSES.includes(short)
}
export function isFinished(short) {
  return FINISHED_STATUSES.includes(short)
}

// Giờ hiển thị theo múi giờ máy người dùng (Phase 5 sẽ cho chọn timezone).
export function matchTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

export function matchDay(iso) {
  try {
    return new Date(iso).toLocaleDateString([], { day: '2-digit', month: 'short' })
  } catch {
    return ''
  }
}

// Ảnh lỗi -> thay bằng placeholder để không vỡ layout.
export function imgFallback(e) {
  e.target.src =
    'data:image/svg+xml;utf8,' +
    encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect width="40" height="40" rx="8" fill="#1c232d"/><text x="50%" y="55%" font-size="16" fill="#8b949e" text-anchor="middle">?</text></svg>'
    )
}
