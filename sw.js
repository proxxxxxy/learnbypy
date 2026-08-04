/* オフラインで動かすための最小 Service Worker。
   通信できるときは常に新しいものを取りに行き (network-first)、
   圏外なら直前にキャッシュした版を返す。

   fetch() は既定でブラウザの HTTP キャッシュを経由するため、
   そのままだと「network-first のはずが古い index.html が返る」ことがある。
   (ホーム画面に追加した iOS の Web アプリで特に起こりやすい)
   そこでネットワーク取得は必ず cache:'no-store' で行う。 */
const CACHE = 'flashcards-v9';
const ASSETS = ['./', './index.html', './manifest.json', './lists/index.json'];

self.addEventListener('install', ev => {
  ev.waitUntil(
    caches.open(CACHE)
      .then(c => Promise.allSettled(ASSETS.map(u => c.add(new Request(u, { cache: 'reload' })))))
      .then(() => self.skipWaiting())
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
  const req = ev.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin) return;
  /* 版の確認だけは絶対にキャッシュを挟まない */
  const pathname = new URL(req.url).pathname;
  if (pathname.endsWith('/version.json') || pathname.endsWith('/start.html')) return;

  ev.respondWith(
    fetch(new Request(req, { cache: 'no-store' }))
      .then(res => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
        }
        return res;
      })
      .catch(() => caches.match(req).then(hit => hit || caches.match('./index.html')))
  );
});

/* ページから «すぐ切り替えろ» と言われたら待たずに有効化する */
self.addEventListener('message', ev => {
  if (ev.data === 'skip-waiting') self.skipWaiting();
});
