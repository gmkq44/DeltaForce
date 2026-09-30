const CACHE = 'df-v1';
const CORE = ['./', './index.html', './manifest.webmanifest', './icons/icon-192.png', './icons/icon-512.png'];

self.addEventListener('install', e => {
    e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
    e.waitUntil(caches.keys()
        .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
        .then(() => self.clients.claim()));
});

// Network first (so daily passwords stay fresh), fall back to cache when offline
self.addEventListener('fetch', e => {
    if (e.request.method !== 'GET') return;
    e.respondWith(
        fetch(e.request).then(res => {
            if (res.ok || res.type === 'opaque') {
                const copy = res.clone();
                caches.open(CACHE).then(c => c.put(e.request, copy));
            }
            return res;
        }).catch(() => caches.match(e.request, { ignoreSearch: true })
            .then(r => r || (e.request.mode === 'navigate' ? caches.match('./index.html') : undefined)))
    );
});
