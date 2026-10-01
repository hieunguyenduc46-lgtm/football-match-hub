// Round / stage label for each match.
// Translate API-Football's `league.round` string into Vietnamese / English.
//   e.g. "Quarter-finals"   -> "Tứ kết" / "Quarter-finals"
//      "Group Stage - 1"  -> "Vòng bảng · lượt 1" / "Group stage · MD 1"
//      "Regular Season - 38" -> "Vòng 38" / "Round 38"
// Reads state.locale (reactive), so calling it in a template re-translates when the language changes.
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
  // Friendlies: the API returns round = "Friendly International" / "Club Friendlies" -> same as the
  // competition name ("Friendlies") and in English -> hidden so the header does not repeat or mix languages.
  if (/friendl/.test(r)) return ''
  const numMatch = r.match(/(\d+)\s*$/)          // number at the END of the string (e.g. "- 38", "- 1")
  const num = numMatch ? numMatch[1] : ''

  // The ORDER of checks matters: "semi-finals"/"quarter-finals"/"3rd place final" all
  // contain the word "final" -> check the specific rounds FIRST, so only a bare "final" becomes the Final.
  if (/3rd place|third place/.test(r)) return D.third
  if (/semi/.test(r)) return D.semi
  if (/quarter/.test(r)) return D.quarter
  if (/round of 16|1\/8|8th final/.test(r)) return D.r16
  if (/round of 32|1\/16|16th final/.test(r)) return D.r32
  if (/round of 64|1\/32|32nd final/.test(r)) return D.r64
  if (/knockout round play|knockout play/.test(r)) return D.knockoutPlayoff
  if (/\bfinal\b/.test(r)) return D.final
  if (/preliminary/.test(r)) return D.preliminary
  if (/qualif/.test(r)) return num ? `${D.qualifying} ${num}` : D.qualifying
  if (/relegation/.test(r)) return D.relegation
  if (/group/.test(r)) {
    // "Group A" -> Group A ; "Group Stage - 1" -> Group stage · MD 1
    const letter = r.match(/group\s+([a-z])\b/)
    if (letter) return `${D.group} ${letter[1].toUpperCase()}`
    return num ? `${D.group} · ${D.matchday} ${num}` : D.group
  }
  // Domestic league / League Stage: "Regular Season - 38", "League Stage - 1" -> Round 38 / Round 1
  if (/regular season|league stage|^round\b|matchday|round - /.test(r)) {
    return num ? `${D.round} ${num}` : round
  }
  if (/play-?\s?off/.test(r)) return D.playoff
  return round   // no pattern matched -> return the ORIGINAL text (never lose words)
}
