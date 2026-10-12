"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  listMyOrders,
  listTables,
  setDelivered,
  releaseTable,
  retryPrint,
  reprintOrder,
  deleteOrder,
  type Order,
  type ApiErrorBody,
} from "@/lib/api/orders";
import { formatPrice, todayIso } from "@/lib/format";
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

/** RF-8: "entregado" never becomes a 5th real status — it's a
 * presentation rule layered on top of "en preparación", computed from
 * the same (status, delivered) pair every order payload already
 * carries. Every other status keeps its own label regardless of
 * `delivered` (plan.md, decisión técnica 10). */
function displayStatus(order: Order): { label: string; badgeClass: string } {
  if (order.status === "IN_PROGRESS" && order.delivered) {
    return { label: "Entregado", badgeClass: styles.badgeDelivered };
  }
  return { label: STATUS_LABEL[order.status], badgeClass: STATUS_BADGE_CLASS[order.status] };
}

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

/** RF-14: the internal id is never shown as text — only the daily
 * number (or "Borrador" while it has none yet). */
function orderTitle(order: Order): string {
  if (order.daily_number !== null) return `N° ${order.daily_number}`;
  return order.status === "DRAFT" ? "Borrador" : "N° —";
}

function formatSentAt(sentAt: string | null): string | null {
  if (!sentAt) return null;
  const date = new Date(sentAt);
  const pad = (value: number) => value.toString().padStart(2, "0");
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)} ${pad(
    date.getHours()
  )}:${pad(date.getMinutes())}`;
}

/** Mesero's own-orders screen (T67 — RF-8, RF-10): quick "Entregado"
 * toggle and "Liberar mesa" once the order was charged. Shows one day
 * at a time (RF-16): today by default, plus whatever is still pending
 * from earlier days, as decided by the backend. */
export function MyOrdersList() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [paidTables, setPaidTables] = useState<Set<number>>(new Set());
  const [message, setMessage] = useState<string | null>(null);
  const [fecha, setFecha] = useState<string>(todayIso);

  function refresh() {
    return Promise.all([listMyOrders(fecha), listTables()])
      .then(([ordersData, tablesData]) => {
        setOrders(ordersData);
        setPaidTables(
          new Set(
            tablesData
              .filter((table) => table.status === "PAID")
              .map((table) => table.number)
          )
        );
      })
      .catch((error) => setMessage(formatError(error)));
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fecha]);

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

  async function handleDelete(order: Order) {
    setMessage(null);
    try {
      await deleteOrder(order.id);
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

  async function handleReprint(order: Order) {
    setMessage(null);
    try {
      const updated = await reprintOrder(order.id);
      setMessage(updated.print_warning ?? "Pedido reimpreso en cocina.");
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <section className={styles.section}>
      <div className={styles.headerRow}>
        <h1 className={styles.heading}>Mis pedidos</h1>
        <label className={styles.dateLabel}>
          Fecha
          <input
            type="date"
            className={styles.dateInput}
            value={fecha}
            max={todayIso()}
            onChange={(event) => event.target.value && setFecha(event.target.value)}
          />
        </label>
      </div>
      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}
      {orders.length === 0 && (
        <p className={styles.empty}>No hay pedidos para esta fecha.</p>
      )}
      <ul className={styles.list}>
        {orders.map((order) => (
          <li key={order.id} className={styles.card}>
            <div className={styles.cardHeader}>
              <div className={styles.titleGroup}>
                <Link
                  href={`/mesero/pedidos/${order.id}`}
                  className={styles.orderLink}
                >
                  {orderTitle(order)}
                </Link>
                {formatSentAt(order.sent_at) && (
                  <span className={styles.sentAt}>
                    {formatSentAt(order.sent_at)}
                  </span>
                )}
              </div>
              <span className={styles.table}>Mesa {order.table_number}</span>
            </div>
            <div className={styles.metaRow}>
              <span className={`${styles.badge} ${displayStatus(order).badgeClass}`}>
                {displayStatus(order).label}
              </span>
              <span className={styles.total}>${formatPrice(order.total)}</span>
              {order.has_pending_print && (
                <span className={`${styles.badge} ${styles.badgePrintPending}`}>
                  No impreso en cocina
                </span>
              )}
            </div>
            {order.draft_reminder && (
              <p className={styles.draftReminder} role="note">
                Borrador sin enviar: envíalo o elimínalo para liberar la mesa.
              </p>
            )}
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.actionButton}
                onClick={() => handleToggleDelivered(order)}
              >
                {order.delivered ? "Desmarcar entregado" : "Marcar entregado"}
              </button>
              {order.status === "DRAFT" && (
                <button
                  type="button"
                  className={styles.actionButton}
                  onClick={() => handleDelete(order)}
                >
                  Eliminar
                </button>
              )}
              {order.status === "CHARGED" && paidTables.has(order.table_number) && (
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
              {order.status === "IN_PROGRESS" && (
                <button
                  type="button"
                  className={styles.actionButton}
                  onClick={() => handleReprint(order)}
                >
                  Reimprimir pedido
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
