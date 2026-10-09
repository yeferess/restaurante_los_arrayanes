"use client";

import { useEffect, useState, type FormEvent } from "react";
import {
  listAccounts,
  createAccount,
  deleteAccount,
  type PaymentAccount,
  type ApiErrorBody,
} from "@/lib/api/payments";
import styles from "./PaymentAccountsManagement.module.css";

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

/** Payment accounts catalog management (005-cobro — RF-2): create
 * accounts and delete the ones that were never used. "Efectivo" is
 * fixed — never offered for deletion here. */
export function PaymentAccountsManagement() {
  const [accounts, setAccounts] = useState<PaymentAccount[]>([]);
  const [newName, setNewName] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  async function refresh() {
    const data = await listAccounts();
    setAccounts(data);
  }

  useEffect(() => {
    refresh().catch((error) => setMessage(formatError(error)));
  }, []);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      await createAccount(newName);
      setNewName("");
      await refresh();
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  async function handleDelete(accountId: number) {
    setMessage(null);
    try {
      await deleteAccount(accountId);
      await refresh();
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <section>
      <h1 className={styles.heading}>Opciones de pago</h1>
      <form className={styles.createForm} onSubmit={handleCreate}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="new-account-name">
            Nueva cuenta
          </label>
          <input
            id="new-account-name"
            className={styles.input}
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            required
          />
        </div>
        <button type="submit" className={styles.primaryButton}>
          Crear cuenta
        </button>
      </form>
      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}
      <ul className={styles.list}>
        {accounts.map((account) => (
          <li key={account.id} className={styles.row}>
            <span className={styles.rowName}>{account.name}</span>
            {account.is_fixed ? (
              <span className={styles.fixedTag}>fija</span>
            ) : (
              <button
                type="button"
                className={styles.dangerButton}
                onClick={() => handleDelete(account.id)}
              >
                Eliminar
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
