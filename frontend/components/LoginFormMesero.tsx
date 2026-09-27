"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { login, type ApiError } from "@/lib/api/auth";

const PIN_MAX_LENGTH = 6;
const KEYPAD_DIGITS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"];

export function LoginFormMesero() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function appendDigit(digit: string) {
    setPin((current) => (current.length < PIN_MAX_LENGTH ? current + digit : current));
  }

  function backspace() {
    setPin((current) => current.slice(0, -1));
  }

  function clearPin() {
    setPin("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login("mesero", { username, pin });
      router.push("/mesero");
    } catch (err) {
      setError((err as ApiError).detail ?? "No se pudo iniciar sesión.");
      setPin("");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} aria-label="Ingreso de mesero">
      <label htmlFor="mesero-username">Usuario</label>
      <input
        id="mesero-username"
        name="username"
        value={username}
        onChange={(event) => setUsername(event.target.value)}
        required
      />

      <div role="group" aria-label="PIN">
        <output aria-label="PIN ingresado">{"•".repeat(pin.length)}</output>
        <div>
          {KEYPAD_DIGITS.map((digit) => (
            <button
              key={digit}
              type="button"
              onClick={() => appendDigit(digit)}
              aria-label={`Dígito ${digit}`}
            >
              {digit}
            </button>
          ))}
          <button type="button" onClick={backspace} aria-label="Borrar">
            ⌫
          </button>
          <button type="button" onClick={clearPin} aria-label="Limpiar">
            Limpiar
          </button>
        </div>
      </div>

      <button type="submit" disabled={isSubmitting || pin.length < 4}>
        Ingresar
      </button>

      {error && <p role="alert">{error}</p>}
    </form>
  );
}
