"use client";

import { useEffect, useState, type FormEvent } from "react";
import {
  listMeseros,
  createMesero,
  resetMeseroPin,
  deactivateMesero,
  reactivateMesero,
  unlockMesero,
  type MeseroAccount,
  type ApiErrorBody,
} from "@/lib/api/usuarios";
import styles from "./MeseroManagement.module.css";

function formatError(error: unknown): string {
  const detail = (error as ApiErrorBody)?.detail;
  if (Array.isArray(detail)) return detail.join(" ");
  return detail ?? "Ocurrió un error inesperado.";
}

function MeseroSelect({
  id,
  label,
  meseros,
  value,
  onChange,
}: {
  id: string;
  label: string;
  meseros: MeseroAccount[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className={styles.field}>
      <label className={styles.label} htmlFor={id}>
        {label}
      </label>
      <select
        id={id}
        className={styles.input}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
      >
        <option value="">Selecciona un mesero</option>
        {meseros.map((mesero) => (
          <option key={mesero.id} value={mesero.id}>
            {mesero.username}
            {!mesero.is_active ? " (inactivo)" : ""}
          </option>
        ))}
      </select>
    </div>
  );
}

function CreateMeseroForm({ onCreated }: { onCreated: () => void }) {
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
      onCreated();
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

function ResetPinForm({ meseros }: { meseros: MeseroAccount[] }) {
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
      <MeseroSelect
        id="reset-pin-mesero"
        label="Mesero (restablecer PIN)"
        meseros={meseros}
        value={meseroId}
        onChange={setMeseroId}
      />
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

function DeactivateForm({
  meseros,
  onChanged,
}: {
  meseros: MeseroAccount[];
  onChanged: () => void;
}) {
  const [meseroId, setMeseroId] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      await deactivateMesero(Number(meseroId));
      setMessage("Mesero desactivado.");
      onChanged();
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <form className={styles.card} onSubmit={handleSubmit}>
      <h2 className={styles.cardTitle}>Desactivar mesero</h2>
      <MeseroSelect
        id="deactivate-mesero"
        label="Mesero (desactivar)"
        meseros={meseros}
        value={meseroId}
        onChange={setMeseroId}
      />
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

function ReactivateForm({
  meseros,
  onChanged,
}: {
  meseros: MeseroAccount[];
  onChanged: () => void;
}) {
  const [meseroId, setMeseroId] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      await reactivateMesero(Number(meseroId));
      setMessage("Mesero reactivado.");
      onChanged();
    } catch (error) {
      setMessage(formatError(error));
    }
  }

  return (
    <form className={styles.card} onSubmit={handleSubmit}>
      <h2 className={styles.cardTitle}>Reactivar mesero</h2>
      <MeseroSelect
        id="reactivate-mesero"
        label="Mesero (reactivar)"
        meseros={meseros}
        value={meseroId}
        onChange={setMeseroId}
      />
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

function UnlockForm({ meseros }: { meseros: MeseroAccount[] }) {
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
      <MeseroSelect
        id="unlock-mesero"
        label="Mesero (desbloquear)"
        meseros={meseros}
        value={meseroId}
        onChange={setMeseroId}
      />
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
 * Every action form picks its target mesero from a dropdown (populated
 * from GET /api/usuarios/meseros) instead of asking the admin to type a
 * raw id. */
export function MeseroManagement() {
  const [meseros, setMeseros] = useState<MeseroAccount[]>([]);

  function refresh() {
    return listMeseros().then(setMeseros);
  }

  useEffect(() => {
    refresh();
  }, []);

  return (
    <section>
      <h1 className={styles.heading}>Gestión de meseros</h1>
      <div className={styles.grid}>
        <CreateMeseroForm onCreated={refresh} />
        <ResetPinForm meseros={meseros} />
        <DeactivateForm meseros={meseros} onChanged={refresh} />
        <ReactivateForm meseros={meseros} onChanged={refresh} />
        <UnlockForm meseros={meseros} />
      </div>
    </section>
  );
}
