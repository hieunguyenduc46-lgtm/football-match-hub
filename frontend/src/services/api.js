import axios from 'axios'

// Dev: để trống VITE_API_BASE -> dùng '/api' (Vite proxy sang backend localhost).
// Prod: đặt VITE_API_BASE = URL backend đã deploy, ví dụ https://...onrender.com/api
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 15000,
})

// API-Football đôi khi trả TÊN đã MÃ HOÁ HTML (vd "O&apos;Reilly", "C&ocirc;te...") -> Vue
// render text nên hiện literal "&apos;". Giải mã 1 lần ở đây để mọi nơi hiển thị tên đúng.
// Chỉ chạm chuỗi CÓ ký tự '&' (đa số chuỗi bỏ qua ngay), không đổi logic dữ liệu khác.
function decodeEntities(s) {
  if (typeof s !== 'string' || s.indexOf('&') === -1) return s
  return s
    .replace(/&apos;/g, "'").replace(/&#0*39;/g, "'").replace(/&#x0*27;/gi, "'")
    .replace(/&quot;/g, '"').replace(/&#0*34;/g, '"')
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&#0*(\d+);/g, (_, n) => String.fromCharCode(+n))
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCharCode(parseInt(h, 16)))
    .replace(/&amp;/g, '&') // luôn cuối cùng để không nuốt nhầm các entity khác
}

function deepDecode(v) {
  if (typeof v === 'string') return decodeEntities(v)
  if (Array.isArray(v)) { for (let i = 0; i < v.length; i++) v[i] = deepDecode(v[i]); return v }
  if (v && typeof v === 'object') { for (const k in v) v[k] = deepDecode(v[k]); return v }
  return v
}

api.interceptors.response.use((res) => {
  if (res && res.data) res.data = deepDecode(res.data)
  return res
})

export default api
