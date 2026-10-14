"use client";

import { useCallback, useEffect, useState } from "react";
import { chargeOrder, getOrder, type Order, type ApiErrorBody } from "@/lib/api/orders";
import { subscribeToOrderUpdates } from "@/lib/api/ordersSocket";
import {
  listAccounts,
  previewCharge,
  printBill,
  printReceipt,
  voidCharge,
  type ChargePreview,
  type PaymentAccount,
} from "@/lib/api/payments";
import { formatPrice, tableLabel } from "@/lib/format";
import { AdminNoteEditor } from "./AdminNoteEditor";
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

/** The backend's preview for one specific discount input on one order
 * total — only shown while both are still the current ones. */
type PreviewState = { forDiscount: string; result: ChargePreview | null; error: string | null };

/** Charge confirmation modal (005-cobro — RF-1, RF-3, RF-4, RF-10,
 * RF-11): shows the order's already-calculated lines and total, an
 * optional peso discount (the total to pay comes from the backend's
 * preview, never computed here), the payment option, and — once
 * charged — the customer receipt.
 *
 * RF-12: the order shown is always re-fetched from the backend when the
 * window opens and whenever an order changes, and the charge sends the
 * total on screen so the backend refuses it if the order changed. */
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
  const [current, setCurrent] = useState<Order>(order);

  const hasDiscount = discount.trim() !== "" && Number(discount) !== 0;
  const previewKey = `${discount}|${current.total}`;
  const currentPreview = hasDiscount && preview?.forDiscount === previewKey ? preview : null;
  const changedSinceOpened =
    current.total !== order.total || current.items.length !== order.items.length;

  const reload = useCallback(async () => {
    try {
      setCurrent(await getOrder(order.id));
    } catch {
      // Keep showing the last known copy; charging still checks the total.
    }
  }, [order.id]);

  useEffect(() => {
    reload();
    const handle = subscribeToOrderUpdates(reload);
    return () => handle.close();
  }, [reload]);

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
    const key = previewKey;
    const timer = setTimeout(() => {
      previewCharge(order.id, Number(requested))
        .then((result) => setPreview({ forDiscount: key, result, error: null }))
        .catch((error) =>
          setPreview({ forDiscount: key, result: null, error: formatError(error) })
        );
    }, PREVIEW_DELAY_MS);
    return () => clearTimeout(timer);
  }, [discount, hasDiscount, order.id, previewKey]);

  async function handleCharge() {
    setMessage(null);
    try {
      const updated = await chargeOrder(
        order.id,
        Number(accountId),
        hasDiscount ? { amount: Number(discount), reason: discountReason } : undefined,
        current.total
      );
      setCharged(updated);
    } catch (error) {
      setMessage(formatError(error));
      // RF-12: if the order changed meanwhile, show its new items/total.
      await reload();
    }
  }

  /** RF-13: the bill with the discount typed right now; charges nothing
   * and the window stays open until the customer pays. */
  async function handleBill() {
    setMessage(null);
    try {
      const result = await printBill(order.id, hasDiscount ? Number(discount) : undefined);
      setMessage(result.print_warning ?? "Cuenta impresa.");
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
          {orderTitle(current)} — {tableLabel(current.table_number)}
        </h2>
        {formatSentAt(current.sent_at) && (
          <p className={styles.sentAt}>Enviado {formatSentAt(current.sent_at)}</p>
        )}
        {changedSinceOpened && (
          <p className={styles.changedNotice} role="alert">
            El pedido cambió: se actualizaron los ítems y el total. Revísalos antes
            de cobrar.
          </p>
        )}

        <ul className={styles.itemsList}>
          {(current.item_groups ?? []).map((group) => (
            <li key={group.parts[0].item_id} className={styles.itemLine}>
              <span>
                {group.quantity}x {group.name}
              </span>
              <span>${formatPrice(group.line_total)}</span>
            </li>
          ))}
        </ul>
        <div className={styles.totalRow}>
          <span>Total</span>
          <span className={styles.totalAmount}>${formatPrice(current.total)}</span>
        </div>

        <AdminNoteEditor order={current} onSaved={setCurrent} />

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
            className={styles.cancelButton}
            onClick={handleBill}
            disabled={Boolean(currentPreview?.error)}
          >
            Imprimir cuenta
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
