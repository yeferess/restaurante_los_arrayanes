"use client";

import { useState, type FormEvent } from "react";
import {
  createMesero,
  resetMeseroPin,
  deactivateMesero,
  reactivateMesero,
  unlockMesero,
  type ApiErrorBody,
} from "@/lib/api/usuarios";

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

function CreateMeseroForm() {
  const [username, setUsername] = useState("");
  const [pin, setPin] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      const mesero = await createMesero(username, pin);
      setMessage(`Mesero "${mesero.username}" creado (id ${mesero.id}).`);
      setUsername("");
      setPin("");
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2>Crear mesero</h2>
      <label htmlFor="create-mesero-username">Nuevo usuario</label>
      <input
        id="create-mesero-username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        required
      />
      <label htmlFor="create-mesero-pin">Nuevo PIN (crear)</label>
      <input
        id="create-mesero-pin"
        value={pin}
        onChange={(e) => setPin(e.target.value)}
        required
      />
      <button type="submit">Crear mesero</button>
      {message && <p role="status">{message}</p>}
    </form>
  );
}

function ResetPinForm() {
  const [meseroId, setMeseroId] = useState("");
  const [nuevoPin, setNuevoPin] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      await resetMeseroPin(Number(meseroId), nuevoPin);
      setMessage("PIN restablecido correctamente.");
      setNuevoPin("");
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2>Restablecer PIN</h2>
      <label htmlFor="reset-pin-id">Id del mesero (PIN)</label>
      <input
        id="reset-pin-id"
        value={meseroId}
        onChange={(e) => setMeseroId(e.target.value)}
        required
      />
      <label htmlFor="reset-pin-value">Nuevo PIN (restablecer)</label>
      <input
        id="reset-pin-value"
        value={nuevoPin}
        onChange={(e) => setNuevoPin(e.target.value)}
        required
      />
      <button type="submit">Restablecer PIN</button>
      {message && <p role="status">{message}</p>}
    </form>
  );
}

function DeactivateForm() {
  const [meseroId, setMeseroId] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      await deactivateMesero(Number(meseroId));
      setMessage("Mesero desactivado.");
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2>Desactivar mesero</h2>
      <label htmlFor="deactivate-id">Id del mesero (desactivar)</label>
      <input
        id="deactivate-id"
        value={meseroId}
        onChange={(e) => setMeseroId(e.target.value)}
        required
      />
      <button type="submit">Desactivar</button>
      {message && <p role="status">{message}</p>}
    </form>
  );
}

function ReactivateForm() {
  const [meseroId, setMeseroId] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      await reactivateMesero(Number(meseroId));
      setMessage("Mesero reactivado.");
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2>Reactivar mesero</h2>
      <label htmlFor="reactivate-id">Id del mesero (reactivar)</label>
      <input
        id="reactivate-id"
        value={meseroId}
        onChange={(e) => setMeseroId(e.target.value)}
        required
      />
      <button type="submit">Reactivar</button>
      {message && <p role="status">{message}</p>}
    </form>
  );
}

function UnlockForm() {
  const [meseroId, setMeseroId] = useState("");
  const [nuevoPin, setNuevoPin] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      await unlockMesero(Number(meseroId), nuevoPin);
      setMessage("Mesero desbloqueado.");
      setNuevoPin("");
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2>Desbloquear mesero</h2>
      <label htmlFor="unlock-id">Id del mesero (desbloquear)</label>
      <input
        id="unlock-id"
        value={meseroId}
        onChange={(e) => setMeseroId(e.target.value)}
        required
      />
      <label htmlFor="unlock-pin">PIN de desbloqueo</label>
      <input
        id="unlock-pin"
        value={nuevoPin}
        onChange={(e) => setNuevoPin(e.target.value)}
        required
      />
      <button type="submit">Desbloquear</button>
      {message && <p role="status">{message}</p>}
    </form>
  );
}

/** Mesero management screen (T53 — RF-2, RF-3, RF-4, RF-5, RF-7).
 *
 * No listing endpoint exists in the API (spec's Fase 3 only defines
 * per-action POSTs by id), so this is a set of independent action forms
 * operating on a mesero id, not a live table. */
export function MeseroManagement() {
  return (
    <section>
      <h1>Gestión de meseros</h1>
      <CreateMeseroForm />
      <ResetPinForm />
      <DeactivateForm />
      <ReactivateForm />
      <UnlockForm />
    </section>
  );
}
