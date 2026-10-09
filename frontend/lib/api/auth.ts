// Auth API client (T51 — RF-1, RF-8, RF-9). Created early as a
// prerequisite for T49/T50 (login pages); completed with logout/session/
// heartbeat and its own dedicated tests when T51 is formally implemented.

import { apiFetch } from "./client";

export type Role = "ADMIN" | "MESERO";

export type UserSession = {
  id: number;
  username: string;
  role: Role;
};

export type ApiError = {
  detail: string;
  intentos_restantes?: number;
};

async function parseJsonOrThrow<T>(response: Response): Promise<T> {
  const data = await response.json();
  if (!response.ok) {
    throw data as ApiError;
  }
  return data as T;
}

export async function login(
  role: "admin" | "mesero",
  credentials: { username: string; password: string } | { username: string; pin: string }
): Promise<UserSession> {
  const response = await apiFetch(`/api/auth/${role}/login`, {
    method: "POST",
    body: JSON.stringify(credentials),
  });
  return parseJsonOrThrow<UserSession>(response);
}

export async function logout(): Promise<void> {
  const response = await apiFetch("/api/auth/logout", { method: "POST" });
  if (!response.ok) {
    const data = await response.json().catch(() => ({ detail: "No se pudo cerrar sesión." }));
    throw data as ApiError;
  }
}

export async function session(): Promise<UserSession> {
  const response = await apiFetch("/api/auth/session");
  return parseJsonOrThrow<UserSession>(response);
}

export async function heartbeat(): Promise<{ expira_en_seg: number }> {
  const response = await apiFetch("/api/auth/heartbeat", { method: "POST" });
  return parseJsonOrThrow<{ expira_en_seg: number }>(response);
}
