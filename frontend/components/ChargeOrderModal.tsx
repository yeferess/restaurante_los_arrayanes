"use client";

import { useEffect, useState } from "react";
import { chargeOrder, type Order, type ApiErrorBody } from "@/lib/api/orders";
import {
  listAccounts,
  voidCharge,
  type PaymentAccount,
} from "@/lib/api/payments";
import { formatPrice } from "@/lib/format";
import styles from "./ChargeOrderModal.module.css";

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

/** RF-4, 003-RF-14: identifies the order by its daily number — never
 * the internal id — inherited from the same order payload 003 already
 * serializes (plan.md, sección 6). */
function orderTitle(order: Order): string {
  return order.daily_number !== null ? `N° ${order.daily_number}` : "Sin número";
}

function formatSentAt(sentAt: string | null): string | null {
  if (!sentAt) return null;
  const date = new Date(sentAt);
  const pad = (value: number) => value.toString().padStart(2, "0");
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)} ${pad(
    date.getHours()
  )}:${pad(date.getMinutes())}`;
}

/** Charge confirmation modal (005-cobro — RF-1, RF-3, RF-4): shows the
 * order's already-calculated total and lets the admin pick a payment
 * option from the catalog before confirming. */
export function ChargeOrderModal({
  order,
  onClose,
  onCharged,
}: {
  order: Order;
  onClose: () => void;
  onCharged: (order: Order) => void;
}) {
  const [accounts, setAccounts] = useState<PaymentAccount[]>([]);
  const [accountId, setAccountId] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [charged, setCharged] = useState<Order | null>(null);

  useEffect(() => {
    listAccounts()
      .then((data) => {
        setAccounts(data);
        setAccountId((current) => current || String(data[0]?.id ?? ""));
      })
      .catch((error) => setMessage(formatError(error)));
  }, []);

  async function handleCharge() {
    setMessage(null);
    try {
      const updated = await chargeOrder(order.id, Number(accountId));
      setCharged(updated);
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  async function handleUndo() {
    if (!charged) return;
    const reason = window.prompt("Motivo de la anulación del cobro:");
    if (!reason) return;
    setMessage(null);
    try {
      const reverted = await voidCharge(charged.id, reason);
      onCharged(reverted);
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  if (charged) {
    return (
      <div className={styles.overlay}>
        <div className={styles.modal}>
          <h2 className={styles.heading}>{orderTitle(charged)} cobrado</h2>
          <p className={styles.confirmationText}>
            Cobrado con <strong>{charged.active_payment?.account_name}</strong>
            {" — "}${formatPrice(charged.active_payment?.amount ?? 0)}
          </p>

          {message && (
            <p className={styles.message} role="status">
              {message}
            </p>
          )}

          <div className={styles.actions}>
            <button
              type="button"
              className={styles.cancelButton}
              onClick={handleUndo}
            >
              Anular cobro
            </button>
            <button
              type="button"
              className={styles.chargeButton}
              onClick={() => onCharged(charged)}
            >
              Cerrar
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        <h2 className={styles.heading}>
          {orderTitle(order)} — Mesa {order.table_number}
        </h2>
        {formatSentAt(order.sent_at) && (
          <p className={styles.sentAt}>Enviado {formatSentAt(order.sent_at)}</p>
        )}

        <ul className={styles.itemsList}>
          {order.items
            .filter((item) => !item.is_voided)
            .map((item) => (
              <li key={item.id} className={styles.itemLine}>
                <span>
                  {item.quantity}x {item.name}
                </span>
                <span>${formatPrice(Number(item.unit_price) * item.quantity)}</span>
              </li>
            ))}
        </ul>
        <div className={styles.totalRow}>
          <span>Total</span>
          <span className={styles.totalAmount}>${formatPrice(order.total)}</span>
        </div>

        {message && (
          <p className={styles.message} role="status">
            {message}
          </p>
        )}

        <div className={styles.field}>
          <label className={styles.label} htmlFor="payment-account">
            Opción de pago
          </label>
          <select
            id="payment-account"
            className={styles.select}
            value={accountId}
            onChange={(event) => setAccountId(event.target.value)}
          >
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.actions}>
          <button type="button" className={styles.cancelButton} onClick={onClose}>
            Cancelar
          </button>
          <button
            type="button"
            className={styles.chargeButton}
            onClick={handleCharge}
            disabled={!accountId}
          >
            Cobrar
          </button>
        </div>
      </div>
    </div>
  );
}
