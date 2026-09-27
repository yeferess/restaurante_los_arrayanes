"use client";

import { useEffect, useRef } from "react";
import { heartbeat } from "@/lib/api/auth";

const THROTTLE_MS = 60_000;
const ACTIVITY_EVENTS = ["mousemove", "click", "keydown", "scroll", "touchstart"] as const;

/** Pings the backend on user activity so an admin's session survives
 * inactivity checks (RF-8). Mount only inside the admin panel layout —
 * never on the login page. */
export function SessionHeartbeat() {
  const lastSentAtRef = useRef(Number.NEGATIVE_INFINITY);

  useEffect(() => {
    function handleActivity() {
      const now = Date.now();
      if (now - lastSentAtRef.current < THROTTLE_MS) {
        return;
      }
      lastSentAtRef.current = now;
      heartbeat().catch(() => {
        // A stale/expired session surfaces on the next real request the
        // user makes; nothing actionable to do from a background ping.
      });
    }

    for (const eventName of ACTIVITY_EVENTS) {
      window.addEventListener(eventName, handleActivity);
    }
    return () => {
      for (const eventName of ACTIVITY_EVENTS) {
        window.removeEventListener(eventName, handleActivity);
      }
    };
  }, []);

  return null;
}
