const CACHE_NAME = 'hub-hyo-v1';

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            // Opcional: Se você quiser que o site abra até sem internet depois, 
            // coloca os nomes das músicas e imagens aqui dentro no futuro.
            return cache.addAll(['./', './index.html']);
        })
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        fetch(event.request).catch(() => caches.match(event.request))
    );
});
