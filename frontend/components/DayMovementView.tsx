"use client";

import { useEffect, useState } from "react";
import { getDayMovement, type DayMovement, type ApiErrorBody } from "@/lib/api/stats";
import { formatPrice } from "@/lib/format";
import styles from "./DayMovementView.module.css";

const ORDER_STATUS_LABEL: Record<string, string> = {
  DRAFT: "Borrador",
  IN_PROGRESS: "En preparación",
  CHARGED: "Cobrado",
  VOIDED: "Anulado",
};

const PAYMENT_STATUS_LABEL: Record<string, string> = {
  ACTIVE: "Activo",
  VOIDED: "Anulado",
};

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)} ${pad(
    date.getHours()
  )}:${pad(date.getMinutes())}`;
}

/** Movement of a specific day (006-estadisticas, RF-6): every order
 * sent and every payment registered that day, including voided ones —
 * for traceability, never filtered. */
export function DayMovementView() {
  const [date, setDate] = useState("");
  const [movement, setMovement] = useState<DayMovement | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setMessage(null);
    getDayMovement(date || undefined)
      .then(setMovement)
      .catch((error) => setMessage(formatError(error)));
  }, [date]);

  return (
    <section className={styles.section}>
      <div className={styles.header}>
        <h1 className={styles.heading}>Movimiento del día</h1>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="movement-date">
            Fecha
          </label>
          <input
            id="movement-date"
            type="date"
            className={styles.input}
            value={date}
            onChange={(event) => setDate(event.target.value)}
          />
        </div>
      </div>

      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}

      {movement && (
        <div className={styles.grid}>
          <section className={styles.card}>
            <h2 className={styles.cardHeading}>Pedidos</h2>
            {movement.orders.length === 0 ? (
              <p className={styles.empty}>Sin movimiento de pedidos.</p>
            ) : (
              <ul className={styles.list}>
                {movement.orders.map((order, index) => (
                  <li key={index} className={styles.row}>
                    <span className={styles.rowMain}>
                      N° {order.daily_number ?? "—"}
                    </span>
                    <span>{order.waiter}</span>
                    <span>{ORDER_STATUS_LABEL[order.status] ?? order.status}</span>
                    <span className={styles.value}>${formatPrice(order.total)}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className={styles.card}>
            <h2 className={styles.cardHeading}>Cobros</h2>
            {movement.payments.length === 0 ? (
              <p className={styles.empty}>Sin movimiento de cobros.</p>
            ) : (
              <ul className={styles.list}>
                {movement.payments.map((payment, index) => (
                  <li key={index} className={styles.row}>
                    <span className={styles.rowMain}>{payment.account_name}</span>
                    <span className={styles.value}>${formatPrice(payment.amount)}</span>
                    <span>{payment.charged_by}</span>
                    <span>{formatDateTime(payment.charged_at)}</span>
                    <span>
                      {PAYMENT_STATUS_LABEL[payment.status] ?? payment.status}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </section>
  );
}
