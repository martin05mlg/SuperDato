// SuperDato Lightweight Service Worker for PWA Installation and App Shell Cache
const CACHE_NAME = 'superdato-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/favicon.svg',
  '/manifest.webmanifest'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  // Let API and network requests go directly to network
  if (event.request.url.includes('/api/')) {
    return;
  }

  // Network first with cache fallback for navigation and static assets
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});

