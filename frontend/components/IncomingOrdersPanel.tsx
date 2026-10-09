"use client";

import { useCallback, useEffect, useState } from "react";
import {
  listIncomingOrders,
  voidOrder,
  type Order,
  type ApiErrorBody,
} from "@/lib/api/orders";
import { subscribeToOrderUpdates } from "@/lib/api/ordersSocket";
import { ChargeOrderModal } from "./ChargeOrderModal";
import styles from "./IncomingOrdersPanel.module.css";

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
  const [chargingOrder, setChargingOrder] = useState<Order | null>(null);

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

  async function handleChargedSuccessfully() {
    setChargingOrder(null);
    await refresh();
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
      <div className={styles.headerRow}>
        <h1 className={styles.heading}>Pedidos entrantes</h1>
        <button type="button" className={styles.refreshButton} onClick={refresh}>
          Actualizar
        </button>
      </div>
      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}
      {orders.length === 0 ? (
        <p className={styles.empty}>No hay pedidos en preparación por ahora.</p>
      ) : (
        <ul className={styles.list}>
          {orders.map((order) => (
            <li key={order.id} className={styles.card}>
              <div className={styles.cardHeader}>
                <span className={styles.orderId}>Pedido {order.id}</span>
                <span className={styles.table}>Mesa {order.table_number}</span>
              </div>
              <div className={styles.total}>${order.total}</div>
              {order.has_pending_print && (
                <span className={styles.printPendingBadge}>No impreso en cocina</span>
              )}
              <div className={styles.actions}>
                <button
                  type="button"
                  className={`${styles.actionButton} ${styles.chargeButton}`}
                  onClick={() => setChargingOrder(order)}
                >
                  Cobrar
                </button>
                <button
                  type="button"
                  className={`${styles.actionButton} ${styles.voidButton}`}
                  onClick={() => handleVoid(order)}
                >
                  Anular pedido
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {chargingOrder && (
        <ChargeOrderModal
          order={chargingOrder}
          onClose={() => setChargingOrder(null)}
          onCharged={handleChargedSuccessfully}
        />
      )}
    </section>
  );
}
