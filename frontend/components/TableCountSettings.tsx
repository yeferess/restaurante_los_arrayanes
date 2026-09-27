"use client";

import { useEffect, useState, type FormEvent } from "react";
import {
  listTables,
  resizeTables,
  type Table,
  type ApiErrorBody,
} from "@/lib/api/orders";

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
      <h1>Gestión de mesas</h1>
      <form onSubmit={handleSubmit}>
        <label htmlFor="table-count">Número de mesas</label>
        <input
          id="table-count"
          type="number"
          min={1}
          value={count}
          onChange={(e) => setCount(e.target.value)}
          required
        />
        <button type="submit">Guardar</button>
      </form>
      {message && <p role="status">{message}</p>}
      <ul>
        {tables.map((table) => (
          <li key={table.number}>
            Mesa {table.number} — {table.status}
          </li>
        ))}
      </ul>
    </section>
  );
}
