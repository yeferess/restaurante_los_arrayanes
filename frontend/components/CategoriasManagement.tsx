"use client";

import { useEffect, useState, type FormEvent } from "react";
import {
  listCategories,
  createCategory,
  renameCategory,
  deleteCategory,
  type Category,
  type ApiErrorBody,
} from "@/lib/api/menu";
import styles from "./CategoriasManagement.module.css";

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

/** Category management screen (T38 — RF-1): create, rename and delete
 * categories. Renaming/deleting act on the loaded list, not on a
 * manually-typed id — the admin never has to remember category ids. */
export function CategoriasManagement() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [newName, setNewName] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [renameDrafts, setRenameDrafts] = useState<Record<number, string>>({});

  async function refresh() {
    const data = await listCategories();
    setCategories(data);
    setRenameDrafts(Object.fromEntries(data.map((c) => [c.id, c.name])));
  }

  useEffect(() => {
    refresh().catch((error) => setMessage(formatError(error)));
  }, []);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      await createCategory(newName);
      setNewName("");
      await refresh();
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  async function handleRename(categoryId: number) {
    setMessage(null);
    try {
      await renameCategory(categoryId, renameDrafts[categoryId] ?? "");
      await refresh();
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  async function handleDelete(categoryId: number) {
    setMessage(null);
    try {
      await deleteCategory(categoryId);
      await refresh();
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <section>
      <h1 className={styles.heading}>Gestión de categorías</h1>
      <form className={styles.createForm} onSubmit={handleCreate}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="new-category-name">
            Nueva categoría
          </label>
          <input
            id="new-category-name"
            className={styles.input}
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            required
          />
        </div>
        <button type="submit" className={styles.primaryButton}>
          Crear categoría
        </button>
      </form>
      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}
      <ul className={styles.list}>
        {categories.map((category) => (
          <li key={category.id} className={styles.row}>
            <label className={styles.rowLabel} htmlFor={`rename-category-${category.id}`}>
              Nombre
            </label>
            <input
              id={`rename-category-${category.id}`}
              className={styles.rowInput}
              value={renameDrafts[category.id] ?? ""}
              onChange={(e) =>
                setRenameDrafts((prev) => ({ ...prev, [category.id]: e.target.value }))
              }
            />
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={() => handleRename(category.id)}
            >
              Renombrar
            </button>
            <button
              type="button"
              className={styles.dangerButton}
              onClick={() => handleDelete(category.id)}
            >
              Eliminar
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
