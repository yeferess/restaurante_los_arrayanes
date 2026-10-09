// Menu API client (T36 — RF-1, RF-2, RF-3, RF-4, RF-5, RF-7).

import { requestJson, type ApiErrorBody } from "./client";

export type { ApiErrorBody };

export type Category = {
  id: number;
  name: string;
};

export type Product = {
  id: number;
  name: string;
  category: Category;
  price: string;
  is_available: boolean;
};

export function listCategories(): Promise<Category[]> {
  return requestJson<Category[]>("/api/menu/categorias");
}

export function createCategory(name: string): Promise<Category> {
  return requestJson<Category>("/api/menu/categorias", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function renameCategory(categoryId: number, name: string): Promise<Category> {
  return requestJson<Category>(`/api/menu/categorias/${categoryId}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}

export function deleteCategory(categoryId: number): Promise<void> {
  return requestJson<void>(`/api/menu/categorias/${categoryId}`, {
    method: "DELETE",
  });
}

export function listProducts(): Promise<Product[]> {
  return requestJson<Product[]>("/api/menu/productos");
}

export function createProduct(
  name: string,
  categoryId: number,
  price: number,
  isAvailable?: boolean
): Promise<Product> {
  return requestJson<Product>("/api/menu/productos", {
    method: "POST",
    body: JSON.stringify({
      name,
      category_id: categoryId,
      price,
      ...(isAvailable === undefined ? {} : { is_available: isAvailable }),
    }),
  });
}

export function updateProduct(
  productId: number,
  changes: { name?: string; categoryId?: number; price?: number }
): Promise<Product> {
  const body: Record<string, unknown> = {};
  if (changes.name !== undefined) body.name = changes.name;
  if (changes.categoryId !== undefined) body.category_id = changes.categoryId;
  if (changes.price !== undefined) body.price = changes.price;
  return requestJson<Product>(`/api/menu/productos/${productId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function setProductAvailability(
  productId: number,
  isAvailable: boolean
): Promise<Product> {
  return requestJson<Product>(`/api/menu/productos/${productId}/disponibilidad`, {
    method: "POST",
    body: JSON.stringify({ is_available: isAvailable }),
  });
}

export function deleteProduct(productId: number): Promise<void> {
  return requestJson<void>(`/api/menu/productos/${productId}`, {
    method: "DELETE",
  });
}

export function getMenu(): Promise<Product[]> {
  return requestJson<Product[]>("/api/menu");
}
