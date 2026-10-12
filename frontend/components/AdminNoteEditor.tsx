"use client";

import { useState, type FormEvent } from "react";
import { setAdminNote, type Order, type ApiErrorBody } from "@/lib/api/orders";
import styles from "./AdminNoteEditor.module.css";

const NOTE_MAX_LENGTH = 300;

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

/** 003 RF-17: the admin's own note on an order — never shown to waiters,
 * never printed. Used in the incoming and charged orders panels. */
export function AdminNoteEditor({
  order,
  onSaved,
}: {
  order: Order;
  onSaved?: (order: Order) => void;
}) {
  const [note, setNote] = useState(order.admin_note ?? "");
  const [status, setStatus] = useState<string | null>(null);
  const inputId = `admin-note-${order.id}`;
  const changed = note.trim() !== (order.admin_note ?? "");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus(null);
    try {
      const updated = await setAdminNote(order.id, note);
      setNote(updated.admin_note ?? "");
      setStatus("Nota guardada.");
      onSaved?.(updated);
    } catch (error) {
      setStatus(formatError(error));
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <label className={styles.label} htmlFor={inputId}>
        Nota del pedido (solo admin)
      </label>
      <div className={styles.row}>
        <input
          id={inputId}
          className={styles.input}
          value={note}
          maxLength={NOTE_MAX_LENGTH}
          onChange={(event) => setNote(event.target.value)}
        />
        <button type="submit" className={styles.saveButton} disabled={!changed}>
          Guardar
        </button>
      </div>
      {status && (
        <p className={styles.status} role="status">
          {status}
        </p>
      )}
    </form>
  );
}
