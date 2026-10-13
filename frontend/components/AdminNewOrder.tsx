"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  createOrder,
  listMyOrders,
  listTables,
  type ApiErrorBody,
  type Order,
  type Table,
} from "@/lib/api/orders";
import { formatPrice, tableLabel } from "@/lib/format";
import styles from "./AdminNewOrder.module.css";

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

const OPEN_STATUS_LABEL: Partial<Record<Order["status"], string>> = {
  DRAFT: "Borrador",
  IN_PROGRESS: "En preparación",
};

/** 003 RF-18: the admin takes an order from the computer — a counter
 * order ("Mostrador / para llevar", no table) or one on a free table —
 * and keeps a list of their own open orders to continue editing them.
 * The order itself is built with the same OrderBuilder the waiters use. */
export function AdminNewOrder() {
  const router = useRouter();
  const [freeTables, setFreeTables] = useState<Table[]>([]);
  const [openOrders, setOpenOrders] = useState<Order[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listTables(), listMyOrders()])
      .then(([tables, mine]) => {
        setFreeTables(tables.filter((table) => table.status === "FREE"));
        setOpenOrders(
          mine.filter((order) => order.status === "DRAFT" || order.status === "IN_PROGRESS")
        );
      })
      .catch((error) => setMessage(formatError(error)));
  }, []);

  async function handleCreate(tableNumber: number | null) {
    setMessage(null);
    try {
      const order = await createOrder(tableNumber);
      router.push(`/admin/pedidos/nuevo/${order.id}`);
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <section className={styles.section}>
      <h1 className={styles.heading}>Nuevo pedido</h1>
      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}

      <button
        type="button"
        className={styles.counterButton}
        onClick={() => handleCreate(null)}
      >
        Mostrador / para llevar
      </button>

      <h2 className={styles.subheading}>O en una mesa libre</h2>
      {freeTables.length === 0 ? (
        <p className={styles.empty}>No hay mesas libres.</p>
      ) : (
        <ul className={styles.tables}>
          {freeTables.map((table) => (
            <li key={table.number}>
              <button
                type="button"
                className={styles.tableButton}
                onClick={() => handleCreate(table.number)}
              >
                Mesa {table.number}
              </button>
            </li>
          ))}
        </ul>
      )}

      <h2 className={styles.subheading}>Mis pedidos abiertos</h2>
      {openOrders.length === 0 ? (
        <p className={styles.empty}>No tienes pedidos abiertos.</p>
      ) : (
        <ul className={styles.openList}>
          {openOrders.map((order) => (
            <li key={order.id} className={styles.openItem}>
              <Link href={`/admin/pedidos/nuevo/${order.id}`} className={styles.openLink}>
                {order.daily_number !== null ? `N° ${order.daily_number}` : "Borrador"} ·{" "}
                {tableLabel(order.table_number)}
              </Link>
              <span className={styles.openMeta}>
                {OPEN_STATUS_LABEL[order.status]} · ${formatPrice(order.total)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
