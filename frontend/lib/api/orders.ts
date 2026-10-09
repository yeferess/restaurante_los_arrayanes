// Orders API client (T62 — RF-1 a RF-11).

import { requestJson, type ApiErrorBody } from "./client";

export type { ApiErrorBody };

export type TableStatus = "FREE" | "OCCUPIED" | "PAID";

export type Table = {
  number: number;
  status: TableStatus;
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
  print_warning?: string | null;
};

export type ActivePayment = {
  account_name: string;
  amount: string;
  charged_by: string;
  charged_at: string;
};

export type Order = {
  id: number;
  table_number: number;
  waiter_id: number;
  status: OrderStatus;
  delivered: boolean;
  items: OrderItem[];
  total: string;
  has_pending_print: boolean;
  print_warning?: string | null;
  active_payment: ActivePayment | null;
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

export function releaseTable(tableNumber: number): Promise<Table> {
  return requestJson<Table>(`/api/mesas/${tableNumber}/liberar`, {
    method: "POST",
  });
}

export function createOrder(tableNumber: number): Promise<Order> {
  return requestJson<Order>("/api/pedidos", {
    method: "POST",
    body: JSON.stringify({ table_number: tableNumber }),
  });
}

export function listMyOrders(): Promise<Order[]> {
  return requestJson<Order[]>("/api/pedidos/mios");
}

export function listIncomingOrders(): Promise<Order[]> {
  return requestJson<Order[]>("/api/pedidos/entrantes");
}

export function getOrder(orderId: number): Promise<Order> {
  return requestJson<Order>(`/api/pedidos/${orderId}`);
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

export function sendOrder(orderId: number): Promise<Order> {
  return requestJson<Order>(`/api/pedidos/${orderId}/enviar`, {
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

export function chargeOrder(orderId: number, accountId: number): Promise<Order> {
  return requestJson<Order>(`/api/pedidos/${orderId}/cobrar`, {
    method: "POST",
    body: JSON.stringify({ account_id: accountId }),
  });
}

export function voidOrder(orderId: number, reason: string): Promise<Order> {
  return requestJson<Order>(`/api/pedidos/${orderId}/anular`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function retryPrint(orderId: number): Promise<Order> {
  return requestJson<Order>(`/api/pedidos/${orderId}/reimprimir`, {
    method: "POST",
  });
}
