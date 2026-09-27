"use client";

import { useEffect, useState } from "react";
import {
  listMyOrders,
  setDelivered,
  releaseTable,
  type Order,
  type ApiErrorBody,
} from "@/lib/api/orders";

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

/** Mesero's own-orders screen (T67 — RF-8, RF-10): quick "Entregado"
 * toggle and "Liberar mesa" once the order was charged. */
export function MyOrdersList() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  function refresh() {
    return listMyOrders()
      .then(setOrders)
      .catch((error) => setMessage(formatError(error)));
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleToggleDelivered(order: Order) {
    setMessage(null);
    try {
      const updated = await setDelivered(order.id, !order.delivered);
      setOrders((current) =>
        current.map((item) => (item.id === updated.id ? updated : item))
      );
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  async function handleReleaseTable(order: Order) {
    setMessage(null);
    try {
      await releaseTable(order.table_number);
      await refresh();
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <section>
      <h1>Mis pedidos</h1>
      {message && <p role="status">{message}</p>}
      <ul>
        {orders.map((order) => (
          <li key={order.id}>
            Pedido {order.id} — Mesa {order.table_number} — {order.status} —
            total ${order.total}
            <button type="button" onClick={() => handleToggleDelivered(order)}>
              {order.delivered ? "Desmarcar entregado" : "Marcar entregado"}
            </button>
            {order.status === "CHARGED" && (
              <button type="button" onClick={() => handleReleaseTable(order)}>
                Liberar mesa
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
