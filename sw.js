/* オフラインで動かすための最小 Service Worker。
   通信できるときは常に新しいものを取りに行き (network-first)、
   圏外なら直前にキャッシュした版を返す。 */
const CACHE = 'flashcards-v2';
const ASSETS = ['./', './index.html', './manifest.json', './lists/index.json'];

self.addEventListener('install', ev => {
  ev.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', ev => {
  ev.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', ev => {
  if (ev.request.method !== 'GET') return;
  ev.respondWith(
    fetch(ev.request)
      .then(res => {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(ev.request, copy)).catch(() => {});
        return res;
      })
      .catch(() => caches.match(ev.request).then(hit => hit || caches.match('./index.html')))
  );
});
