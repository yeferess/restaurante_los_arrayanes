// Read-only statistics API client (006-estadisticas, RF-1 a RF-6).

import { requestJson, type ApiErrorBody } from "./client";

export type { ApiErrorBody };

export type MoneyByAccount = { account_name: string; total: string };
export type OrdersByWaiter = { waiter_username: string; orders_sent: number };
export type TopProduct = { product_name: string; quantity: number };

export type DaySummary = {
  date: string;
  money_total: string;
  orders_charged_count: number;
  money_by_account: MoneyByAccount[];
  orders_by_waiter: OrdersByWaiter[];
  top_products: TopProduct[];
};

export type RangeSummary = {
  from: string;
  to: string;
  money_total: string;
  orders_sent_count: number;
  money_by_account: MoneyByAccount[];
  orders_by_waiter: OrdersByWaiter[];
  top_products: TopProduct[];
};

export type DayMovementOrder = {
  daily_number: number | null;
  waiter: string;
  status: "DRAFT" | "IN_PROGRESS" | "CHARGED" | "VOIDED";
  total: string;
};

export type DayMovementPayment = {
  account_name: string;
  amount: string;
  charged_by: string;
  charged_at: string;
  status: "ACTIVE" | "VOIDED";
};

export type DayMovement = {
  date: string;
  orders: DayMovementOrder[];
  payments: DayMovementPayment[];
};

export function getDaySummary(date?: string): Promise<DaySummary> {
  const query = date ? `?date=${date}` : "";
  return requestJson<DaySummary>(`/api/estadisticas/resumen${query}`);
}

export function getRangeSummary(from: string, to: string): Promise<RangeSummary> {
  return requestJson<RangeSummary>(
    `/api/estadisticas/rango?from=${from}&to=${to}`
  );
}

export function getDayMovement(date?: string): Promise<DayMovement> {
  const query = date ? `?date=${date}` : "";
  return requestJson<DayMovement>(`/api/estadisticas/movimiento${query}`);
}
