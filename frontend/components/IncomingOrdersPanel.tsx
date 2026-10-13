"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { session } from "@/lib/api/auth";
import {
  listIncomingOrders,
  listOccupiedTables,
  reprintOrder,
  voidOrder,
  type Order,
  type ApiErrorBody,
} from "@/lib/api/orders";
import { subscribeToOrderUpdates } from "@/lib/api/ordersSocket";
import { formatPrice } from "@/lib/format";
import { AdminNoteEditor } from "./AdminNoteEditor";
import { ChargeOrderModal } from "./ChargeOrderModal";
import styles from "./IncomingOrdersPanel.module.css";

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

/** RF-14: the internal id is never shown as text — only the daily
 * number (blank, as "N° —", for a pre-upgrade order with none). */
function orderTitle(order: Order): string {
  return order.daily_number !== null ? `N° ${order.daily_number}` : "N° —";
}

function formatSentAt(sentAt: string | null): string | null {
  if (!sentAt) return null;
  const date = new Date(sentAt);
  const pad = (value: number) => value.toString().padStart(2, "0");
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)} ${pad(
    date.getHours()
  )}:${pad(date.getMinutes())}`;
}

/** Admin's incoming-orders panel (T68 — soporte RF-9, RF-11).
 *
 * Refreshes itself when the backend notifies a change over
 * `/ws/pedidos/`, and offers a manual "Actualizar" button as backup —
 * both paths call the exact same refetch function. */
export function IncomingOrdersPanel() {
  const router = useRouter();
  const [orders, setOrders] = useState<Order[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [chargingOrder, setChargingOrder] = useState<Order | null>(null);

  const [staleTables, setStaleTables] = useState(0);

  const refresh = useCallback(async () => {
    try {
      const data = await listIncomingOrders();
      setOrders(data);
      setMessage(null);
    } catch (error) {
      setMessage(formatError(error));
      // T94: an expired session (the PC sat unused) must not leave an
      // outdated list on screen — send the admin back to log in. A network
      // error (no `detail`) keeps the list and the message instead.
      try {
        await session();
      } catch (sessionError) {
        if ((sessionError as ApiErrorBody)?.detail !== undefined) {
          router.replace("/admin/login");
          return;
        }
      }
    }
    // RF-15: the notice is secondary — a failure here never hides the list.
    try {
      const occupied = await listOccupiedTables();
      setStaleTables(occupied.filter((table) => table.is_stale).length);
    } catch {
      setStaleTables(0);
    }
  }, [router]);

  useEffect(() => {
    refresh();
    const handle = subscribeToOrderUpdates(refresh);
    // T94: coming back to the tab or the network reconnecting refetches,
    // in case a notification was missed meanwhile.
    function handleVisible() {
      if (document.visibilityState === "visible") refresh();
    }
    document.addEventListener("visibilitychange", handleVisible);
    window.addEventListener("online", refresh);
    return () => {
      handle.close();
      document.removeEventListener("visibilitychange", handleVisible);
      window.removeEventListener("online", refresh);
    };
  }, [refresh]);

  async function handleChargedSuccessfully() {
    setChargingOrder(null);
    await refresh();
  }

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

  async function handleReprint(order: Order) {
    setMessage(null);
    try {
      const updated = await reprintOrder(order.id);
      setMessage(updated.print_warning ?? "Pedido reimpreso en cocina.");
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <section>
      <div className={styles.headerRow}>
        <h1 className={styles.heading}>Pedidos entrantes</h1>
        <button type="button" className={styles.refreshButton} onClick={refresh}>
          Actualizar
        </button>
      </div>
      {staleTables > 0 && (
        <p className={styles.staleNotice} role="alert">
          {staleTables === 1
            ? "Hay 1 mesa ocupada desde hace más de 3 horas."
            : `Hay ${staleTables} mesas ocupadas desde hace más de 3 horas.`}{" "}
          <Link href="/admin/mesas" className={styles.staleLink}>
            Revisar en Mesas
          </Link>
        </p>
      )}
      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}
      {orders.length === 0 ? (
        <p className={styles.empty}>No hay pedidos en preparación por ahora.</p>
      ) : (
        <ul className={styles.list}>
          {orders.map((order) => (
            <li key={order.id} className={styles.card}>
              <div className={styles.cardHeader}>
                <div className={styles.titleGroup}>
                  <span className={styles.orderId}>{orderTitle(order)}</span>
                  {formatSentAt(order.sent_at) && (
                    <span className={styles.sentAt}>
                      {formatSentAt(order.sent_at)}
                    </span>
                  )}
                </div>
                <span className={styles.table}>Mesa {order.table_number}</span>
              </div>
              <p className={styles.waiter}>Mesero: {order.waiter_username}</p>
              <div className={styles.total}>${formatPrice(order.total)}</div>
              {order.has_pending_print && (
                <span className={styles.printPendingBadge}>No impreso en cocina</span>
              )}
              <div className={styles.actions}>
                <button
                  type="button"
                  className={`${styles.actionButton} ${styles.chargeButton}`}
                  onClick={() => setChargingOrder(order)}
                >
                  Cobrar
                </button>
                <button
                  type="button"
                  className={`${styles.actionButton} ${styles.voidButton}`}
                  onClick={() => handleVoid(order)}
                >
                  Anular pedido
                </button>
                <button
                  type="button"
                  className={styles.actionButton}
                  onClick={() => handleReprint(order)}
                >
                  Reimprimir
                </button>
              </div>
              <AdminNoteEditor order={order} />
            </li>
          ))}
        </ul>
      )}
      {chargingOrder && (
        <ChargeOrderModal
          order={chargingOrder}
          onClose={() => setChargingOrder(null)}
          onCharged={handleChargedSuccessfully}
        />
      )}
    </section>
  );
}
