const CACHE_NAME = 'bibliotheca-v3';
const ASSETS = [
  './',
  './index.html',
  './catalogo.json',
  'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  // Para bibliotecas externas (PDF.js/Fontes), prioriza o cache para abrir instantaneamente offline
  if (e.request.url.includes('cdnjs.cloudflare.com') || e.request.url.includes('fonts.')) {
    e.respondWith(
      caches.match(e.request).then((cached) => cached || fetch(e.request))
    );
    return;
  }

  // Para o catálogo e app, busca a versão mais nova na rede primeiro
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        const resClone = res.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(e.request, resClone));
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});