// Orders API client (T62 — RF-1 a RF-11).

import { requestJson, type ApiErrorBody } from "./client";

export type { ApiErrorBody };

export type TableStatus = "FREE" | "OCCUPIED" | "PAID";

export type Table = {
  number: number;
  status: TableStatus;
  active_order_daily_number: number | null;
};

export type OrderStatus = "DRAFT" | "IN_PROGRESS" | "CHARGED" | "VOIDED";

export type OrderItem = {
  id: number;
  order_id: number;
  name: string;
  unit_price: string;
  quantity: number;
  note: string;
  line_type: "ORIGINAL" | "ADDITION";
  is_voided: boolean;
  void_reason: string | null;
  /** 003 RF-3: quantity × unit price, computed by the backend. */
  line_total: string;
  /** 003 RF-5: an addition the waiter hasn't sent yet (waiter-only). */
  pending_send?: boolean;
  print_warning?: string | null;
};

export type ActivePayment = {
  account_name: string;
  /** 005 RF-10: items total, peso discount and what was actually paid. */
  subtotal: string;
  discount: string;
  discount_reason: string;
  amount: string;
  charged_by: string;
  charged_at: string;
};

export type Order = {
  id: number;
  /** 003 RF-18: null for a counter order ("Mostrador"). */
  table_number: number | null;
  waiter_id: number;
  waiter_username: string;
  status: OrderStatus;
  delivered: boolean;
  items: OrderItem[];
  total: string;
  /** 003 RF-5: unsent additions, kept out of `total` (waiter-only). */
  pending_additions_count?: number;
  pending_additions_total?: string;
  /** 004 RF-10: "Imprimir pedido" has something to print (waiter-only). */
  has_unprinted_changes?: boolean;
  /** 004 RF-9: a print attempt failed and is still pending. */
  has_pending_print: boolean;
  print_warning?: string | null;
  active_payment: ActivePayment | null;
  daily_number: number | null;
  sent_at: string | null;
  created_at: string;
  draft_reminder: boolean;
  /** 003 RF-17: only present in admin-only responses. */
  admin_note?: string;
};

/** RF-15: an occupied table with the order holding it (admin-only). */
export type OccupiedTable = {
  number: number;
  order: Order | null;
  is_stale: boolean;
};

export function listTables(): Promise<Table[]> {
  return requestJson<Table[]>("/api/mesas");
}

export function resizeTables(numero: number): Promise<Table[]> {
  return requestJson<Table[]>("/api/mesas/numero", {
    method: "PATCH",
    body: JSON.stringify({ numero }),
  });
}

export function listOccupiedTables(): Promise<OccupiedTable[]> {
  return requestJson<OccupiedTable[]>("/api/mesas/ocupadas");
}

export function releaseTable(tableNumber: number): Promise<Table> {
  return requestJson<Table>(`/api/mesas/${tableNumber}/liberar`, {
    method: "POST",
  });
}

/** 003 RF-2; RF-18: `null` (admin only) creates a counter order. */
export function createOrder(tableNumber: number | null): Promise<Order> {
  return requestJson<Order>("/api/pedidos", {
    method: "POST",
    body: JSON.stringify(tableNumber === null ? {} : { table_number: tableNumber }),
  });
}

export function listMyOrders(fecha?: string): Promise<Order[]> {
  const query = fecha ? `?fecha=${encodeURIComponent(fecha)}` : "";
  return requestJson<Order[]>(`/api/pedidos/mios${query}`);
}

export function listIncomingOrders(): Promise<Order[]> {
  return requestJson<Order[]>("/api/pedidos/entrantes");
}

export function getOrder(orderId: number): Promise<Order> {
  return requestJson<Order>(`/api/pedidos/${orderId}`);
}

export function deleteOrder(orderId: number): Promise<void> {
  return requestJson<void>(`/api/pedidos/${orderId}`, {
    method: "DELETE",
  });
}

