"use client";

import { useCallback, useEffect, useState } from "react";
import { getMenu, type Product, type ApiErrorBody } from "@/lib/api/menu";
import { subscribeToMenuUpdates } from "@/lib/api/menuSocket";
import { formatPrice } from "@/lib/format";
import { HighlightedText, MenuSearchBar } from "./MenuSearchBar";
import searchStyles from "./MenuSearchBar.module.css";
import { useMenuSearch } from "./useMenuSearch";
import styles from "./MenuMeseroView.module.css";

function groupByCategory(products: Product[]): Array<[string, Product[]]> {
  const groups = new Map<string, Product[]>();
  for (const product of products) {
    const list = groups.get(product.category.name) ?? [];
    list.push(product);
    groups.set(product.category.name, list);
  }
  return Array.from(groups.entries());
}

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

/** Mesero's read-only menu view (T40 — RF-6, RF-7).
 *
 * Refreshes itself when the backend notifies a change over `/ws/menu/`,
 * and offers a manual "Actualizar menú" button as the backup RF-6
 * requires — both paths call the exact same refetch function, so they
 * always agree. The search bar (RF-6) highlights the matching dishes
 * without hiding the rest of the menu. */
export function MenuMeseroView() {
  const [products, setProducts] = useState<Product[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const search = useMenuSearch(products, "menu-product");

  const refresh = useCallback(async () => {
    try {
      const data = await getMenu();
      setProducts(data);
      setMessage(null);
    } catch (error) {
      setMessage(formatError(error));
    }
  }, []);

  useEffect(() => {
    refresh();
    const handle = subscribeToMenuUpdates(refresh);
    return () => handle.close();
  }, [refresh]);

  return (
    <section className={styles.section}>
      <div className={styles.headerRow}>
        <h1 className={styles.heading}>Menú</h1>
        <button type="button" className={styles.refreshButton} onClick={refresh}>
          Actualizar menú
        </button>
      </div>
      <MenuSearchBar
        inputId="menu-search"
        query={search.query}
        onQueryChange={search.setQuery}
        count={search.count}
        index={search.index}
        onNext={search.next}
        onPrevious={search.previous}
      />
      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}
      {groupByCategory(products).map(([categoryName, items]) => (
        <div className={styles.categoryGroup} key={categoryName}>
          <span className={styles.categoryLabel}>{categoryName}</span>
          <ul className={styles.list}>
            {items.map((product) => (
              <li
                key={product.id}
                id={`menu-product-${product.id}`}
                className={[
                  styles.row,
                  search.isMatch(product.id) && searchStyles.matchRow,
                  search.activeId === product.id && searchStyles.activeRow,
                ]
                  .filter(Boolean)
                  .join(" ")}
                aria-current={search.activeId === product.id ? "true" : undefined}
              >
                <span className={styles.name}>
                  <HighlightedText text={product.name} query={search.query} />
                </span>
                <span className={styles.price}>${formatPrice(product.price)}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}
