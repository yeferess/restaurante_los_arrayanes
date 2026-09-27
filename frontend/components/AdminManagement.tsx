"use client";

import { useState, type FormEvent } from "react";
import { createAdmin, changeOwnPassword, type ApiErrorBody } from "@/lib/api/usuarios";

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
    <form onSubmit={handleSubmit}>
      <h2>Crear admin adicional</h2>
      <label htmlFor="create-admin-username">Nuevo usuario admin</label>
      <input
        id="create-admin-username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        required
      />
      <label htmlFor="create-admin-password">Nueva contraseña admin</label>
      <input
        id="create-admin-password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <button type="submit">Crear admin</button>
      {message && <p role="status">{message}</p>}
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
    <form onSubmit={handleSubmit}>
      <h2>Cambiar mi contraseña</h2>
      <label htmlFor="current-password">Contraseña actual</label>
      <input
        id="current-password"
        type="password"
        value={current}
        onChange={(e) => setCurrent(e.target.value)}
        required
      />
      <label htmlFor="new-password">Contraseña nueva</label>
      <input
        id="new-password"
        type="password"
        value={nueva}
        onChange={(e) => setNueva(e.target.value)}
        required
      />
      <label htmlFor="confirm-new-password">Confirmar contraseña nueva</label>
      <input
        id="confirm-new-password"
        type="password"
        value={confirmacion}
        onChange={(e) => setConfirmacion(e.target.value)}
        required
      />
      <button type="submit">Cambiar contraseña</button>
      {message && <p role="status">{message}</p>}
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
      <h1>Gestión de administradores</h1>
      <CreateAdminForm />
      <ChangeOwnPasswordForm />
    </section>
  );
}
