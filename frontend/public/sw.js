// Service worker tối giản: cache app shell để mở offline được.
// Chỉ đăng ký ở bản production (xem main.js) nên không ảnh hưởng dev.
const CACHE = 'fmh-v7'
const SHELL = ['/', '/index.html', '/icon-v2.svg', '/manifest.webmanifest', '/pwa-192-v2.png', '/pwa-512-v2.png', '/apple-touch-icon-v2.png']

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)))
  self.skipWaiting()
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
  )
  self.clients.claim()
})

self.addEventListener('fetch', (e) => {
  const { request } = e
  if (request.method !== 'GET') return
  const url = new URL(request.url)

  // Không cache API -> luôn lấy dữ liệu mới.
  if (url.pathname.startsWith('/api')) return

  // Không cache route nội bộ Vercel (/_vercel/insights/* của Web Analytics):
  // nếu cache-first sẽ giữ bản cũ/hỏng -> script analytics không nạp đúng.
  if (url.pathname.startsWith('/_vercel')) return

  // Điều hướng trang: LUÔN lấy index.html MỚI từ mạng (no-store) để không bao giờ phục vụ
  // shell cũ trỏ tới file chunk đã bị xoá sau khi deploy (gây trang trắng). Offline -> fallback.
  if (request.mode === 'navigate') {
    e.respondWith(fetch(request, { cache: 'no-store' }).catch(() => caches.match('/index.html')))
    return
  }

  // Tài nguyên tĩnh: cache-first.
  e.respondWith(
    caches.match(request).then((cached) => {
      return (
        cached ||
        fetch(request).then((res) => {
          const copy = res.clone()
          caches.open(CACHE).then((c) => c.put(request, copy))
          return res
        }).catch(() => cached)
      )
    })
  )
})
