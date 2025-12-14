const CACHE_NAME = 'school-manager-v5'; // Force cache refresh - fixed API caching
const urlsToCache = [
  '/static/manifest.json',
  '/static/images/school_192.png',
  '/static/offline.html'
  // Removed '/' from cache - navigation requests use network-first strategy
];

// Install Service Worker
self.addEventListener('install', event => {
  console.log('Service Worker installing.');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Service Worker caching core files.');
        return cache.addAll(urlsToCache);
      })
      .then(() => {
        console.log('Service Worker installed and core files cached.');
        return self.skipWaiting();
      })
      .catch(error => {
        console.error('Service Worker installation failed:', error);
      })
  );
});

// Fetch Event
self.addEventListener('fetch', event => {
  console.log('Fetch event for:', event.request.url, 'Mode:', event.request.mode, 'Destination:', event.request.destination);

  // Handle navigation requests (page loads) - Network First Strategy
  if (event.request.mode === 'navigate') {
    console.log('Handling navigation request with network-first strategy');
    event.respondWith(
      fetch(event.request)
        .then(response => {
          console.log('Navigation successful, caching response');
          // Cache successful navigation responses
          const responseClone = response.clone();
          caches.open(CACHE_NAME)
            .then(cache => {
              cache.put(event.request, responseClone);
            });
          return response;
        })
        .catch(() => {
          console.log('Navigation failed, serving offline page');
          return caches.match('/static/offline.html');
        })
    );
    return;
  }

  // Handle API requests - Network First, no offline fallback
  if (event.request.url.includes('/api/') ||
      event.request.url.includes('/db-test') ||
      event.request.url.includes('/teacher/') ||
      event.request.url.includes('/secretary/') ||
      event.request.url.includes('/headteacher/') ||
      event.request.url.includes('/admin/') ||
      event.request.url.includes('/bursar/') ||
      event.request.url.includes('/parent/')) {
    console.log('Handling API request:', event.request.url);
    event.respondWith(
      fetch(event.request)
        .catch(() => {
          return new Response(JSON.stringify({ error: 'Offline', message: 'This feature requires internet connection' }), {
            status: 503,
            statusText: 'Service Unavailable',
            headers: { 'Content-Type': 'application/json' }
          });
        })
    );
    return;
  }

  // Handle static assets - Cache First Strategy
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          console.log('Serving from cache:', event.request.url);
          return response;
        }

        return fetch(event.request)
          .then(response => {
            // Cache successful GET responses for static assets only (not API calls)
            if (response.status === 200 &&
                event.request.method === 'GET' &&
                !event.request.url.includes('/teacher/') &&
                !event.request.url.includes('/secretary/') &&
                !event.request.url.includes('/headteacher/') &&
                !event.request.url.includes('/parent/') &&
                !event.request.url.includes('/admin/') &&
                !event.request.url.includes('/bursar/') &&
                !event.request.url.includes('/api/') &&
                (response.type === 'basic' || response.type === 'cors')) {
              const responseClone = response.clone();
              caches.open(CACHE_NAME)
                .then(cache => {
                  cache.put(event.request, responseClone);
                });
            }
            return response;
          })
          .catch(error => {
            console.log('Fetch failed for:', event.request.url, error);
            // For failed static asset requests, return a basic response
            return new Response('', { status: 404, statusText: 'Not Found' });
          });
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