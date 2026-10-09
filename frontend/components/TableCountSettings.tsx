"use client";

import { useEffect, useState, type FormEvent } from "react";
import {
  listTables,
  resizeTables,
  type Table,
  type ApiErrorBody,
} from "@/lib/api/orders";
import styles from "./TableCountSettings.module.css";

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

/** Table count management screen (T64 — RF-1): the admin sets a single
 * total; the backend creates/removes tables at the top of the range. */
export function TableCountSettings() {
  const [tables, setTables] = useState<Table[]>([]);
  const [count, setCount] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  async function refresh() {
    const data = await listTables();
    setTables(data);
    setCount(String(data.length));
  }

  useEffect(() => {
    refresh().catch((error) => setMessage(formatError(error)));
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      const data = await resizeTables(Number(count));
      setTables(data);
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <section>
      <h1 className={styles.heading}>Gestión de mesas</h1>
      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="table-count">
            Número de mesas
          </label>
          <input
            id="table-count"
            className={styles.input}
            type="number"
            min={1}
            value={count}
            onChange={(e) => setCount(e.target.value)}
            required
          />
        </div>
        <button type="submit" className={styles.saveButton}>
          Guardar
        </button>
      </form>
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
          </li>
        ))}
      </ul>
    </section>
  );
}
