import axios from 'axios'

// Dev: để trống VITE_API_BASE -> dùng '/api' (Vite proxy sang backend localhost).
// Prod: đặt VITE_API_BASE = URL backend đã deploy, ví dụ https://...onrender.com/api
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 15000,
})

export default api
