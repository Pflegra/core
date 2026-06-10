// Pflegra Service Worker — v50
// Strategie: Statische Assets cachen + Offline-Fallback

const CACHE_NAME    = 'pflegra-static-v50';
const OFFLINE_URL   = '/offline';

const STATIC_ASSETS = [
  '/static/manifest.json',
  '/offline',
];

// Installation
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Aktivierung — alte Caches löschen
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch-Strategie
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Nur GET
  if (event.request.method !== 'GET') return;

  // Statische Assets: Cache First
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request).then(cached => {
        if (cached) return cached;
        return fetch(event.request).then(response => {
          if (response.ok) {
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, response.clone()));
          }
          return response;
        });
      })
    );
    return;
  }

  // HTML-Seiten: Network First, bei Fehler Offline-Fallback
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() =>
        caches.match(OFFLINE_URL).then(r => r || new Response('Offline', { status: 503 }))
      )
    );
    return;
  }

  // Alles andere direkt ans Netzwerk
});
