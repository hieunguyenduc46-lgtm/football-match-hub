// Dịch loại chấn thương / lý do vắng mặt (API-Football trả tiếng Anh) sang tiếng Việt.
// 3 lớp: (1) bảng dịch chính xác, (2) bộ phận cơ thể đứng một mình -> "Chấn thương <bp>",
// (3) mẫu "<bp> Injury" / "Broken <bp>" / "<bp> Surgery". Không khớp -> giữ nguyên (an toàn).
import { state } from '../i18n'

// Bộ phận cơ thể (khoá viết thường)
const PART_VI = {
  knee: 'đầu gối', ankle: 'cổ chân', foot: 'bàn chân', 'ankle/foot': 'cổ chân/bàn chân',
  thigh: 'đùi', hip: 'hông', 'hip/thigh': 'hông/đùi', hamstring: 'gân kheo',
  calf: 'bắp chân', shin: 'ống đồng', 'calf/shin': 'bắp chân/ống đồng',
  groin: 'háng', pelvis: 'xương chậu', 'groin/pelvis': 'háng/xương chậu',
  back: 'lưng', shoulder: 'vai', muscle: 'cơ', muscular: 'cơ',
  head: 'đầu', face: 'mặt', mouth: 'miệng', eye: 'mắt', nose: 'mũi', jaw: 'hàm',
  rib: 'xương sườn', chest: 'ngực', abdominal: 'bụng', abdomen: 'bụng', stomach: 'bụng',
  toe: 'ngón chân', finger: 'ngón tay', thumb: 'ngón cái', hand: 'bàn tay',
  wrist: 'cổ tay', elbow: 'khuỷu tay', neck: 'cổ', heel: 'gót chân',
  leg: 'chân', arm: 'cánh tay', tooth: 'răng', teeth: 'răng', collarbone: 'xương đòn',
  quadriceps: 'cơ tứ đầu', adductor: 'cơ khép', achilles: 'gân Achilles',
  'achilles tendon': 'gân Achilles', tendon: 'gân', ligament: 'dây chằng',
  'cruciate ligament': 'dây chằng chéo', 'knee ligament': 'dây chằng gối',
  meniscus: 'sụn chêm', cartilage: 'sụn', 'hip flexor': 'cơ gấp hông',
}

// Dịch chính xác (không theo mẫu bộ phận)
const INJURY_VI = {
  injury: 'Chấn thương', knock: 'Va chạm', illness: 'Ốm', sick: 'Ốm',
  virus: 'Nhiễm virus', flu: 'Cúm', fever: 'Sốt', infection: 'Nhiễm trùng',
  coronavirus: 'Covid-19', 'covid-19': 'Covid-19', covid: 'Covid-19',
  wound: 'Vết thương', bruise: 'Bầm tím', cut: 'Vết cắt', blister: 'Phồng rộp',
  concussion: 'Chấn động não', fracture: 'Gãy xương', 'broken bone': 'Gãy xương',
  surgery: 'Phẫu thuật', disease: 'Bệnh lý', 'bowel disease': 'Bệnh đường ruột',
  'heart problems': 'Vấn đề tim mạch', 'muscular problems': 'Vấn đề cơ bắp',
  'muscle injury': 'Chấn thương cơ', 'hamstring': 'Chấn thương gân kheo',
  fitness: 'Thể lực', 'lack of fitness': 'Chưa đủ thể lực', rest: 'Nghỉ dưỡng sức',
  unknown: 'Không rõ', 'knee surgery': 'Phẫu thuật đầu gối',
  // treo giò / vắng mặt
  suspended: 'Treo giò', 'red card': 'Treo giò (thẻ đỏ)', 'yellow cards': 'Treo giò (thẻ vàng)',
  'coach decision': 'Quyết định của HLV', "coach's decision": 'Quyết định của HLV',
  'national selection': 'Tập trung đội tuyển', 'personal reasons': 'Lý do cá nhân',
  'personal problems': 'Vấn đề cá nhân', 'contract issues': 'Vấn đề hợp đồng',
  doping: 'Doping',
  // type (trạng thái)
  'missing fixture': 'Vắng mặt', questionable: 'Chưa chắc chắn', doubtful: 'Chưa chắc ra sân',
  injured: 'Đang chấn thương', inactive: 'Không trong đội hình', out: 'Vắng mặt',
}

export function injuryName(str) {
  if (!str) return str
  if (state.locale !== 'vi') return str
  const s = String(str).trim()
  const low = s.toLowerCase()
  // 1) khớp chính xác
  if (INJURY_VI[low]) return INJURY_VI[low]
  // 2) bộ phận đứng một mình (vd "Hamstring", "Calf") -> "Chấn thương <bp>"
  if (PART_VI[low]) return 'Chấn thương ' + PART_VI[low]
  // 3) các mẫu
  if (low.endsWith(' injury')) {
    const part = low.slice(0, -7).trim()
    return 'Chấn thương ' + (PART_VI[part] || part)
  }
  if (low.startsWith('broken ')) {
    const part = low.slice(7).trim()
    return 'Gãy ' + (PART_VI[part] || part)
  }
  if (low.endsWith(' surgery')) {
    const part = low.slice(0, -8).trim()
    return 'Phẫu thuật ' + (PART_VI[part] || part)
  }
  if (low.endsWith(' problems')) {
    const part = low.slice(0, -9).trim()
    return 'Vấn đề ' + (PART_VI[part] || part)
  }
  if (low.endsWith(' disease')) {
    const part = low.slice(0, -8).trim()
    return 'Bệnh ' + (PART_VI[part] || part)
  }
  // 4) không khớp -> giữ nguyên (không bịa)
  return s
}
