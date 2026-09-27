"use client";

import { useCallback, useEffect, useState } from "react";
import {
  listIncomingOrders,
  chargeOrder,
  voidOrder,
  type Order,
  type ApiErrorBody,
} from "@/lib/api/orders";
import { subscribeToOrderUpdates } from "@/lib/api/ordersSocket";

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

/** Admin's incoming-orders panel (T68 — soporte RF-9, RF-11).
 *
 * Refreshes itself when the backend notifies a change over
 * `/ws/pedidos/`, and offers a manual "Actualizar" button as backup —
 * both paths call the exact same refetch function. */
export function IncomingOrdersPanel() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await listIncomingOrders();
      setOrders(data);
      setMessage(null);
    } catch (error) {
      setMessage(formatError(error));
    }
  }, []);

  useEffect(() => {
    refresh();
    const handle = subscribeToOrderUpdates(refresh);
    return () => handle.close();
  }, [refresh]);

  async function handleCharge(order: Order) {
    setMessage(null);
    try {
      await chargeOrder(order.id);
      await refresh();
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  async function handleVoid(order: Order) {
    const reason = window.prompt("Motivo de la anulación:");
    if (!reason) return;
    setMessage(null);
    try {
      await voidOrder(order.id, reason);
      await refresh();
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <section>
      <h1>Pedidos entrantes</h1>
      <button type="button" onClick={refresh}>
        Actualizar
      </button>
      {message && <p role="status">{message}</p>}
      <ul>
        {orders.map((order) => (
          <li key={order.id}>
            Pedido {order.id} — Mesa {order.table_number} — total $
            {order.total}
            <button type="button" onClick={() => handleCharge(order)}>
              Cobrar
            </button>
            <button type="button" onClick={() => handleVoid(order)}>
              Anular pedido
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
