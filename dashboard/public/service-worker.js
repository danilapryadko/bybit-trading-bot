// Service Worker for Bybit Trading Bot PWA
// Version 2.0.0 - Enhanced with offline queue and push notifications

const CACHE_NAME = 'bybit-bot-v2';
const urlsToCache = [
  '/',
  '/index.html',
  '/static/css/main.css',
  '/static/js/main.js',
  '/manifest.json',
  '/favicon.ico',
  '/logo192.png',
  '/logo512.png'
];

// Offline trade queue
let offlineQueue = [];

// Install event - cache assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
      .catch(error => {
        console.error('Failed to cache:', error);
      })
  );
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
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
  );
  self.clients.claim();
});

// Fetch event - serve from cache, fallback to network with offline queue support
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Handle GraphQL/API requests specially for offline queue
  if (url.pathname.includes('/graphql') || url.pathname.includes('/api/')) {
    event.respondWith(handleApiRequest(request));
    return;
  }
  
  // Skip WebSocket requests
  if (url.protocol === 'ws:' || url.protocol === 'wss:') {
    return;
  }

  // For other requests, use cache-first strategy
  event.respondWith(
    caches.match(request)
      .then(response => {
        // Cache hit - return response
        if (response) {
          return response;
        }

        // Clone the request
        const fetchRequest = request.clone();

        return fetch(fetchRequest).then(response => {
          // Check if valid response
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }

          // Clone the response
          const responseToCache = response.clone();

          caches.open(CACHE_NAME)
            .then(cache => {
              cache.put(request, responseToCache);
            });

          return response;
        }).catch(error => {
          // Network failed, try to return cached version
          console.error('[SW] Fetch failed:', error);
          return caches.match('/index.html');
        });
      })
  );
});

