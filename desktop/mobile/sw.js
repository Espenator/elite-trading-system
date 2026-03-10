/**
 * Embodier Trader Mobile — service worker.
 * Cache-first for static assets; network-first for API.
 */

const CACHE_NAME = 'embodier-mobile-v1';
const STATIC_ASSETS = [
  '/index.html',
  '/styles.css',
  '/app.js',
  '/manifest.webmanifest',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  const path = url.pathname;

  // API: network-first (no cache)
  if (path.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request).catch(() =>
        new Response(JSON.stringify({ error: 'Offline' }), {
          status: 503,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );
    return;
  }

  // Static assets: cache-first
  const isStatic =
    path === '/' ||
    path === '/index.html' ||
    path.endsWith('.css') ||
    path.endsWith('.js') ||
    path.endsWith('.webmanifest');
  if (isStatic) {
    const cacheRequest = path === '/' ? '/index.html' : event.request;
    event.respondWith(
      caches.match(cacheRequest).then((cached) => {
        if (cached) return cached;
        return fetch(event.request).then((res) => {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return res;
        });
      })
    );
    return;
  }

  event.respondWith(fetch(event.request));
});
