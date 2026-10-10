// Minimal service worker (006: HTTPS/PWA installability) — no offline
// caching strategy was requested, this only exists so Chrome detects a
// registered worker. Plain network passthrough.
self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  event.respondWith(fetch(event.request));
});
