"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { login, type ApiError } from "@/lib/api/auth";

export function LoginFormAdmin() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login("admin", { username, password });
      router.push("/admin");
    } catch (err) {
      setError((err as ApiError).detail ?? "No se pudo iniciar sesión.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} aria-label="Ingreso de administrador">
      <label htmlFor="admin-username">Usuario</label>
      <input
        id="admin-username"
        name="username"
        value={username}
        onChange={(event) => setUsername(event.target.value)}
        required
      />

      <label htmlFor="admin-password">Contraseña</label>
      <input
        id="admin-password"
        name="password"
        type="password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        required
      />

      <button type="submit" disabled={isSubmitting}>
        Ingresar
      </button>

      {error && <p role="alert">{error}</p>}
    </form>
  );
}
