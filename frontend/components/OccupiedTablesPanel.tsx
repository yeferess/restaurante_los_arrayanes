"use client";

import { useCallback, useEffect, useState } from "react";
import {
  discardDraft,
  listOccupiedTables,
  voidOrder,
  type OccupiedTable,
  type Order,
  type ApiErrorBody,
} from "@/lib/api/orders";
import { subscribeToOrderUpdates } from "@/lib/api/ordersSocket";
import { formatPrice } from "@/lib/format";
import styles from "./OccupiedTablesPanel.module.css";

const STATUS_LABEL: Partial<Record<Order["status"], string>> = {
  DRAFT: "Borrador",
  IN_PROGRESS: "En preparación",
};

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

function formatSince(createdAt: string): string {
  const date = new Date(createdAt);
  const pad = (value: number) => value.toString().padStart(2, "0");
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)} ${pad(
    date.getHours()
  )}:${pad(date.getMinutes())}`;
}

/** RF-15: admin view of what is holding each occupied table, so a
 * forgotten order (draft or sent) can be found and voided. */
export function OccupiedTablesPanel() {
  const [tables, setTables] = useState<OccupiedTable[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setTables(await listOccupiedTables());
    } catch (error) {
      setMessage(formatError(error));
    }
  }, []);

  useEffect(() => {
    refresh();
    const handle = subscribeToOrderUpdates(refresh);
    return () => handle.close();
  }, [refresh]);

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

  async function handleDiscardDraft(tableNumber: number, order: Order) {
    const confirmed = window.confirm(
      `¿Eliminar el borrador de la mesa ${tableNumber}? La mesa quedará libre.`
    );
    if (!confirmed) return;
    setMessage(null);
    try {
      await discardDraft(order.id);
      await refresh();
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  const staleCount = tables.filter((table) => table.is_stale).length;

  return (
    <section className={styles.section}>
      <h2 className={styles.heading}>Mesas ocupadas</h2>
      {staleCount > 0 && (
        <p className={styles.staleNotice} role="alert">
          {staleCount === 1
            ? "Hay 1 mesa ocupada desde hace más de 3 horas."
            : `Hay ${staleCount} mesas ocupadas desde hace más de 3 horas.`}
        </p>
      )}
      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}
      {tables.length === 0 ? (
        <p className={styles.empty}>No hay mesas ocupadas.</p>
      ) : (
        <ul className={styles.list}>
          {tables.map((table) => (
            <li
              key={table.number}
              className={table.is_stale ? `${styles.card} ${styles.cardStale}` : styles.card}
            >
              <div className={styles.cardHeader}>
                <span className={styles.table}>Mesa {table.number}</span>
                {table.order && (
                  <span className={styles.badge}>{STATUS_LABEL[table.order.status]}</span>
                )}
              </div>
              {table.order ? (
                <>
                  <p className={styles.meta}>
                    Mesero: {table.order.waiter_username} · desde{" "}
                    {formatSince(table.order.created_at)} · {table.order.items.length}{" "}
                    {table.order.items.length === 1 ? "ítem" : "ítems"} · $
                    {formatPrice(table.order.total)}
                  </p>
                  {table.order.status === "DRAFT" ? (
                    <button
                      type="button"
                      className={styles.voidButton}
                      onClick={() => handleDiscardDraft(table.number, table.order as Order)}
                    >
                      Eliminar borrador
                    </button>
                  ) : (
                    <button
                      type="button"
                      className={styles.voidButton}
                      onClick={() => handleVoid(table.order as Order)}
                    >
                      Anular pedido
                    </button>
                  )}
                </>
              ) : (
                <p className={styles.meta}>Sin pedido activo.</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
