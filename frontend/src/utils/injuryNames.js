// Dịch loại chấn thương / lý do vắng mặt (API-Football trả tiếng Anh) sang tiếng Việt.
// Khoá theo chuỗi gốc viết thường. Không có trong bảng -> giữ nguyên (an toàn, không bịa).
import { state } from '../i18n'

const INJURY_VI = {
  // Lý do chung
  'injury': 'Chấn thương',
  'knock': 'Va chạm',
  'illness': 'Ốm',
  'virus': 'Nhiễm virus',
  'wound': 'Vết thương',
  'fitness': 'Thể lực',
  'rest': 'Nghỉ dưỡng sức',
  'concussion': 'Chấn động não',
  'fracture': 'Gãy xương',
  'broken bone': 'Gãy xương',
  // Theo bộ phận
  'knee injury': 'Chấn thương đầu gối',
  'muscle injury': 'Chấn thương cơ',
  'hamstring injury': 'Chấn thương gân kheo',
  'thigh injury': 'Chấn thương đùi',
  'hip/thigh injury': 'Chấn thương hông/đùi',
  'calf/shin injury': 'Chấn thương bắp chân/ống đồng',
  'calf injury': 'Chấn thương bắp chân',
  'groin injury': 'Chấn thương háng',
  'ankle/foot injury': 'Chấn thương cổ chân/bàn chân',
  'ankle injury': 'Chấn thương cổ chân',
  'foot injury': 'Chấn thương bàn chân',
  'toe injury': 'Chấn thương ngón chân',
  'back injury': 'Chấn thương lưng',
  'shoulder injury': 'Chấn thương vai',
  'head injury': 'Chấn thương đầu',
  'achilles tendon injury': 'Chấn thương gân Achilles',
  'cruciate ligament injury': 'Đứt dây chằng chéo',
  'adductor problems': 'Chấn thương cơ khép',
  // Treo giò / vắng mặt
  'suspended': 'Treo giò',
  'yellow cards': 'Treo giò (thẻ vàng)',
  'red card': 'Treo giò (thẻ đỏ)',
  'coach decision': 'Quyết định của HLV',
  "coach's decision": 'Quyết định của HLV',
  'national selection': 'Tập trung đội tuyển',
  'personal reasons': 'Lý do cá nhân',
  // type (trạng thái)
  'missing fixture': 'Vắng mặt',
  'questionable': 'Chưa chắc chắn',
  'injured': 'Đang chấn thương',
  'inactive': 'Không trong đội hình',
  'doubtful': 'Chưa chắc ra sân',
}

export function injuryName(str) {
  if (!str) return str
  if (state.locale !== 'vi') return str
  return INJURY_VI[String(str).trim().toLowerCase()] || str
}
