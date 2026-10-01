// Competition name -> common Vietnamese name.
// Keyed by LEAGUE ID (not name) because many countries have a league named "Premier League"
// (England, Lebanon, Ukraine, Wales...) -> translating by name would rename all of them.
// Only translate competitions with a common Vietnamese name; competitions not in the table keep their original name.
// Big domestic leagues (La Liga, Serie A, Bundesliga, Ligue 1...) are intentionally KEPT unchanged.
import { state } from '../i18n'

export const LEAGUE_VI = {
  // Anh
  39: 'Ngoại Hạng Anh',
  45: 'Cúp FA',
  48: 'Cúp Liên đoàn Anh',
  528: 'Siêu cúp Anh',
  // European cups
  2: 'Champions League (Cúp C1)',
  3: 'Europa League (Cúp C2)',
  848: 'Conference League (Cúp C3)',
  531: 'Siêu cúp châu Âu',
  5: 'UEFA Nations League',
  // Domestic cups of major countries
  143: 'Cúp Nhà vua Tây Ban Nha',
  556: 'Siêu cúp Tây Ban Nha',
  137: 'Cúp Quốc gia Ý',
  81: 'Cúp Quốc gia Đức',
  66: 'Cúp Quốc gia Pháp',
  // National team / international
  4: 'Vô địch châu Âu (EURO)',
  7: 'Cúp bóng đá châu Á',
  10: 'Giao hữu',
  667: 'Giao hữu CLB',
  // Other
  307: 'Giải VĐQG Ả Rập Xê Út',
  253: 'Nhà nghề Mỹ (MLS)',
  340: 'V-League 1',
}

// Return the competition name in the current language. Pass the id for an exact lookup.
// locale 'en' or id not in the table -> keep the original name.
export function leagueName(name, id) {
  if (state.locale !== 'vi') return name
  if (id != null && LEAGUE_VI[id]) return LEAGUE_VI[id]
  return name
}
