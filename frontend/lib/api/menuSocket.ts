// Menu WebSocket client (T37 — RF-6).

const BACKEND_API_URL =
  process.env.NEXT_PUBLIC_BACKEND_API_URL ?? "http://127.0.0.1:8000";

const INITIAL_BACKOFF_MS = 1_000;
const MAX_BACKOFF_MS = 30_000;

function menuWebSocketUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_BACKEND_WS_URL;
  if (explicit) return `${explicit}/ws/menu/`;
  return `${BACKEND_API_URL.replace(/^http/, "ws")}/ws/menu/`;
}

export type MenuSocketHandle = {
  close: () => void;
};

/** Subscribes to real-time menu change notifications (RF-6).
 *
 * Calls `onMenuChanged` every time the backend broadcasts
 * `menu.actualizado`; reconnects automatically with exponential backoff
 * if the connection drops, since this is only a convenience — the
 * "Actualizar menú" manual button (RF-6) is the real fallback and never
 * depends on this socket being connected. */
export function subscribeToMenuUpdates(onMenuChanged: () => void): MenuSocketHandle {
  let socket: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let backoffMs = INITIAL_BACKOFF_MS;
  let closedByCaller = false;

  function connect() {
    socket = new WebSocket(menuWebSocketUrl());

    socket.onopen = () => {
      backoffMs = INITIAL_BACKOFF_MS;
    };

    socket.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        if (data?.type === "menu.actualizado") {
          onMenuChanged();
        }
      } catch {
        // Malformed frame: nothing actionable client-side.
      }
    };

    socket.onclose = () => {
      if (closedByCaller) return;
      reconnectTimer = setTimeout(() => {
        backoffMs = Math.min(backoffMs * 2, MAX_BACKOFF_MS);
        connect();
      }, backoffMs);
    };
  }

  connect();

  return {
    close: () => {
      closedByCaller = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
    },
  };
}
