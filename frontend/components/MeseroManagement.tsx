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
import styles from "./MeseroManagement.module.css";

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
    <form className={styles.card} onSubmit={handleSubmit}>
      <h2 className={styles.cardTitle}>Crear mesero</h2>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="create-mesero-username">
          Nuevo usuario
        </label>
        <input
          id="create-mesero-username"
          className={styles.input}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
      </div>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="create-mesero-pin">
          Nuevo PIN (crear)
        </label>
        <input
          id="create-mesero-pin"
          className={styles.input}
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          required
        />
      </div>
      <button type="submit" className={styles.submitButton}>
        Crear mesero
      </button>
      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}
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
    <form className={styles.card} onSubmit={handleSubmit}>
      <h2 className={styles.cardTitle}>Restablecer PIN</h2>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="reset-pin-id">
          Id del mesero (PIN)
        </label>
        <input
          id="reset-pin-id"
          className={styles.input}
          value={meseroId}
          onChange={(e) => setMeseroId(e.target.value)}
          required
        />
      </div>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="reset-pin-value">
          Nuevo PIN (restablecer)
        </label>
        <input
          id="reset-pin-value"
          className={styles.input}
          value={nuevoPin}
          onChange={(e) => setNuevoPin(e.target.value)}
          required
        />
      </div>
      <button type="submit" className={styles.submitButton}>
        Restablecer PIN
      </button>
      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}
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
    <form className={styles.card} onSubmit={handleSubmit}>
      <h2 className={styles.cardTitle}>Desactivar mesero</h2>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="deactivate-id">
          Id del mesero (desactivar)
        </label>
        <input
          id="deactivate-id"
          className={styles.input}
          value={meseroId}
          onChange={(e) => setMeseroId(e.target.value)}
          required
        />
      </div>
      <button type="submit" className={styles.submitButton}>
        Desactivar
      </button>
      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}
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
    <form className={styles.card} onSubmit={handleSubmit}>
      <h2 className={styles.cardTitle}>Reactivar mesero</h2>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="reactivate-id">
          Id del mesero (reactivar)
        </label>
        <input
          id="reactivate-id"
          className={styles.input}
          value={meseroId}
          onChange={(e) => setMeseroId(e.target.value)}
          required
        />
      </div>
      <button type="submit" className={styles.submitButton}>
        Reactivar
      </button>
      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}
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
    <form className={styles.card} onSubmit={handleSubmit}>
      <h2 className={styles.cardTitle}>Desbloquear mesero</h2>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="unlock-id">
          Id del mesero (desbloquear)
        </label>
        <input
          id="unlock-id"
          className={styles.input}
          value={meseroId}
          onChange={(e) => setMeseroId(e.target.value)}
          required
        />
      </div>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="unlock-pin">
          PIN de desbloqueo
        </label>
        <input
          id="unlock-pin"
          className={styles.input}
          value={nuevoPin}
          onChange={(e) => setNuevoPin(e.target.value)}
          required
        />
      </div>
      <button type="submit" className={styles.submitButton}>
        Desbloquear
      </button>
      {message && (
        <p className={styles.message} role="status">
          {message}
        </p>
      )}
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
      <h1 className={styles.heading}>Gestión de meseros</h1>
      <div className={styles.grid}>
        <CreateMeseroForm />
        <ResetPinForm />
        <DeactivateForm />
        <ReactivateForm />
        <UnlockForm />
      </div>
    </section>
  );
}
