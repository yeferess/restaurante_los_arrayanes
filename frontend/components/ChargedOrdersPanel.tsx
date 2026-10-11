"use client";

import { useCallback, useEffect, useState } from "react";
import {
  listChargedOrders,
  reprintOrder,
  type Order,
  type ApiErrorBody,
} from "@/lib/api/orders";
import { formatPrice } from "@/lib/format";
import styles from "./ChargedOrdersPanel.module.css";

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

/** RF-14: the internal id is never shown as text — only the daily number. */
function orderTitle(order: Order): string {
  return order.daily_number !== null ? `N° ${order.daily_number}` : "N° —";
}

function formatTime(iso: string): string {
  const date = new Date(iso);
  const pad = (value: number) => value.toString().padStart(2, "0");
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** Today in the browser's local time, as YYYY-MM-DD for <input type="date">. */
function todayIso(): string {
  const now = new Date();
  const pad = (value: number) => value.toString().padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** Admin's "Cobrados" tab (005; reprint per 004 RF-12): orders charged
 * on the chosen day, with their detail and a reprint action. */
export function ChargedOrdersPanel() {
  const [fecha, setFecha] = useState<string>(todayIso);
  const [orders, setOrders] = useState<Order[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setOrders(await listChargedOrders(fecha));
      setMessage(null);
    } catch (error) {
      setMessage(formatError(error));
    }
  }, [fecha]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleReprint(order: Order) {
    setMessage(null);
    try {
      const updated = await reprintOrder(order.id);
      setMessage(updated.print_warning ?? `${orderTitle(order)} reimpreso en cocina.`);
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <section>
      <div className={styles.headerRow}>
        <h1 className={styles.heading}>Pedidos cobrados</h1>
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
      {orders.length === 0 ? (
        <p className={styles.empty}>No hay pedidos cobrados en esta fecha.</p>
      ) : (
        <ul className={styles.list}>
          {orders.map((order) => {
            const activeItems = order.items.filter((item) => !item.is_voided);
            return (
              <li key={order.id} className={styles.card}>
                <div className={styles.cardHeader}>
                  <span className={styles.orderId}>{orderTitle(order)}</span>
                  <span className={styles.table}>Mesa {order.table_number}</span>
                </div>
                <p className={styles.meta}>
                  Mesero: {order.waiter_username}
                  {order.active_payment && (
                    <>
                      {" · "}Cobrado {formatTime(order.active_payment.charged_at)} por{" "}
                      {order.active_payment.charged_by} · {order.active_payment.account_name}
                    </>
                  )}
                </p>
                <ul className={styles.items}>
                  {activeItems.map((item) => (
                    <li key={item.id} className={styles.item}>
                      <div className={styles.itemLine}>
                        <span>
                          {item.quantity}x {item.name}
                        </span>
                        <span className={styles.itemPrice}>
                          ${formatPrice(item.unit_price)} c/u
                        </span>
                      </div>
                      {item.note && <p className={styles.note}>Nota: {item.note}</p>}
                    </li>
                  ))}
                </ul>
                <div className={styles.footer}>
                  <span className={styles.total}>Total ${formatPrice(order.total)}</span>
                  <button
                    type="button"
                    className={styles.actionButton}
                    onClick={() => handleReprint(order)}
                  >
                    Reimprimir
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
