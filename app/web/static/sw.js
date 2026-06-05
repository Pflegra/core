// Pflegra Service Worker — v44
// Strategie: Nur statische Assets cachen (CSS, JS, Icons)
// HTML, API, Login-Seiten werden NICHT gecacht

const CACHE_NAME = 'pflegra-static-v44';

const STATIC_ASSETS = [
  '/static/manifest.json',
];

// Installation — nur Manifest cachen
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

  // Nur GET cachen
  if (event.request.method !== 'GET') return;

  // NUR statische Assets cachen (CSS, JS, Icons, Fonts)
  const isStatic = url.pathname.startsWith('/static/');

  if (isStatic) {
    // Cache First für statische Assets
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
  }
  // Alles andere (HTML, API, Login) → direkt ans Netzwerk — kein Caching
});
