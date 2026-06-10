// Đặt tiêu đề tab trình duyệt. Giúp tab/bookmark/lịch sử hiển thị đúng nội dung,
// và tốt hơn khi người dùng mở nhiều tab. (Preview khi share link dùng OG tags ở index.html.)
const SUFFIX = 'Football Match Hub'

export function setTitle(name) {
  document.title = name ? `${name} · ${SUFFIX}` : SUFFIX
}
