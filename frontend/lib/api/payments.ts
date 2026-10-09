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

export function voidCharge(orderId: number, reason: string): Promise<Order> {
  return requestJson<Order>(`/api/pedidos/${orderId}/cobro/anular`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}
