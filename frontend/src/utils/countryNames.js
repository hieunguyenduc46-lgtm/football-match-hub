// Country (national team) names English -> Vietnamese.
// Only used for NATIONAL TEAMS. Club names are not in the map, so
// they are returned unchanged -> club competitions are not affected.
import { state } from '../i18n'

export const COUNTRY_VI = {
  // Europe
  'England': 'Anh',
  'Scotland': 'Scotland',
  'Wales': 'Wales',
  'Northern Ireland': 'Bắc Ireland',
  'Ireland': 'Ireland',
  'Republic of Ireland': 'Cộng hòa Ireland',
  'France': 'Pháp',
  'Germany': 'Đức',
  'Spain': 'Tây Ban Nha',
  'Italy': 'Ý',
  'Portugal': 'Bồ Đào Nha',
  'Netherlands': 'Hà Lan',
  'Belgium': 'Bỉ',
  'Switzerland': 'Thụy Sĩ',
  'Austria': 'Áo',
  'Poland': 'Ba Lan',
  'Sweden': 'Thụy Điển',
  'Norway': 'Na Uy',
  'Denmark': 'Đan Mạch',
  'Finland': 'Phần Lan',
  'Iceland': 'Iceland',
  'Russia': 'Nga',
  'Ukraine': 'Ukraine',
  'Croatia': 'Croatia',
  'Serbia': 'Serbia',
  'Slovenia': 'Slovenia',
  'Slovakia': 'Slovakia',
  'Czech Republic': 'Cộng hòa Séc',
  'Czechia': 'Séc',
  'Hungary': 'Hungary',
  'Romania': 'Romania',
  'Bulgaria': 'Bulgaria',
  'Greece': 'Hy Lạp',
  'Turkey': 'Thổ Nhĩ Kỳ',
  'Türkiye': 'Thổ Nhĩ Kỳ',
  'Albania': 'Albania',
  'Kosovo': 'Kosovo',
  'North Macedonia': 'Bắc Macedonia',
  'Bosnia and Herzegovina': 'Bosnia và Herzegovina',
  'Montenegro': 'Montenegro',
  'Andorra': 'Andorra',
  'Luxembourg': 'Luxembourg',
  'Malta': 'Malta',
  'Cyprus': 'Síp',
  'Estonia': 'Estonia',
  'Latvia': 'Latvia',
  'Lithuania': 'Litva',
  'Belarus': 'Belarus',
  'Moldova': 'Moldova',
  'Georgia': 'Gruzia',
  'Armenia': 'Armenia',
  'Azerbaijan': 'Azerbaijan',
  'Kazakhstan': 'Kazakhstan',
  'Gibraltar': 'Gibraltar',
  'San Marino': 'San Marino',
  'Liechtenstein': 'Liechtenstein',
  'Faroe Islands': 'Quần đảo Faroe',

  // South America
  'Brazil': 'Brazil',
  'Argentina': 'Argentina',
  'Uruguay': 'Uruguay',
  'Colombia': 'Colombia',
  'Chile': 'Chile',
  'Peru': 'Peru',
  'Ecuador': 'Ecuador',
  'Paraguay': 'Paraguay',
  'Bolivia': 'Bolivia',
  'Venezuela': 'Venezuela',

  // North/Central America
  'United States': 'Mỹ',
  'USA': 'Mỹ',
  'Mexico': 'Mexico',
  'Canada': 'Canada',
  'Costa Rica': 'Costa Rica',
  'Panama': 'Panama',
  'Honduras': 'Honduras',
  'Jamaica': 'Jamaica',
  'El Salvador': 'El Salvador',
  'Guatemala': 'Guatemala',
  'Haiti': 'Haiti',
  'Trinidad and Tobago': 'Trinidad và Tobago',

  // Africa
  'Nigeria': 'Nigeria',
  'Senegal': 'Senegal',
  'Egypt': 'Ai Cập',
  'Morocco': 'Maroc',
  'Algeria': 'Algeria',
  'Tunisia': 'Tunisia',
  'Ghana': 'Ghana',
  'Cameroon': 'Cameroon',
  'Ivory Coast': 'Bờ Biển Ngà',
  'Côte d\'Ivoire': 'Bờ Biển Ngà',
  'South Africa': 'Nam Phi',
  'Mali': 'Mali',
  'Burkina Faso': 'Burkina Faso',
  'DR Congo': 'CHDC Congo',
  'Congo DR': 'CHDC Congo',
  'Cape Verde': 'Cape Verde',
  'Guinea': 'Guinea',
  'Gabon': 'Gabon',
  'Zambia': 'Zambia',
  'Angola': 'Angola',
  'Kenya': 'Kenya',
  'Ethiopia': 'Ethiopia',
  'Mauritania': 'Mauritania',
  'Equatorial Guinea': 'Guinea Xích Đạo',

  // Asia
  'Japan': 'Nhật Bản',
  'South Korea': 'Hàn Quốc',
  'Korea Republic': 'Hàn Quốc',
  'North Korea': 'Triều Tiên',
  'Korea DPR': 'Triều Tiên',
  'China': 'Trung Quốc',
  'China PR': 'Trung Quốc',
  'Australia': 'Úc',
  'Iran': 'Iran',
  'Saudi Arabia': 'Ả Rập Xê Út',
  'Qatar': 'Qatar',
  'Iraq': 'Iraq',
  'United Arab Emirates': 'UAE',
  'UAE': 'UAE',
  'Jordan': 'Jordan',
  'Syria': 'Syria',
  'Lebanon': 'Lebanon',
  'Uzbekistan': 'Uzbekistan',
  'Bahrain': 'Bahrain',
  'Oman': 'Oman',
  'Kuwait': 'Kuwait',
  'Palestine': 'Palestine',
  'India': 'Ấn Độ',
  'Vietnam': 'Việt Nam',
  'Thailand': 'Thái Lan',
  'Indonesia': 'Indonesia',
  'Malaysia': 'Malaysia',
  'Singapore': 'Singapore',
  'Philippines': 'Philippines',
  'Myanmar': 'Myanmar',
  'Cambodia': 'Campuchia',
  'Laos': 'Lào',
  'Bangladesh': 'Bangladesh',
  'Pakistan': 'Pakistan',
  'Sri Lanka': 'Sri Lanka',
  'Nepal': 'Nepal',
  'Maldives': 'Maldives',
  'Hong Kong': 'Hồng Kông',
  'Chinese Taipei': 'Đài Bắc Trung Hoa',

  // Oceania
  'New Zealand': 'New Zealand',
  'Fiji': 'Fiji',
}

// Youth / women's team suffixes -> kept as-is when translating the country part.
const SUFFIX_RE = /\s+(U\d{2}|W|Women|Olympic|B)$/i

// Return the display name in the current language.
// - locale 'en'  -> keep the original name.
// - locale 'vi'  -> translate if it is in the map, splitting off U23/W... suffixes if needed.
export function teamName(name) {
  if (!name || state.locale !== 'vi') return name

  if (COUNTRY_VI[name]) return COUNTRY_VI[name]

  const m = name.match(SUFFIX_RE)
  if (m) {
    const base = name.slice(0, m.index)
    if (COUNTRY_VI[base]) return COUNTRY_VI[base] + ' ' + m[1]
  }
  return name
}
