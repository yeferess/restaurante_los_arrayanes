// Payment accounts catalog + charge correction API client (005-cobro).

import { requestJson, type ApiErrorBody } from "./client";
import type { Order } from "./orders";

export type { ApiErrorBody };

export type PaymentAccount = {
  id: number;
  name: string;
  is_fixed: boolean;
};

export function listAccounts(): Promise<PaymentAccount[]> {
  return requestJson<PaymentAccount[]>("/api/cuentas-pago");
}

export function createAccount(name: string): Promise<PaymentAccount> {
  return requestJson<PaymentAccount>("/api/cuentas-pago", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function deleteAccount(accountId: number): Promise<void> {
  return requestJson<void>(`/api/cuentas-pago/${accountId}`, {
    method: "DELETE",
  });
}

/** 005 RF-10: what charging with this peso discount would produce. */
export type ChargePreview = { subtotal: string; discount: string; total: string };

export function previewCharge(orderId: number, discount: number): Promise<ChargePreview> {
  return requestJson<ChargePreview>(`/api/pedidos/${orderId}/cobro/previsualizar`, {
    method: "POST",
    body: JSON.stringify({ discount }),
  });
}

/** 005 RF-11: print the customer receipt of a charged order. */
export function printReceipt(orderId: number): Promise<{ print_warning: string | null }> {
  return requestJson<{ print_warning: string | null }>(
    `/api/pedidos/${orderId}/comprobante`,
    { method: "POST" }
  );
}

/** 005 RF-13: print the bill of an order still to be paid, with the
 * discount typed in the charge window. Charges nothing. */
export function printBill(
  orderId: number,
  discount?: number
): Promise<{ print_warning: string | null }> {
  return requestJson<{ print_warning: string | null }>(`/api/pedidos/${orderId}/cuenta`, {
    method: "POST",
    body: JSON.stringify(discount === undefined ? {} : { discount }),
  });
}

export function voidCharge(orderId: number, reason: string): Promise<Order> {
  return requestJson<Order>(`/api/pedidos/${orderId}/cobro/anular`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}
