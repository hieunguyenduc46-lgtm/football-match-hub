// Tên giải đấu -> tên thường gọi trong tiếng Việt.
// Khoá theo ID GIẢI (không phải tên) vì nhiều nước có giải trùng tên "Premier League"
// (Anh, Lebanon, Ukraine, Wales...) -> nếu dịch theo tên sẽ đổi nhầm tất cả.
// Chỉ dịch các giải có tên Việt phổ biến; giải không có trong bảng -> giữ nguyên tên gốc.
// Các giải VĐQG lớn (La Liga, Serie A, Bundesliga, Ligue 1...) cố ý GIỮ NGUYÊN.
import { state } from '../i18n'

export const LEAGUE_VI = {
  // Anh
  39: 'Ngoại Hạng Anh',
  45: 'Cúp FA',
  48: 'Cúp Liên đoàn Anh',
  528: 'Siêu cúp Anh',
  // Cúp châu Âu
  2: 'Champions League (Cúp C1)',
  3: 'Europa League (Cúp C2)',
  848: 'Conference League (Cúp C3)',
  531: 'Siêu cúp châu Âu',
  5: 'UEFA Nations League',
  // Cúp QG các nước lớn
  143: 'Cúp Nhà vua Tây Ban Nha',
  556: 'Siêu cúp Tây Ban Nha',
  137: 'Cúp Quốc gia Ý',
  81: 'Cúp Quốc gia Đức',
  66: 'Cúp Quốc gia Pháp',
  // Đội tuyển / quốc tế
  4: 'Vô địch châu Âu (EURO)',
  7: 'Cúp bóng đá châu Á',
  10: 'Giao hữu',
  667: 'Giao hữu CLB',
  // Khác
  307: 'Giải VĐQG Ả Rập Xê Út',
  253: 'Nhà nghề Mỹ (MLS)',
  340: 'V-League 1',
}

// Trả tên giải theo ngôn ngữ hiện tại. Cần truyền id để tra chính xác.
// locale 'en' hoặc id không có trong bảng -> giữ nguyên tên gốc.
export function leagueName(name, id) {
  if (state.locale !== 'vi') return name
  if (id != null && LEAGUE_VI[id]) return LEAGUE_VI[id]
  return name
}
