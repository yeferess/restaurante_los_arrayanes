import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  listTables,
  resizeTables,
  releaseTable,
  createOrder,
  listMyOrders,
  listIncomingOrders,
  getOrder,
  addItem,
  removeItem,
  voidItem,
  updateItemNote,
  sendOrder,
  fixTable,
  setDelivered,
  chargeOrder,
  voidOrder,
} from "./orders";

describe("lib/api/orders (T62, RF-1 a RF-11)", () => {
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

  it("listTables gets /api/mesas", async () => {
    mockOk([{ number: 1, status: "FREE" }]);
    const result = await listTables();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/mesas"),
      expect.objectContaining({ credentials: "include" })
    );
    expect(result[0].number).toBe(1);
  });

  it("resizeTables patches /api/mesas/numero and propagates a 409", async () => {
    mockOk([{ number: 1, status: "FREE" }]);
    await resizeTables(3);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/mesas/numero"),
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ numero: 3 }),
      })
    );

    mockError({ detail: "Alguna de las mesas a eliminar no está libre." }, 409);
    await expect(resizeTables(1)).rejects.toEqual({
      detail: "Alguna de las mesas a eliminar no está libre.",
    });
  });

  it("releaseTable posts to /api/mesas/{numero}/liberar", async () => {
    mockOk({ number: 1, status: "FREE" });
    await releaseTable(1);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/mesas/1/liberar"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("createOrder posts table_number to /api/pedidos and propagates a 409", async () => {
    mockOk({ id: 1, table_number: 1, status: "DRAFT" }, 201);
    await createOrder(1);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/pedidos"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ table_number: 1 }),
      })
    );

    mockError({ detail: "La mesa no está libre." }, 409);
    await expect(createOrder(1)).rejects.toEqual({
      detail: "La mesa no está libre.",
    });
  });

  it("listMyOrders gets /api/pedidos/mios", async () => {
    mockOk([{ id: 1, status: "DRAFT" }]);
    await listMyOrders();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/pedidos/mios"),
      expect.objectContaining({ credentials: "include" })
    );
  });

  it("listIncomingOrders gets /api/pedidos/entrantes", async () => {
    mockOk([{ id: 1, status: "IN_PROGRESS" }]);
    await listIncomingOrders();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/pedidos/entrantes"),
      expect.objectContaining({ credentials: "include" })
    );
  });

  it("getOrder gets /api/pedidos/{id}", async () => {
    mockOk({ id: 7, status: "DRAFT" });
    await getOrder(7);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/pedidos/7"),
      expect.objectContaining({ credentials: "include" })
    );
  });

  it("addItem posts product_id for a catalog item", async () => {
    mockOk({ id: 1, name: "Limonada" }, 201);
    await addItem(7, { productId: 3, quantity: 2, note: "sin azúcar" });
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/pedidos/7/items"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          product_id: 3,
          quantity: 2,
          note: "sin azúcar",
        }),
      })
    );
  });

  it("addItem posts name/price for an off-menu item and propagates a 409", async () => {
    mockOk({ id: 2, name: "Postre especial" }, 201);
    await addItem(7, { name: "Postre especial", price: 6 });
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/pedidos/7/items"),
      expect.objectContaining({
        body: JSON.stringify({ name: "Postre especial", price: 6 }),
      })
    );

    mockError({ detail: "El producto ya no está disponible." }, 409);
    await expect(addItem(7, { productId: 3 })).rejects.toEqual({
      detail: "El producto ya no está disponible.",
    });
  });

  it("removeItem deletes /api/pedidos/{id}/items/{item_id}", async () => {
    mockOk(undefined, 204);
    await removeItem(7, 1);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/pedidos/7/items/1"),
      expect.objectContaining({ method: "DELETE" })
    );
  });

  it("voidItem posts the reason and propagates a 400 when missing", async () => {
    mockOk({ id: 1, is_voided: true }, 200);
    await voidItem(7, 1, "Pedido por error");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/pedidos/7/items/1/anular"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ reason: "Pedido por error" }),
      })
    );

    mockError({ detail: "El motivo es obligatorio." }, 400);
    await expect(voidItem(7, 1, "")).rejects.toEqual({
      detail: "El motivo es obligatorio.",
    });
  });

  it("updateItemNote patches the note", async () => {
    mockOk({ id: 1, note: "sin azúcar" });
    await updateItemNote(7, 1, "sin azúcar");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/pedidos/7/items/1/nota"),
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ note: "sin azúcar" }),
      })
    );
  });

  it("sendOrder posts to /api/pedidos/{id}/enviar and propagates a 409", async () => {
    mockOk({ id: 7, status: "IN_PROGRESS" });
    await sendOrder(7);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/pedidos/7/enviar"),
      expect.objectContaining({ method: "POST" })
    );

    mockError({ detail: "El pedido no tiene ningún ítem." }, 409);
    await expect(sendOrder(7)).rejects.toEqual({
      detail: "El pedido no tiene ningún ítem.",
    });
  });

  it("fixTable posts the destination table_number", async () => {
    mockOk({ id: 7, table_number: 2 });
    await fixTable(7, 2);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/pedidos/7/mesa"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ table_number: 2 }),
      })
    );
  });

  it("setDelivered posts the delivered flag", async () => {
    mockOk({ id: 7, delivered: true });
    await setDelivered(7, true);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/pedidos/7/entregado"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ delivered: true }),
      })
    );
  });

  it("chargeOrder posts to /api/pedidos/{id}/cobrar and propagates a 409", async () => {
    mockOk({ id: 7, status: "CHARGED" });
    await chargeOrder(7);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/pedidos/7/cobrar"),
      expect.objectContaining({ method: "POST" })
    );

    mockError({ detail: "La mesa no está ocupada." }, 409);
    await expect(chargeOrder(7)).rejects.toEqual({
      detail: "La mesa no está ocupada.",
    });
  });

  it("voidOrder posts the reason to /api/pedidos/{id}/anular", async () => {
    mockOk({ id: 7, status: "VOIDED" });
    await voidOrder(7, "Cliente se fue");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/pedidos/7/anular"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ reason: "Cliente se fue" }),
      })
    );
  });
});
