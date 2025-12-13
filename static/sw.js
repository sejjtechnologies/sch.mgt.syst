const CACHE_NAME = 'school-manager-v1';
const urlsToCache = [
  '/',
  '/static/manifest.json',
  '/static/images/school_192.png',
  '/static/offline.html',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js'
];

// Install Service Worker
self.addEventListener('install', event => {
  console.log('Service Worker installing.');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Service Worker caching files.');
        return cache.addAll(urlsToCache);
      })
      .then(() => {
        console.log('Service Worker installed and files cached.');
        return self.skipWaiting();
      })
  );
});

// Fetch Event
self.addEventListener('fetch', event => {
  console.log('Fetch event for:', event.request.url);

  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Return cached version or fetch from network
        if (response) {
          console.log('Serving from cache:', event.request.url);
          return response;
        }

        return fetch(event.request)
          .then(response => {
            // Cache successful responses for future use
            if (response.status === 200 && response.type === 'basic') {
              const responseClone = response.clone();
              caches.open(CACHE_NAME)
                .then(cache => {
                  cache.put(event.request, responseClone);
                });
            }
            return response;
          });
      })
      .catch(() => {
        console.log('Network failed, serving offline page for:', event.request.url);
        // If both cache and network fail, show offline page
        if (event.request.mode === 'navigate' || event.request.destination === 'document') {
          return caches.match('/static/offline.html');
        }
      })
  );
});

// Activate Event
self.addEventListener('activate', event => {
  console.log('Service Worker activating.');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
    .then(() => {
      console.log('Service Worker activated.');
      return self.clients.claim();
    })
  );
});