// Auth API client (T51 — RF-1, RF-8, RF-9). Created early as a
// prerequisite for T49/T50 (login pages); completed with logout/session/
// heartbeat and its own dedicated tests when T51 is formally implemented.

const BACKEND_API_URL =
  process.env.NEXT_PUBLIC_BACKEND_API_URL ?? "http://127.0.0.1:8000";

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
  const response = await fetch(`${BACKEND_API_URL}/api/auth/${role}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(credentials),
  });
  return parseJsonOrThrow<UserSession>(response);
}

export async function logout(): Promise<void> {
  const response = await fetch(`${BACKEND_API_URL}/api/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({ detail: "No se pudo cerrar sesión." }));
    throw data as ApiError;
  }
}

export async function session(): Promise<UserSession> {
  const response = await fetch(`${BACKEND_API_URL}/api/auth/session`, {
    credentials: "include",
  });
  return parseJsonOrThrow<UserSession>(response);
}

export async function heartbeat(): Promise<{ expira_en_seg: number }> {
  const response = await fetch(`${BACKEND_API_URL}/api/auth/heartbeat`, {
    method: "POST",
    credentials: "include",
  });
  return parseJsonOrThrow<{ expira_en_seg: number }>(response);
}
