import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  listAccounts,
  createAccount,
  deleteAccount,
  voidCharge,
  previewCharge,
  printReceipt,
  printBill,
} from "./payments";

describe("lib/api/payments (005-cobro, RF-2, RF-6)", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  function mockOk(body: unknown, status = 200) {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(body === undefined ? null : JSON.stringify(body), { status })
    );
  }

  function mockError(body: unknown, status: number) {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(JSON.stringify(body), { status })
    );
  }

  it("previewCharge posts the discount (RF-10)", async () => {
    mockOk({ subtotal: "55000.00", discount: "5000", total: "50000.00" });
    const result = await previewCharge(7, 5000);
    const [url, init] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain("/api/pedidos/7/cobro/previsualizar");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ discount: 5000 });
    expect(result.total).toBe("50000.00");
  });

  it("printReceipt posts /api/pedidos/{id}/comprobante (RF-11)", async () => {
    mockOk({ print_warning: null });
    const result = await printReceipt(7);
    const [url, init] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain("/api/pedidos/7/comprobante");
    expect(init.method).toBe("POST");
    expect(result.print_warning).toBeNull();
  });

  it("printBill posts /api/pedidos/{id}/cuenta with the discount (RF-13)", async () => {
    mockOk({ print_warning: null });
    await printBill(7, 5000);
    const [url, init] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain("/api/pedidos/7/cuenta");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ discount: 5000 });
  });

  it("printBill sends no discount when there is none (RF-13)", async () => {
    mockOk({ print_warning: null });
    await printBill(7);
    const [, init] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(JSON.parse(init.body)).toEqual({});
  });

  it("listAccounts gets /api/cuentas-pago", async () => {
    mockOk([{ id: 1, name: "Efectivo", is_fixed: true }]);
    const result = await listAccounts();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/cuentas-pago"),
      expect.objectContaining({ credentials: "include" })
    );
    expect(result[0].name).toBe("Efectivo");
  });

  it("createAccount posts the name and propagates a 409", async () => {
    mockOk({ id: 2, name: "Nequi #1234", is_fixed: false }, 201);
    await createAccount("Nequi #1234");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/cuentas-pago"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ name: "Nequi #1234" }),
      })
    );

    mockError({ detail: "Ya existe una cuenta con ese nombre." }, 409);
    await expect(createAccount("Nequi #1234")).rejects.toEqual({
      detail: "Ya existe una cuenta con ese nombre.",
    });
  });

  it("deleteAccount deletes /api/cuentas-pago/{id} and propagates a 409", async () => {
    mockOk(undefined, 204);
    await deleteAccount(2);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/cuentas-pago/2"),
      expect.objectContaining({ method: "DELETE" })
    );

    mockError({ detail: "Esta cuenta ya se usó en un cobro." }, 409);
    await expect(deleteAccount(2)).rejects.toEqual({
      detail: "Esta cuenta ya se usó en un cobro.",
    });
  });

  it("voidCharge posts the reason and propagates a 409", async () => {
    mockOk({ id: 7, status: "IN_PROGRESS", active_payment: null });
    await voidCharge(7, "Cuenta equivocada");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/pedidos/7/cobro/anular"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ reason: "Cuenta equivocada" }),
      })
    );

    mockError(
      { detail: "La mesa ya tiene un pedido nuevo; no se puede anular este cobro." },
      409
    );
    await expect(voidCharge(7, "motivo")).rejects.toEqual({
      detail: "La mesa ya tiene un pedido nuevo; no se puede anular este cobro.",
    });
  });
});
