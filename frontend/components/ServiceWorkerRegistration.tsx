"use client";

import { useEffect } from "react";

/** Registers the minimal service worker (006: HTTPS/PWA installability)
 * — only in production, so `next dev` is never affected by a stale
 * cached worker. */
export function ServiceWorkerRegistration() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // Installability is best-effort; a failed registration shouldn't
      // break the app.
    });
  }, []);

  return null;
}
