const CACHE_NAME = 'travel-app-v2';
const STATIC_ASSETS = [
  '/',
  '/static/index.html',
  '/static/style.css',
  '/static/app.js',
  '/static/manifest.json',
  '/static/icon-192.png',
  '/static/icon-512.png'
];

// Install: Cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Caching static assets');
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate: Clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME && name !== 'api-cache')
          .map((name) => {
            console.log('[SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    })
  );
  self.clients.claim();
});

// Fetch: Network first for API, cache fallback
self.addEventListener('fetch', (event) => {
  // Only handle GET requests for caching
  if (event.request.method === 'GET') {
    if (event.request.url.includes('/api/')) {
      event.respondWith(
        fetch(event.request)
          .then((response) => {
            const responseClone = response.clone();
            caches.open('api-cache').then((cache) => {
              cache.put(event.request, responseClone);
            });
            return response;
          })
          .catch(() => {
            console.log('[SW] Network failed, using cache for:', event.request.url);
            return caches.match(event.request);
          })
      );
    } else {
      // Static assets: cache first, fallback to network
      event.respondWith(
        caches.match(event.request).then((cachedResponse) => {
          return cachedResponse || fetch(event.request);
        })
      );
    }
  } else {
    // POST/PUT/DELETE: network only, but queue for sync if offline
    event.respondWith(
      fetch(event.request).catch(() => {
        console.log('[SW] Offline: queuing request for sync');
        return new Response('Offline', { status: 503, statusText: 'Offline' });
      })
    );
  }
});

// Background Sync: Retry failed requests
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-trips') {
    event.waitUntil(syncOfflineRequests());
  }
});

async function syncOfflineRequests() {
  const queue = await getOfflineQueue();
  for (const request of queue) {
    try {
      await fetch(request.url, {
        method: request.method,
        headers: { 'Content-Type': 'application/json' },
        body: request.body,
      });
      await removeFromQueue(request.id);
    } catch (error) {
      console.error('[SW] Sync failed:', error);
    }
  }
}

async function getOfflineQueue() {
  return new Promise((resolve) => {
    self.clients.matchAll().then((clients) => {
      const client = clients[0];
      if (client) {
        client.postMessage({ type: 'GET_QUEUE' });
        self.addEventListener('message', (e) => {
          if (e.data.type === 'QUEUE_DATA') {
            resolve(e.data.queue);
          }
        }, { once: true });
      } else {
        resolve([]);
      }
    });
  });
}

async function removeFromQueue(id) {
  return new Promise((resolve) => {
    self.clients.matchAll().then((clients) => {
      const client = clients[0];
      if (client) {
        client.postMessage({ type: 'REMOVE_FROM_QUEUE', id });
        self.addEventListener('message', (e) => {
          if (e.data.type === 'QUEUE_UPDATED') {
            resolve();
          }
        }, { once: true });
      } else {
        resolve();
      }
    });
  });
}

// Push Notifications
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : { title: 'Travel App', body: 'New update available!' };
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/static/icon-192.png',
      badge: '/static/icon-192.png',
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow('/')
  );
});
