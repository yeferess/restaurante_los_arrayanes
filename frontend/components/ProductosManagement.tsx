"use client";

import { useEffect, useState, type FormEvent } from "react";
import {
  listCategories,
  listProducts,
  createProduct,
  updateProduct,
  setProductAvailability,
  deleteProduct,
  type Category,
  type Product,
  type ApiErrorBody,
} from "@/lib/api/menu";
import searchStyles from "./MenuSearchBar.module.css";
import { MenuSearchBar } from "./MenuSearchBar";
import { useMenuSearch } from "./useMenuSearch";
import styles from "./ProductosManagement.module.css";

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

type ProductDraft = { name: string; categoryId: string; price: string };

function draftFrom(product: Product): ProductDraft {
  return {
    name: product.name,
    categoryId: String(product.category.id),
    price: product.price,
  };
}

/** Product management screen (T39 — RF-2, RF-3, RF-4, RF-5). The
 * category is always chosen from a `<select>` populated by
 * `GET /api/menu/categorias` — it's never a free-text field (RF-2). */
export function ProductosManagement() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  const [newName, setNewName] = useState("");
  const [newCategoryId, setNewCategoryId] = useState("");
  const [newPrice, setNewPrice] = useState("");

  const [drafts, setDrafts] = useState<Record<number, ProductDraft>>({});
  // 002 RF-9: highlights the product by its saved name, never hides rows.
  const search = useMenuSearch(products, "admin-product");

  async function refresh() {
    const [categoryList, productList] = await Promise.all([
      listCategories(),
      listProducts(),
    ]);
    setCategories(categoryList);
    setProducts(productList);
    setDrafts(Object.fromEntries(productList.map((p) => [p.id, draftFrom(p)])));
    setNewCategoryId((current) => current || String(categoryList[0]?.id ?? ""));
  }

  useEffect(() => {
    refresh().catch((error) => setMessage(formatError(error)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      await createProduct(newName, Number(newCategoryId), Number(newPrice));
      setNewName("");
      setNewPrice("");
      await refresh();
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  async function handleSave(productId: number) {
    setMessage(null);
    const draft = drafts[productId];
    try {
      await updateProduct(productId, {
        name: draft.name,
        categoryId: Number(draft.categoryId),
        price: Number(draft.price),
      });
      await refresh();
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  async function handleToggleAvailability(product: Product) {
    setMessage(null);
    try {
      await setProductAvailability(product.id, !product.is_available);
      await refresh();
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  async function handleDelete(productId: number) {
    setMessage(null);
    try {
      await deleteProduct(productId);
      await refresh();
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  function updateDraft(productId: number, changes: Partial<ProductDraft>) {
    setDrafts((prev) => ({ ...prev, [productId]: { ...prev[productId], ...changes } }));
  }

  return (
    <section>
      <h1 className={styles.heading}>Gestión de productos</h1>
      {categories.length === 0 ? (
        <p className={styles.message} role="status">
          Crea al menos una categoría antes de agregar productos.
        </p>
      ) : (
        <form className={styles.createForm} onSubmit={handleCreate}>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="new-product-name">
              Nombre del producto
            </label>
            <input
              id="new-product-name"
              className={styles.input}
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              required
            />
          </div>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="new-product-category">
              Categoría
            </label>
            <select
              id="new-product-category"
              className={styles.select}
              value={newCategoryId}
              onChange={(e) => setNewCategoryId(e.target.value)}
              required
            >
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </div>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="new-product-price">
              Precio
            </label>
            <input
              id="new-product-price"
              className={`${styles.input} ${styles.priceInput}`}
              type="number"
              step="0.01"
              value={newPrice}
              onChange={(e) => setNewPrice(e.target.value)}
              required
            />
          </div>
          <button type="submit" className={styles.primaryButton}>
            Crear producto
          </button>
        </form>
      )}
      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}
      <MenuSearchBar
        inputId="admin-menu-search"
        query={search.query}
        onQueryChange={search.setQuery}
        count={search.count}
        index={search.index}
        onNext={search.next}
        onPrevious={search.previous}
      />
      <ul className={styles.list}>
        {products.map((product) => {
          const draft = drafts[product.id] ?? draftFrom(product);
          return (
            <li
              key={product.id}
              id={`admin-product-${product.id}`}
              className={[
                styles.row,
                search.isMatch(product.id) && searchStyles.matchRow,
                search.activeId === product.id && searchStyles.activeRow,
              ]
                .filter(Boolean)
                .join(" ")}
              aria-current={search.activeId === product.id ? "true" : undefined}
            >
              <label className={styles.rowLabel} htmlFor={`product-name-${product.id}`}>
                Nombre ({product.name})
              </label>
              <input
                id={`product-name-${product.id}`}
                className={`${styles.rowInput} ${styles.rowNameInput}`}
                value={draft.name}
                onChange={(e) => updateDraft(product.id, { name: e.target.value })}
              />
              <label className={styles.rowLabel} htmlFor={`product-category-${product.id}`}>
                Categoría ({product.name})
              </label>
              <select
                id={`product-category-${product.id}`}
                className={styles.rowSelect}
                value={draft.categoryId}
                onChange={(e) => updateDraft(product.id, { categoryId: e.target.value })}
              >
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
              <label className={styles.rowLabel} htmlFor={`product-price-${product.id}`}>
                Precio ({product.name})
              </label>
              <input
                id={`product-price-${product.id}`}
                className={`${styles.rowInput} ${styles.rowPriceInput}`}
                type="number"
                step="0.01"
                value={draft.price}
                onChange={(e) => updateDraft(product.id, { price: e.target.value })}
              />
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => handleSave(product.id)}
              >
                Guardar
              </button>
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => handleToggleAvailability(product)}
              >
                {product.is_available ? "Marcar no disponible" : "Marcar disponible"}
              </button>
              <button
                type="button"
                className={styles.dangerButton}
                onClick={() => handleDelete(product.id)}
              >
                Eliminar
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
