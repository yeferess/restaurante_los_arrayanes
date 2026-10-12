"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  deleteOrder,
  getOrder,
  addItem,
  voidItem,
  sendOrder,
  fixTable,
  listTables,
  type Order,
  type Table,
  type ApiErrorBody,
} from "@/lib/api/orders";
import { getMenu, type Product } from "@/lib/api/menu";
import { formatPrice } from "@/lib/format";
import styles from "./OrderBuilder.module.css";

const STATUS_LABEL: Record<Order["status"], string> = {
  DRAFT: "Borrador",
  IN_PROGRESS: "En preparación",
  CHARGED: "Cobrado",
  VOIDED: "Anulado",
};

/** RF-8: same presentation rule as MyOrdersList.tsx — "entregado" is
 * not a 5th real status, just the label shown while "en preparación"
 * and delivered (plan.md, decisión técnica 10). */
function displayStatus(order: Order): { label: string; isDelivered: boolean } {
  if (order.status === "IN_PROGRESS" && order.delivered) {
    return { label: "Entregado", isDelivered: true };
  }
  return { label: STATUS_LABEL[order.status], isDelivered: false };
}

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

/** Mesero's order builder screen (T66 — RF-3, RF-4, RF-5, RF-6, RF-7):
 * add catalog/off-menu items with notes, send the draft, add
 * post-send additions, void an item with a reason, and correct the
 * order's table. */
