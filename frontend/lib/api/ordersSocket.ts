// Orders WebSocket client (T63 — soporte de RF-9, RF-11). Admin-only
// feed of incoming order changes (unlike menuSocket.ts, mesero never
// connects here — it acts on orders it already has on screen).

const BACKEND_API_URL =
  process.env.NEXT_PUBLIC_BACKEND_API_URL ?? "http://127.0.0.1:8000";

const INITIAL_BACKOFF_MS = 1_000;
const MAX_BACKOFF_MS = 30_000;

function ordersWebSocketUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_BACKEND_WS_URL;
  if (explicit) return `${explicit}/ws/pedidos/`;
  return `${BACKEND_API_URL.replace(/^http/, "ws")}/ws/pedidos/`;
}

export type OrdersSocketHandle = {
  close: () => void;
};

/** Subscribes to real-time order change notifications for the admin
 * panel (plan.md, sección 4). Calls `onOrdersChanged` every time the
 * backend broadcasts `pedidos.actualizado`; reconnects automatically
 * with exponential backoff if the connection drops, and refetches once
 * reconnected so nothing missed meanwhile stays hidden — the manual
 * "Actualizar" button in the admin panel never depends on this socket
 * being connected. */
export function subscribeToOrderUpdates(
  onOrdersChanged: () => void
): OrdersSocketHandle {
  let socket: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let backoffMs = INITIAL_BACKOFF_MS;
  let closedByCaller = false;
  let hasConnectedBefore = false;

  function connect() {
    socket = new WebSocket(ordersWebSocketUrl());

    socket.onopen = () => {
      backoffMs = INITIAL_BACKOFF_MS;
      // T94: changes broadcast while the socket was down were never
      // received — ask for the list again on every reconnection.
      if (hasConnectedBefore) onOrdersChanged();
      hasConnectedBefore = true;
    };

    socket.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        if (data?.type === "pedidos.actualizado") {
          onOrdersChanged();
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
