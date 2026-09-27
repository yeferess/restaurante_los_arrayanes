"use client";

import { useEffect, useState } from "react";
import {
  listTables,
  createOrder,
  type Table,
  type ApiErrorBody,
} from "@/lib/api/orders";

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
    <section>
      <h1>Mesas</h1>
      {message && <p role="status">{message}</p>}
      <ul>
        {tables.map((table) => (
          <li key={table.number}>
            Mesa {table.number} — {table.status}
            {table.status === "FREE" && (
              <button type="button" onClick={() => handleCreate(table.number)}>
                Crear pedido
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
