// Tên quốc gia (đội tuyển) tiếng Anh -> tiếng Việt.
// Chỉ dùng cho các đội TUYỂN QUỐC GIA. Tên CLB không nằm trong map nên
// sẽ được trả về nguyên gốc -> không ảnh hưởng các giải CLB.
import { state } from '../i18n'

export const COUNTRY_VI = {
  // Châu Âu
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

  // Nam Mỹ
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

  // Bắc/Trung Mỹ
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

  // Châu Phi
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

  // Châu Á
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

  // Châu Đại Dương
  'New Zealand': 'New Zealand',
  'Fiji': 'Fiji',
}

// Hậu tố đội trẻ / đội nữ -> giữ nguyên khi dịch phần tên nước.
const SUFFIX_RE = /\s+(U\d{2}|W|Women|Olympic|B)$/i

// Trả về tên hiển thị theo ngôn ngữ hiện tại.
// - locale 'en'  -> giữ nguyên tên gốc.
// - locale 'vi'  -> dịch nếu có trong map, tách hậu tố U23/W... nếu cần.
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
