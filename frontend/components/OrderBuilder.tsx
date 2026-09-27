"use client";

import { useEffect, useState, type FormEvent } from "react";
import {
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

  async function handleAddItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      if (mode === "catalog") {
        await addItem(orderId, {
          productId: Number(productId),
          quantity: Number(quantity),
          note: note || undefined,
        });
      } else {
        await addItem(orderId, {
          name: offMenuName,
          price: Number(offMenuPrice),
          quantity: Number(quantity),
          note: note || undefined,
        });
      }
      setOffMenuName("");
      setOffMenuPrice("");
      setQuantity("1");
      setNote("");
      await refresh();
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  async function handleSend() {
    setMessage(null);
    try {
      const updated = await sendOrder(orderId);
      setOrder(updated);
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  async function handleVoidItem(itemId: number) {
    const reason = window.prompt("Motivo de la anulación:");
    if (!reason) return;
    setMessage(null);
    try {
      await voidItem(orderId, itemId, reason);
      await refresh();
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
    <section>
      <h1>
        Pedido {order.id} — Mesa {order.table_number}
      </h1>
      {message && <p role="status">{message}</p>}

      <ul>
        {order.items.map((item) => (
          <li key={item.id}>
            {item.quantity}x {item.name} — ${item.unit_price}
            {item.note && <span> ({item.note})</span>}
            {item.is_voided && <span> [anulado]</span>}
            {!item.is_voided && order.status === "IN_PROGRESS" && (
              <button type="button" onClick={() => handleVoidItem(item.id)}>
                Anular
              </button>
            )}
          </li>
        ))}
      </ul>

      {(order.status === "DRAFT" || order.status === "IN_PROGRESS") && (
        <form onSubmit={handleAddItem}>
          <h2>Agregar ítem</h2>
          <label>
            <input
              type="radio"
              checked={mode === "catalog"}
              onChange={() => setMode("catalog")}
            />
            Del menú
          </label>
          <label>
            <input
              type="radio"
              checked={mode === "off-menu"}
              onChange={() => setMode("off-menu")}
            />
            Fuera de carta
          </label>

          {mode === "catalog" ? (
            <>
              <label htmlFor="product-select">Producto</label>
              <select
                id="product-select"
                value={productId}
                onChange={(event) => setProductId(event.target.value)}
              >
                {products.map((product) => (
                  <option key={product.id} value={product.id}>
                    {product.name}
                  </option>
                ))}
              </select>
            </>
          ) : (
            <>
              <label htmlFor="off-menu-name">Nombre</label>
              <input
                id="off-menu-name"
                value={offMenuName}
                onChange={(event) => setOffMenuName(event.target.value)}
              />
              <label htmlFor="off-menu-price">Precio</label>
              <input
                id="off-menu-price"
                type="number"
                step="0.01"
                value={offMenuPrice}
                onChange={(event) => setOffMenuPrice(event.target.value)}
              />
            </>
          )}

          <label htmlFor="item-quantity">Cantidad</label>
          <input
            id="item-quantity"
            type="number"
            min={1}
            value={quantity}
            onChange={(event) => setQuantity(event.target.value)}
          />

          <label htmlFor="item-note">Nota</label>
          <input
            id="item-note"
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />

          <button type="submit">Agregar</button>
        </form>
      )}

      {order.status === "DRAFT" && (
        <button type="button" onClick={handleSend}>
          Enviar pedido
        </button>
      )}

      {(order.status === "DRAFT" || order.status === "IN_PROGRESS") && (
        <form onSubmit={handleFixTable}>
          <h2>Corregir mesa</h2>
          <label htmlFor="destination-table">Mesa destino</label>
          <select
            id="destination-table"
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
          <button type="submit">Guardar mesa</button>
        </form>
      )}
    </section>
  );
}