// Handle API requests with offline queue support
async function handleApiRequest(request) {
  try {
    const response = await fetch(request.clone());
    
    // If successful and we have queued items, try to process them
    if (response.ok && offlineQueue.length > 0) {
      // Process queue in background
      syncOfflineQueue();
    }
    
    return response;
  } catch (error) {
    console.error('[SW] API request failed:', error);
    
    // If it's a mutation/trade request and we're offline, queue it
    if (request.method === 'POST') {
      try {
        const body = await request.clone().json();
        
        // Check if it's a trade-related mutation
        if (body.query && (body.query.includes('placeOrder') || body.query.includes('closePosition'))) {
          // Add to offline queue
          addToOfflineQueue(request, body);
          
          // Return success response indicating it was queued
          return new Response(JSON.stringify({
            data: {
              success: true,
              queued: true,
              message: 'Trade queued for execution when online',
              queueId: Date.now()
            }
          }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
          });
        }
      } catch (e) {
        console.error('[SW] Failed to parse request body:', e);
      }
    }
    
    // For GET requests or non-queueable POST requests, try cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Return offline error
    return new Response(JSON.stringify({
      error: 'Network request failed - offline',
      offline: true
    }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// Background sync for offline trades
self.addEventListener('sync', event => {
  if (event.tag === 'sync-trades') {
    event.waitUntil(syncOfflineQueue());
  }
});

// Enhanced offline queue processing
async function syncOfflineQueue() {
  console.log('[SW] Processing offline queue:', offlineQueue.length, 'items');
  
  // Load queue from storage
  await loadQueueFromStorage();
  
  const queue = [...offlineQueue];
  offlineQueue = [];
  
  for (const item of queue) {
    try {
      const response = await fetch(item.url, {
        method: item.method,
        headers: item.headers,
        body: JSON.stringify(item.body)
      });
      
      if (response.ok) {
        console.log('[SW] Successfully processed queued trade');
        
        // Notify user
        self.registration.showNotification('Trade Executed', {
          body: `Your queued ${item.body.side} order for ${item.body.symbol} has been executed.`,
          icon: '/logo192.png',
          badge: '/logo192.png',
          tag: 'trade-executed',
          requireInteraction: false
        });
      } else {
        // Re-add to queue if failed
        offlineQueue.push(item);
      }
    } catch (error) {
      console.error('[SW] Failed to process queued trade:', error);
      offlineQueue.push(item);
    }
  }
  
  // Save updated queue
  if (offlineQueue.length > 0) {
    await saveQueueToStorage();
  } else {
    await clearQueueStorage();
  }
}

// Save offline queue to cache storage
async function saveQueueToStorage() {
  const cache = await caches.open('offline-queue');
  await cache.put('/queue', new Response(JSON.stringify(offlineQueue)));
}

// Load offline queue from cache storage
async function loadQueueFromStorage() {
  try {
    const cache = await caches.open('offline-queue');
    const response = await cache.match('/queue');
    if (response) {
      offlineQueue = await response.json();
    }
  } catch (error) {
    console.error('[SW] Failed to load queue:', error);
  }
}

// Clear queue storage
async function clearQueueStorage() {
  const cache = await caches.open('offline-queue');
  await cache.delete('/queue');
}

// Add trade to offline queue
function addToOfflineQueue(request, body) {
  offlineQueue.push({
    url: request.url,
    method: request.method,
    headers: Object.fromEntries(request.headers.entries()),
    body: body,
    timestamp: Date.now()
  });
  
  saveQueueToStorage();
  
  // Register sync when back online
  self.registration.sync.register('sync-trades');
}

// Enhanced push notifications with different types
self.addEventListener('push', event => {
  let notification = {
    title: 'Bybit Trading Bot',
    body: 'New trading alert',
    icon: '/logo192.png',
    badge: '/logo192.png',
    vibrate: [100, 50, 100],
    tag: 'trading-alert',
    requireInteraction: false,
    data: {
      dateOfArrival: Date.now()
    }
  };
  
  if (event.data) {
    try {
      const data = event.data.json();
      
      // Customize notification based on type
      switch (data.type) {
        case 'trade_executed':
          notification.title = '✅ Trade Executed';
          notification.body = `${data.side} ${data.amount} ${data.symbol} at ${data.price}`;
          notification.tag = 'trade-executed';
          notification.actions = [
            { action: 'view', title: 'View Position' },
            { action: 'close', title: 'Close Position' }
          ];
          break;
          
        case 'price_alert':
          notification.title = '📈 Price Alert';
          notification.body = `${data.symbol} reached ${data.price} (${data.change}%)`;
          notification.tag = 'price-alert';
          notification.actions = [
            { action: 'trade', title: 'Trade Now' },
            { action: 'dismiss', title: 'Dismiss' }
          ];
          break;
          
        case 'stop_loss':
          notification.title = '⛔ Stop Loss Triggered';
          notification.body = `Position closed: ${data.symbol} at ${data.price} (Loss: ${data.loss})`;
          notification.tag = 'stop-loss';
          notification.requireInteraction = true;
          break;
          
        case 'take_profit':
          notification.title = '💰 Take Profit Reached';
          notification.body = `Position closed: ${data.symbol} at ${data.price} (Profit: ${data.profit})`;
          notification.tag = 'take-profit';
          break;
          
        case 'daily_report':
          notification.title = '📊 Daily Report';
          notification.body = `P&L: ${data.pnl}, Win Rate: ${data.winRate}%, Trades: ${data.trades}`;
          notification.tag = 'daily-report';
          notification.actions = [
            { action: 'view_report', title: 'View Full Report' },
            { action: 'dismiss', title: 'Dismiss' }
          ];
          break;
          
        default:
          notification.title = data.title || notification.title;
          notification.body = data.body || notification.body;
      }
      
      notification.data = { ...notification.data, ...data };
    } catch (e) {
      notification.body = event.data.text();
    }
  }
  
  const options = notification;

  event.waitUntil(
    self.registration.showNotification('Bybit Trading Bot', options)
  );
});

// Enhanced notification click handler
self.addEventListener('notificationclick', event => {
  event.notification.close();
  
  const action = event.action;
  const data = event.notification.data;
  
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(clientList => {
        // Focus existing window if available
        for (const client of clientList) {
          if (client.url === '/' && 'focus' in client) {
            client.focus();
            
            // Send message to client with action
            client.postMessage({
              type: 'NOTIFICATION_CLICKED',
              action: action,
              data: data
            });
            
            return;
          }
        }
        
        // Open new window with specific route based on action
        let url = '/';
        switch (action) {
          case 'view':
          case 'view_position':
            url = '/positions';
            break;
          case 'trade':
            url = `/trade?symbol=${data.symbol || ''}`;
            break;
          case 'view_report':
            url = '/analytics';
            break;
          case 'close':
            url = `/positions?action=close&symbol=${data.symbol || ''}`;
            break;
        }
        
        return clients.openWindow(url);
      })
  );
});

// Periodic background sync for market data and positions
self.addEventListener('periodicsync', event => {
  if (event.tag === 'update-market-data') {
    event.waitUntil(updateMarketData());
  }
  if (event.tag === 'check-positions') {
    event.waitUntil(checkPositions());
  }
});

async function updateMarketData() {
  try {
    const response = await fetch('/api/v2/market/update');
    const data = await response.json();
    
    // Store in cache for offline access
    const cache = await caches.open('market-data');
    await cache.put(
      new Request('/api/v2/market/latest'),
      new Response(JSON.stringify(data), {
        headers: { 'Content-Type': 'application/json' }
      })
    );
    
    // Check for significant price changes
    if (data.alerts && data.alerts.length > 0) {
      for (const alert of data.alerts) {
        self.registration.showNotification('Price Alert', {
          body: alert.message,
          icon: '/logo192.png',
          badge: '/logo192.png',
          tag: `price-alert-${alert.symbol}`,
          data: alert
        });
      }
    }
  } catch (error) {
    console.error('[SW] Failed to update market data:', error);
  }
}

async function checkPositions() {
  try {
    const response = await fetch('/api/v2/positions/check');
    const data = await response.json();
    
    // Notify about positions requiring attention
    if (data.warnings && data.warnings.length > 0) {
      for (const warning of data.warnings) {
        self.registration.showNotification('Position Warning', {
          body: warning.message,
          icon: '/logo192.png',
          badge: '/logo192.png',
          tag: `position-warning-${warning.symbol}`,
          requireInteraction: true,
          data: warning
        });
      }
    }
  } catch (error) {
    console.error('[SW] Failed to check positions:', error);
  }
}

// Message handler for app communication
self.addEventListener('message', event => {
  const { type, data } = event.data;
  
  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
      
    case 'QUEUE_TRADE':
      addToOfflineQueue(data.request, data.body);
      event.ports[0].postMessage({ success: true, queued: true });
      break;
      
    case 'GET_QUEUE_STATUS':
      event.ports[0].postMessage({
        queueLength: offlineQueue.length,
        items: offlineQueue
      });
      break;
      
    case 'PROCESS_QUEUE':
      syncOfflineQueue();
      break;
      
    case 'ENABLE_NOTIFICATIONS':
      // Request notification permission handled by main app
      break;
  }
});

// Load offline queue on service worker start
loadQueueFromStorage();

console.log('[ServiceWorker] v2.0.0 loaded with enhanced features');