export function OrderBuilder({ orderId }: { orderId: number }) {
  const [order, setOrder] = useState<Order | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [freeTables, setFreeTables] = useState<Table[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  const [mode, setMode] = useState<"catalog" | "off-menu">("catalog");
  const [productId, setProductId] = useState("");
  const [offMenuName, setOffMenuName] = useState("");
  const [offMenuPrice, setOffMenuPrice] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [note, setNote] = useState("");

  const [destinationTable, setDestinationTable] = useState("");

  async function refresh() {
    const [orderData, menuData, tablesData] = await Promise.all([
      getOrder(orderId),
      getMenu(),
      listTables(),
    ]);
    setOrder(orderData);
    setProducts(menuData);
    setFreeTables(tablesData.filter((table) => table.status === "FREE"));
    setProductId((current) => current || (menuData[0] ? String(menuData[0].id) : ""));
  }

  useEffect(() => {
    refresh().catch((error) => setMessage(formatError(error)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId]);

  // RF-15: leaving the screen with a draft that never got an item
  // discards it, so a mistaken tap doesn't keep the table occupied.
  const latestOrder = useRef<Order | null>(null);
  useEffect(() => {
    latestOrder.current = order;
  }, [order]);
  useEffect(() => {
    return () => {
      const current = latestOrder.current;
      if (current?.status === "DRAFT" && current.items.length === 0) {
        deleteOrder(current.id).catch(() => {});
      }
    };
  }, [orderId]);

  async function handleAddItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      const item =
        mode === "catalog"
          ? await addItem(orderId, {
              productId: Number(productId),
              quantity: Number(quantity),
              note: note || undefined,
            })
          : await addItem(orderId, {
              name: offMenuName,
              price: Number(offMenuPrice),
              quantity: Number(quantity),
              note: note || undefined,
            });
      setOffMenuName("");
      setOffMenuPrice("");
      setQuantity("1");
      setNote("");
      await refresh();
      if (item.print_warning) {
        setMessage(item.print_warning);
      }
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  async function handleSend() {
    setMessage(null);
    try {
      const updated = await sendOrder(orderId);
      setOrder(updated);
      if (updated.print_warning) {
        setMessage(updated.print_warning);
      }
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  async function handleVoidItem(itemId: number) {
    const reason = window.prompt("Motivo de la anulación:");
    if (!reason) return;
    setMessage(null);
    try {
      const item = await voidItem(orderId, itemId, reason);
      await refresh();
      if (item.print_warning) {
        setMessage(item.print_warning);
      }
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  async function handleFixTable(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!destinationTable) return;
    setMessage(null);
    try {
      const updated = await fixTable(orderId, Number(destinationTable));
      setOrder(updated);
      setDestinationTable("");
      await refresh();
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  if (!order) {
    return <p role="status">{message ?? "Cargando..."}</p>;
  }

  return (
    <section className={styles.section}>
      <div>
        <div className={styles.header}>
          <h1 className={styles.heading}>
            Pedido <span className={styles.orderId}>{order.id}</span>
          </h1>
          <span className={styles.table}>Mesa {order.table_number}</span>
        </div>
        <span
          className={`${styles.badge} ${
            displayStatus(order).isDelivered ? styles.badgeDelivered : ""
          }`}
        >
          {displayStatus(order).label}
        </span>
      </div>

      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}

      <div className={styles.itemsCard}>
        {order.items.length === 0 ? (
          <p className={styles.emptyItems}>Todavía no agregaste ningún ítem.</p>
        ) : (
          <ul className={styles.itemsList}>
            {order.items.map((item) => (
              <li
                key={item.id}
                className={item.is_voided ? `${styles.item} ${styles.itemVoided}` : styles.item}
              >
                <div className={styles.itemInfo}>
                  <span className={styles.itemLine}>
                    <span className={styles.itemQty}>{item.quantity}x</span> {item.name} — $
                    {formatPrice(item.unit_price)}
                  </span>
                  {item.note && <span className={styles.itemNote}>{item.note}</span>}
                  {item.is_voided && <span className={styles.itemVoidedTag}>Anulado</span>}
                </div>
                {!item.is_voided && order.status === "IN_PROGRESS" && (
                  <button
                    type="button"
                    className={styles.voidButton}
                    onClick={() => handleVoidItem(item.id)}
                  >
                    Anular
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {(order.status === "DRAFT" || order.status === "IN_PROGRESS") && (
        <form className={styles.card} onSubmit={handleAddItem}>
          <h2 className={styles.cardTitle}>Agregar ítem</h2>
          <div className={styles.modeRow}>
            <label className={styles.modeLabel}>
              <input
                type="radio"
                checked={mode === "catalog"}
                onChange={() => setMode("catalog")}
              />
              Del menú
            </label>
            <label className={styles.modeLabel}>
              <input
                type="radio"
                checked={mode === "off-menu"}
                onChange={() => setMode("off-menu")}
              />
              Fuera de carta
            </label>
          </div>

          {mode === "catalog" ? (
            <div className={styles.field}>
              <label className={styles.label} htmlFor="product-select">
                Producto
              </label>
              <select
                id="product-select"
                className={styles.select}
                value={productId}
                onChange={(event) => setProductId(event.target.value)}
              >
                {products.map((product) => (
                  <option key={product.id} value={product.id}>
                    {product.name}
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <div className={styles.fieldRow}>
              <div className={styles.field}>
                <label className={styles.label} htmlFor="off-menu-name">
                  Nombre
                </label>
                <input
                  id="off-menu-name"
                  className={styles.input}
                  value={offMenuName}
                  onChange={(event) => setOffMenuName(event.target.value)}
                />
              </div>
              <div className={styles.field}>
                <label className={styles.label} htmlFor="off-menu-price">
                  Precio
                </label>
                <input
                  id="off-menu-price"
                  className={styles.input}
                  type="number"
                  step="0.01"
                  value={offMenuPrice}
                  onChange={(event) => setOffMenuPrice(event.target.value)}
                />
              </div>
            </div>
          )}

          <div className={styles.fieldRow}>
            <div className={`${styles.field} ${styles.quantityField}`}>
              <label className={styles.label} htmlFor="item-quantity">
                Cantidad
              </label>
              <input
                id="item-quantity"
                className={styles.input}
                type="number"
                min={1}
                value={quantity}
                onChange={(event) => setQuantity(event.target.value)}
              />
            </div>
            <div className={`${styles.field} ${styles.noteField}`}>
              <label className={styles.label} htmlFor="item-note">
                Nota
              </label>
              <input
                id="item-note"
                className={styles.input}
                value={note}
                onChange={(event) => setNote(event.target.value)}
              />
            </div>
          </div>

          <button type="submit" className={styles.secondaryButton}>
            Agregar
          </button>
        </form>
      )}

      {order.status === "DRAFT" && (
        <button type="button" className={styles.primaryButton} onClick={handleSend}>
          Enviar pedido
        </button>
      )}

      {(order.status === "DRAFT" || order.status === "IN_PROGRESS") && (
        <form className={styles.card} onSubmit={handleFixTable}>
          <h2 className={styles.cardTitle}>Corregir mesa</h2>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="destination-table">
              Mesa destino
            </label>
            <select
              id="destination-table"
              className={styles.select}
              value={destinationTable}
              onChange={(event) => setDestinationTable(event.target.value)}
            >
              <option value="">Selecciona una mesa</option>
              {freeTables.map((table) => (
                <option key={table.number} value={table.number}>
                  Mesa {table.number}
                </option>
              ))}
            </select>
          </div>
          <button type="submit" className={styles.secondaryButton}>
            Guardar mesa
          </button>
        </form>
      )}
    </section>
  );
}