export function addItem(
  orderId: number,
  item:
    | { productId: number; quantity?: number; note?: string }
    | { name: string; price: number; quantity?: number; note?: string }
): Promise<OrderItem> {
  const body: Record<string, unknown> =
    "productId" in item
      ? { product_id: item.productId }
      : { name: item.name, price: item.price };
  if (item.quantity !== undefined) body.quantity = item.quantity;
  if (item.note !== undefined) body.note = item.note;
  return requestJson<OrderItem>(`/api/pedidos/${orderId}/items`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function removeItem(orderId: number, itemId: number): Promise<void> {
  return requestJson<void>(`/api/pedidos/${orderId}/items/${itemId}`, {
    method: "DELETE",
  });
}

export function voidItem(
  orderId: number,
  itemId: number,
  reason: string
): Promise<OrderItem> {
  return requestJson<OrderItem>(
    `/api/pedidos/${orderId}/items/${itemId}/anular`,
    {
      method: "POST",
      body: JSON.stringify({ reason }),
    }
  );
}

export function updateItemNote(
  orderId: number,
  itemId: number,
  note: string
): Promise<OrderItem> {
  return requestJson<OrderItem>(`/api/pedidos/${orderId}/items/${itemId}/nota`, {
    method: "PATCH",
    body: JSON.stringify({ note }),
  });
}

/** 003 RF-5: "Crear pedido" — into the system, without printing. */
export function sendOrder(orderId: number): Promise<Order> {
  return requestJson<Order>(`/api/pedidos/${orderId}/enviar`, {
    method: "POST",
  });
}

/** 003 RF-5: the pending additions reach the admin, without printing. */
export function sendAdditions(orderId: number): Promise<Order> {
  return requestJson<Order>(`/api/pedidos/${orderId}/enviar-adicion`, {
    method: "POST",
  });
}

/** 004 RF-1: "Imprimir pedido" — sends pending additions, then prints
 * everything not on paper yet in a single ticket. */
export function printOrder(orderId: number): Promise<Order> {
  return requestJson<Order>(`/api/pedidos/${orderId}/imprimir`, {
    method: "POST",
  });
}

export function fixTable(orderId: number, tableNumber: number): Promise<Order> {
  return requestJson<Order>(`/api/pedidos/${orderId}/mesa`, {
    method: "POST",
    body: JSON.stringify({ table_number: tableNumber }),
  });
}

export function setDelivered(
  orderId: number,
  delivered: boolean
): Promise<Order> {
  return requestJson<Order>(`/api/pedidos/${orderId}/entregado`, {
    method: "POST",
    body: JSON.stringify({ delivered }),
  });
}

export function chargeOrder(
  orderId: number,
  accountId: number,
  discount?: { amount: number; reason: string },
  expectedTotal?: string
): Promise<Order> {
  const body = {
    account_id: accountId,
    ...(discount ? { discount: discount.amount, discount_reason: discount.reason } : {}),
    // 005 RF-12: the total on screen; the backend refuses if it changed.
    ...(expectedTotal !== undefined ? { expected_total: expectedTotal } : {}),
  };
  return requestJson<Order>(`/api/pedidos/${orderId}/cobrar`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** 003 RF-17: the admin's own note on an order. */
export function setAdminNote(orderId: number, note: string): Promise<Order> {
  return requestJson<Order>(`/api/pedidos/${orderId}/nota-admin`, {
    method: "PATCH",
    body: JSON.stringify({ note }),
  });
}

export function voidOrder(orderId: number, reason: string): Promise<Order> {
  return requestJson<Order>(`/api/pedidos/${orderId}/anular`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

/** RF-15: admin-only one-click discard of a draft (traced as a void). */
export function discardDraft(orderId: number): Promise<Order> {
  return requestJson<Order>(`/api/pedidos/${orderId}/eliminar-borrador`, {
    method: "POST",
  });
}

export function reprintOrder(orderId: number): Promise<Order> {
  return requestJson<Order>(`/api/pedidos/${orderId}/reimpresion`, {
    method: "POST",
  });
}

export function listChargedOrders(fecha?: string): Promise<Order[]> {
  const query = fecha ? `?fecha=${encodeURIComponent(fecha)}` : "";
  return requestJson<Order[]>(`/api/pedidos/cobrados${query}`);
}
