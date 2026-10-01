import axios from 'axios'

// Dev: leave VITE_API_BASE empty -> use '/api' (Vite proxies to the backend on localhost).
// Prod: set VITE_API_BASE = the deployed backend URL, e.g. https://...onrender.com/api
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 15000,
})

// API-Football sometimes returns HTML-ENCODED names (e.g. "O&apos;Reilly", "C&ocirc;te...") -> Vue
// renders text, so the literal "&apos;" appears. Decode once here so names display correctly everywhere.
// Only touches strings CONTAINING '&' (most strings are skipped immediately); no other data logic changes.
function decodeEntities(s) {
  if (typeof s !== 'string' || s.indexOf('&') === -1) return s
  return s
    .replace(/&apos;/g, "'").replace(/&#0*39;/g, "'").replace(/&#x0*27;/gi, "'")
    .replace(/&quot;/g, '"').replace(/&#0*34;/g, '"')
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&#0*(\d+);/g, (_, n) => String.fromCharCode(+n))
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCharCode(parseInt(h, 16)))
    .replace(/&amp;/g, '&') // always last so it does not accidentally swallow other entities
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
