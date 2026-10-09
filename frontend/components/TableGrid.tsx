"use client";

import { useEffect, useState } from "react";
import {
  listTables,
  createOrder,
  type Table,
  type ApiErrorBody,
} from "@/lib/api/orders";
import styles from "./TableGrid.module.css";

const STATUS_LABEL: Record<Table["status"], string> = {
  FREE: "Libre",
  OCCUPIED: "Ocupada",
  PAID: "Pagada",
};

const STATUS_BADGE_CLASS: Record<Table["status"], string> = {
  FREE: styles.badgeFree,
  OCCUPIED: styles.badgeOccupied,
  PAID: styles.badgePaid,
};

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

/** Mesero's table overview (T65 — RF-1, RF-2, RF-13): shows every
 * table's status, and lets the mesero create a new order on a free
 * one. */
export function TableGrid() {
  const [tables, setTables] = useState<Table[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    listTables()
      .then(setTables)
      .catch((error) => setMessage(formatError(error)));
  }, []);

  async function handleCreate(tableNumber: number) {
    setMessage(null);
    try {
      const order = await createOrder(tableNumber);
      setMessage(`Pedido ${order.id} creado en la mesa ${tableNumber}.`);
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <section className={styles.section}>
      <h1 className={styles.heading}>Mesas</h1>
      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}
      <ul className={styles.grid}>
        {tables.map((table) => (
          <li key={table.number} className={styles.card}>
            <span className={`${styles.badge} ${STATUS_BADGE_CLASS[table.status]}`}>
              {STATUS_LABEL[table.status]}
            </span>
            <span className={styles.number}>Mesa {table.number}</span>
            {table.status === "FREE" && (
              <button
                type="button"
                className={styles.createButton}
                onClick={() => handleCreate(table.number)}
              >
                Crear pedido
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
