// Minimal service worker: caches the app shell so the app can open offline.
// Only registered in the production build (see main.js), so it does not affect development.
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

  // Do not cache the API -> always fetch fresh data.
  if (url.pathname.startsWith('/api')) return

  // Do not cache Vercel's internal routes (/_vercel/insights/* for Web Analytics):
  // cache-first would keep an old/broken copy -> the analytics script would not load correctly.
  if (url.pathname.startsWith('/_vercel')) return

  // Page navigation: ALWAYS fetch a FRESH index.html from the network (no-store) so we never serve
  // an old shell pointing to chunk files deleted after a deploy (causing a blank page). Offline -> fallback.
  if (request.mode === 'navigate') {
    e.respondWith(fetch(request, { cache: 'no-store' }).catch(() => caches.match('/index.html')))
    return
  }

  // Static assets: cache-first.
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
