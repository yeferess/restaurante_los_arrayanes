"use client";

import { useEffect, useState } from "react";
import { chargeOrder, type Order, type ApiErrorBody } from "@/lib/api/orders";
import {
  listAccounts,
  previewCharge,
  printReceipt,
  voidCharge,
  type ChargePreview,
  type PaymentAccount,
} from "@/lib/api/payments";
import { formatPrice } from "@/lib/format";
import styles from "./ChargeOrderModal.module.css";

const PREVIEW_DELAY_MS = 300;

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

/** The backend's preview for one specific discount input — only shown
 * while that input is still the current one. */
type PreviewState = { forDiscount: string; result: ChargePreview | null; error: string | null };

/** Charge confirmation modal (005-cobro — RF-1, RF-3, RF-4, RF-10,
 * RF-11): shows the order's already-calculated lines and total, an
 * optional peso discount (the total to pay comes from the backend's
 * preview, never computed here), the payment option, and — once
 * charged — the customer receipt. */
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
  const [discount, setDiscount] = useState("");
  const [discountReason, setDiscountReason] = useState("");
  const [preview, setPreview] = useState<PreviewState | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [charged, setCharged] = useState<Order | null>(null);

  const hasDiscount = discount.trim() !== "" && Number(discount) !== 0;
  const currentPreview = hasDiscount && preview?.forDiscount === discount ? preview : null;

  useEffect(() => {
    listAccounts()
      .then((data) => {
        setAccounts(data);
        setAccountId((current) => current || String(data[0]?.id ?? ""));
      })
      .catch((error) => setMessage(formatError(error)));
  }, []);

  useEffect(() => {
    if (!hasDiscount) return;
    const requested = discount;
    const timer = setTimeout(() => {
      previewCharge(order.id, Number(requested))
        .then((result) => setPreview({ forDiscount: requested, result, error: null }))
        .catch((error) =>
          setPreview({ forDiscount: requested, result: null, error: formatError(error) })
        );
    }, PREVIEW_DELAY_MS);
    return () => clearTimeout(timer);
  }, [discount, hasDiscount, order.id]);

  async function handleCharge() {
    setMessage(null);
    try {
      const updated = hasDiscount
        ? await chargeOrder(order.id, Number(accountId), {
            amount: Number(discount),
            reason: discountReason,
          })
        : await chargeOrder(order.id, Number(accountId));
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

  async function handleReceipt() {
    if (!charged) return;
    setMessage(null);
    try {
      const result = await printReceipt(charged.id);
      setMessage(result.print_warning ?? "Comprobante impreso.");
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  if (charged) {
    const payment = charged.active_payment;
    return (
      <div className={styles.overlay}>
        <div className={styles.modal}>
          <h2 className={styles.heading}>{orderTitle(charged)} cobrado</h2>
          <p className={styles.confirmationText}>
            Cobrado con <strong>{payment?.account_name}</strong>
            {" — "}${formatPrice(payment?.amount ?? 0)}
          </p>
          {payment && Number(payment.discount) > 0 && (
            <p className={styles.discountSummary}>
              Subtotal ${formatPrice(payment.subtotal)} · Descuento −$
              {formatPrice(payment.discount)}
              {payment.discount_reason && ` (${payment.discount_reason})`}
            </p>
          )}

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
              className={styles.cancelButton}
              onClick={handleReceipt}
            >
              Imprimir comprobante
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
                <span>${formatPrice(item.line_total)}</span>
              </li>
            ))}
        </ul>
        <div className={styles.totalRow}>
          <span>Total</span>
          <span className={styles.totalAmount}>${formatPrice(order.total)}</span>
        </div>

        {order.admin_note && (
          <p className={styles.adminNote}>Nota: {order.admin_note}</p>
        )}

        <div className={styles.field}>
          <label className={styles.label} htmlFor="charge-discount">
            Descuento (opcional, $)
          </label>
          <input
            id="charge-discount"
            className={styles.select}
            type="number"
            min={0}
            step="any"
            inputMode="decimal"
            value={discount}
            onChange={(event) => setDiscount(event.target.value)}
          />
        </div>
        {hasDiscount && (
          <div className={styles.field}>
            <label className={styles.label} htmlFor="charge-discount-reason">
              Motivo del descuento (opcional)
            </label>
            <input
              id="charge-discount-reason"
              className={styles.select}
              maxLength={200}
              value={discountReason}
              onChange={(event) => setDiscountReason(event.target.value)}
            />
          </div>
        )}
        {currentPreview?.result && (
          <div className={`${styles.totalRow} ${styles.payRow}`}>
            <span>Total a pagar</span>
            <span className={styles.totalAmount}>
              ${formatPrice(currentPreview.result.total)}
            </span>
          </div>
        )}
        {currentPreview?.error && (
          <p className={styles.message} role="alert">
            {currentPreview.error}
          </p>
        )}

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
            disabled={!accountId || Boolean(currentPreview?.error)}
          >
            Cobrar
          </button>
        </div>
      </div>
    </div>
  );
}
