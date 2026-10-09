"use client";

import { useState, type FormEvent } from "react";
import { createAdmin, changeOwnPassword, type ApiErrorBody } from "@/lib/api/usuarios";
import styles from "./AdminManagement.module.css";

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

function CreateAdminForm() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      const admin = await createAdmin(username, password);
      setMessage(`Admin "${admin.username}" creado (id ${admin.id}).`);
      setUsername("");
      setPassword("");
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <form className={styles.card} onSubmit={handleSubmit}>
      <h2 className={styles.cardTitle}>Crear admin adicional</h2>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="create-admin-username">
          Nuevo usuario admin
        </label>
        <input
          id="create-admin-username"
          className={styles.input}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
      </div>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="create-admin-password">
          Nueva contraseña admin
        </label>
        <input
          id="create-admin-password"
          className={styles.input}
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </div>
      <button type="submit" className={styles.submitButton}>
        Crear admin
      </button>
      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}
    </form>
  );
}

function ChangeOwnPasswordForm() {
  const [current, setCurrent] = useState("");
  const [nueva, setNueva] = useState("");
  const [confirmacion, setConfirmacion] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      await changeOwnPassword(current, nueva, confirmacion);
      setMessage("Contraseña actualizada correctamente.");
      setCurrent("");
      setNueva("");
      setConfirmacion("");
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <form className={styles.card} onSubmit={handleSubmit}>
      <h2 className={styles.cardTitle}>Cambiar mi contraseña</h2>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="current-password">
          Contraseña actual
        </label>
        <input
          id="current-password"
          className={styles.input}
          type="password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          required
        />
      </div>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="new-password">
          Contraseña nueva
        </label>
        <input
          id="new-password"
          className={styles.input}
          type="password"
          value={nueva}
          onChange={(e) => setNueva(e.target.value)}
          required
        />
      </div>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="confirm-new-password">
          Confirmar contraseña nueva
        </label>
        <input
          id="confirm-new-password"
          className={styles.input}
          type="password"
          value={confirmacion}
          onChange={(e) => setConfirmacion(e.target.value)}
          required
        />
      </div>
      <button type="submit" className={styles.submitButton}>
        Cambiar contraseña
      </button>
      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}
    </form>
  );
}

/** Admin management screen (T54 — RF-6, RF-10).
 *
 * Only two actions exist on purpose: creating an additional admin, and
 * changing one's own password. There is deliberately no button to edit,
 * rename, deactivate or otherwise touch another admin's account — RF-6/
 * RF-10 keep that exclusively on the server CLI. */
export function AdminManagement() {
  return (
    <section>
      <h1 className={styles.heading}>Gestión de administradores</h1>
      <div className={styles.grid}>
        <CreateAdminForm />
        <ChangeOwnPasswordForm />
      </div>
    </section>
  );
}
