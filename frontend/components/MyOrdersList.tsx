"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  listMyOrders,
  setDelivered,
  releaseTable,
  retryPrint,
  type Order,
  type ApiErrorBody,
} from "@/lib/api/orders";
import styles from "./MyOrdersList.module.css";

const STATUS_LABEL: Record<Order["status"], string> = {
  DRAFT: "Borrador",
  IN_PROGRESS: "En preparación",
  CHARGED: "Cobrado",
  VOIDED: "Anulado",
};

const STATUS_BADGE_CLASS: Record<Order["status"], string> = {
  DRAFT: styles.badgeDraft,
  IN_PROGRESS: styles.badgeInProgress,
  CHARGED: styles.badgeCharged,
  VOIDED: styles.badgeVoided,
};

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

  async function handleRetryPrint(order: Order) {
    setMessage(null);
    try {
      const updated = await retryPrint(order.id);
      setOrders((current) =>
        current.map((item) => (item.id === updated.id ? updated : item))
      );
      if (updated.print_warning) {
        setMessage(updated.print_warning);
      }
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <section className={styles.section}>
      <h1 className={styles.heading}>Mis pedidos</h1>
      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}
      <ul className={styles.list}>
        {orders.map((order) => (
          <li key={order.id} className={styles.card}>
            <div className={styles.cardHeader}>
              <Link href={`/mesero/pedidos/${order.id}`} className={styles.orderLink}>
                Pedido {order.id}
              </Link>
              <span className={styles.table}>Mesa {order.table_number}</span>
            </div>
            <div className={styles.metaRow}>
              <span className={`${styles.badge} ${STATUS_BADGE_CLASS[order.status]}`}>
                {STATUS_LABEL[order.status]}
              </span>
              <span className={styles.total}>${order.total}</span>
              {order.has_pending_print && (
                <span className={`${styles.badge} ${styles.badgePrintPending}`}>
                  No impreso en cocina
                </span>
              )}
            </div>
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.actionButton}
                onClick={() => handleToggleDelivered(order)}
              >
                {order.delivered ? "Desmarcar entregado" : "Marcar entregado"}
              </button>
              {order.status === "CHARGED" && (
                <button
                  type="button"
                  className={`${styles.actionButton} ${styles.actionButtonPrimary}`}
                  onClick={() => handleReleaseTable(order)}
                >
                  Liberar mesa
                </button>
              )}
              {order.has_pending_print &&
                order.status !== "CHARGED" &&
                order.status !== "VOIDED" && (
                  <button
                    type="button"
                    className={`${styles.actionButton} ${styles.actionButtonPrimary}`}
                    onClick={() => handleRetryPrint(order)}
                  >
                    Reintentar impresión
                  </button>
                )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
