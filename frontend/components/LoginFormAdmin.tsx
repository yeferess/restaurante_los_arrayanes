"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { login, type ApiError } from "@/lib/api/auth";
import styles from "./LoginFormAdmin.module.css";

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
    <form className={styles.form} onSubmit={handleSubmit} aria-label="Ingreso de administrador">
      <div className={styles.field}>
        <label className={styles.label} htmlFor="admin-username">
          Usuario
        </label>
        <input
          id="admin-username"
          className={styles.input}
          name="username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          autoComplete="username"
          required
        />
      </div>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="admin-password">
          Contraseña
        </label>
        <input
          id="admin-password"
          className={styles.input}
          name="password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
          required
        />
      </div>

      <button type="submit" className={styles.submit} disabled={isSubmitting}>
        Ingresar
      </button>

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
