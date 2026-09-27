import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  listCategories,
  createCategory,
  renameCategory,
  deleteCategory,
  listProducts,
  createProduct,
  updateProduct,
  setProductAvailability,
  deleteProduct,
  getMenu,
} from "./menu";

describe("lib/api/menu (T36, RF-1/2/3/4/5/7)", () => {
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

  it("listCategories gets /api/menu/categorias", async () => {
    mockOk([{ id: 1, name: "Bebidas" }]);
    const result = await listCategories();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/menu/categorias"),
      expect.objectContaining({ credentials: "include" })
    );
    expect(result).toEqual([{ id: 1, name: "Bebidas" }]);
  });

  it("createCategory posts the name and propagates a 409 duplicate error", async () => {
    mockOk({ id: 1, name: "Bebidas" }, 201);
    await createCategory("Bebidas");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/menu/categorias"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ name: "Bebidas" }),
      })
    );

    mockError({ detail: "Ya existe una categoría con ese nombre." }, 409);
    await expect(createCategory("Bebidas")).rejects.toEqual({
      detail: "Ya existe una categoría con ese nombre.",
    });
  });

  it("renameCategory patches /api/menu/categorias/{id}", async () => {
    mockOk({ id: 1, name: "Refrescos" });
    await renameCategory(1, "Refrescos");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/menu/categorias/1"),
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ name: "Refrescos" }),
      })
    );
  });

  it("deleteCategory deletes /api/menu/categorias/{id} and propagates a 409", async () => {
    mockError(
      { detail: "Reasigna los productos de esta categoría antes de eliminarla." },
      409
    );
    await expect(deleteCategory(1)).rejects.toEqual({
      detail: "Reasigna los productos de esta categoría antes de eliminarla.",
    });
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/menu/categorias/1"),
      expect.objectContaining({ method: "DELETE" })
    );
  });

  it("listProducts gets /api/menu/productos", async () => {
    mockOk([
      {
        id: 1,
        name: "Limonada",
        category: { id: 1, name: "Bebidas" },
        price: "4.50",
        is_available: true,
      },
    ]);
    const result = await listProducts();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/menu/productos"),
      expect.objectContaining({ credentials: "include" })
    );
    expect(result[0].name).toBe("Limonada");
  });

  it("createProduct posts name/category_id/price", async () => {
    mockOk(
      {
        id: 1,
        name: "Limonada",
        category: { id: 1, name: "Bebidas" },
        price: "4.50",
        is_available: true,
      },
      201
    );
    await createProduct("Limonada", 1, 4.5);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/menu/productos"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ name: "Limonada", category_id: 1, price: 4.5 }),
      })
    );
  });

  it("createProduct includes is_available only when explicitly provided", async () => {
    mockOk(
      {
        id: 1,
        name: "Limonada",
        category: { id: 1, name: "Bebidas" },
        price: "4.50",
        is_available: false,
      },
      201
    );
    await createProduct("Limonada", 1, 4.5, false);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/menu/productos"),
      expect.objectContaining({
        body: JSON.stringify({
          name: "Limonada",
          category_id: 1,
          price: 4.5,
          is_available: false,
        }),
      })
    );
  });

  it("updateProduct patches only the provided fields", async () => {
    mockOk({
      id: 1,
      name: "Limonada natural",
      category: { id: 2, name: "Postres" },
      price: "5.50",
      is_available: true,
    });
    await updateProduct(1, { name: "Limonada natural" });
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/menu/productos/1"),
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ name: "Limonada natural" }),
      })
    );
  });

  it("updateProduct propagates a duplicate-name 409", async () => {
    mockError({ detail: "Ya existe un producto con ese nombre." }, 409);
    await expect(updateProduct(1, { name: "Te helado" })).rejects.toEqual({
      detail: "Ya existe un producto con ese nombre.",
    });
  });

  it("setProductAvailability posts is_available to the disponibilidad endpoint", async () => {
    mockOk({
      id: 1,
      name: "Limonada",
      category: { id: 1, name: "Bebidas" },
      price: "4.50",
      is_available: false,
    });
    await setProductAvailability(1, false);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/menu/productos/1/disponibilidad"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ is_available: false }),
      })
    );
  });

  it("deleteProduct deletes /api/menu/productos/{id}", async () => {
    mockOk(undefined, 204);
    await deleteProduct(1);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/menu/productos/1"),
      expect.objectContaining({ method: "DELETE" })
    );
  });

  it("getMenu gets /api/menu", async () => {
    mockOk([
      {
        id: 1,
        name: "Limonada",
        category: { id: 1, name: "Bebidas" },
        price: "4.50",
        is_available: true,
      },
    ]);
    const result = await getMenu();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/menu"),
      expect.objectContaining({ credentials: "include" })
    );
    expect(result).toHaveLength(1);
  });
});
