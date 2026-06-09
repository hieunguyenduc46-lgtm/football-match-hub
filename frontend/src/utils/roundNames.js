// Nhãn vòng đấu / giai đoạn cho từng trận.
// Dịch chuỗi `league.round` của API-Football sang tiếng Việt / tiếng Anh.
//   vd "Quarter-finals"   -> "Tứ kết" / "Quarter-finals"
//      "Group Stage - 1"  -> "Vòng bảng · lượt 1" / "Group stage · MD 1"
//      "Regular Season - 38" -> "Vòng 38" / "Round 38"
// Đọc state.locale (reactive) nên gọi trong template sẽ tự dịch lại khi đổi ngôn ngữ.
import { state } from '../i18n'

const DICT = {
  vi: {
    final: 'Chung kết',
    third: 'Tranh hạng ba',
    semi: 'Bán kết',
    quarter: 'Tứ kết',
    r16: 'Vòng 1/8',
    r32: 'Vòng 1/16',
    r64: 'Vòng 1/32',
    group: 'Vòng bảng',
    round: 'Vòng',
    matchday: 'lượt',
    playoff: 'Play-off',
    knockoutPlayoff: 'Play-off vòng loại trực tiếp',
    qualifying: 'Vòng loại',
    preliminary: 'Vòng sơ loại',
    relegation: 'Play-off trụ hạng',
  },
  en: {
    final: 'Final',
    third: '3rd place',
    semi: 'Semi-finals',
    quarter: 'Quarter-finals',
    r16: 'Round of 16',
    r32: 'Round of 32',
    r64: 'Round of 64',
    group: 'Group stage',
    round: 'Round',
    matchday: 'MD',
    playoff: 'Play-offs',
    knockoutPlayoff: 'Knockout play-offs',
    qualifying: 'Qualifying',
    preliminary: 'Preliminary round',
    relegation: 'Relegation play-off',
  },
}

export function roundLabel(round) {
  if (!round) return ''
  const D = DICT[state.locale === 'en' ? 'en' : 'vi']
  const r = String(round).toLowerCase().trim()
  const numMatch = r.match(/(\d+)\s*$/)          // số ở CUỐI chuỗi (vd "- 38", "- 1")
  const num = numMatch ? numMatch[1] : ''

  // THỨ TỰ kiểm tra rất quan trọng: "semi-finals"/"quarter-finals"/"3rd place final" đều
  // chứa chữ "final" -> phải xét các vòng cụ thể TRƯỚC, để "final" trơ trọi mới ra Chung kết.
  if (/3rd place|third place/.test(r)) return D.third
  if (/semi/.test(r)) return D.semi
  if (/quarter/.test(r)) return D.quarter
  if (/round of 16|1\/8/.test(r)) return D.r16
  if (/round of 32|1\/16/.test(r)) return D.r32
  if (/round of 64|1\/32/.test(r)) return D.r64
  if (/knockout round play|knockout play/.test(r)) return D.knockoutPlayoff
  if (/\bfinal\b/.test(r)) return D.final
  if (/preliminary/.test(r)) return D.preliminary
  if (/qualif/.test(r)) return num ? `${D.qualifying} ${num}` : D.qualifying
  if (/relegation/.test(r)) return D.relegation
  if (/group/.test(r)) {
    // "Group A" -> Vòng bảng A ; "Group Stage - 1" -> Vòng bảng · lượt 1
    const letter = r.match(/group\s+([a-z])\b/)
    if (letter) return `${D.group} ${letter[1].toUpperCase()}`
    return num ? `${D.group} · ${D.matchday} ${num}` : D.group
  }
  // VĐQG / League Stage: "Regular Season - 38", "League Stage - 1" -> Vòng 38 / Round 1
  if (/regular season|league stage|^round\b|matchday|round - /.test(r)) {
    return num ? `${D.round} ${num}` : round
  }
  if (/play-?\s?off/.test(r)) return D.playoff
  return round   // không khớp mẫu nào -> trả NGUYÊN VĂN (không bao giờ làm mất chữ)
}
