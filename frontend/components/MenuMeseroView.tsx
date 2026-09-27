"use client";

import { useCallback, useEffect, useState } from "react";
import { getMenu, type Product, type ApiErrorBody } from "@/lib/api/menu";
import { subscribeToMenuUpdates } from "@/lib/api/menuSocket";

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

/** Mesero's read-only menu view (T40 — RF-6, RF-7).
 *
 * Refreshes itself when the backend notifies a change over `/ws/menu/`,
 * and offers a manual "Actualizar menú" button as the backup RF-6
 * requires — both paths call the exact same refetch function, so they
 * always agree. */
export function MenuMeseroView() {
  const [products, setProducts] = useState<Product[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await getMenu();
      setProducts(data);
      setMessage(null);
    } catch (error) {
      setMessage(formatError(error));
    }
  }, []);

  useEffect(() => {
    refresh();
    const handle = subscribeToMenuUpdates(refresh);
    return () => handle.close();
  }, [refresh]);

  return (
    <section>
      <h1>Menú</h1>
      <button type="button" onClick={refresh}>
        Actualizar menú
      </button>
      {message && <p role="status">{message}</p>}
      <ul>
        {products.map((product) => (
          <li key={product.id}>
            {product.name} — {product.category.name} — ${product.price}
          </li>
        ))}
      </ul>
    </section>
  );
}
