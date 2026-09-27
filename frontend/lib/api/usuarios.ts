// Users management API client (T55 — RF-2, RF-4, RF-5, RF-6, RF-7, RF-10).
// Mesero functions created early as a prerequisite for T53; admin
// functions (createAdmin, changeOwnPassword) and the dedicated test suite
// for this whole module are completed when T55 is formally implemented.

const BACKEND_API_URL =
  process.env.NEXT_PUBLIC_BACKEND_API_URL ?? "http://127.0.0.1:8000";

export type MeseroAccount = {
  id: number;
  username: string;
  role: "MESERO";
  is_active: boolean;
  created_by: number | null;
  created_at: string;
};

export type ApiErrorBody = { detail?: string | string[] };

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BACKEND_API_URL}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : undefined;

  if (!response.ok) {
    throw (data ?? { detail: "Error inesperado." }) as ApiErrorBody;
  }
  return data as T;
}

export function createMesero(username: string, pin: string): Promise<MeseroAccount> {
  return requestJson<MeseroAccount>("/api/usuarios/meseros", {
    method: "POST",
    body: JSON.stringify({ username, pin }),
  });
}

export function resetMeseroPin(meseroId: number, nuevoPin: string): Promise<void> {
  return requestJson<void>(`/api/usuarios/meseros/${meseroId}/reset-pin`, {
    method: "POST",
    body: JSON.stringify({ nuevo_pin: nuevoPin }),
  });
}

export function deactivateMesero(meseroId: number): Promise<void> {
  return requestJson<void>(`/api/usuarios/meseros/${meseroId}/desactivar`, {
    method: "POST",
  });
}

export function reactivateMesero(meseroId: number): Promise<void> {
  return requestJson<void>(`/api/usuarios/meseros/${meseroId}/reactivar`, {
    method: "POST",
  });
}

export function unlockMesero(meseroId: number, nuevoPin: string): Promise<void> {
  return requestJson<void>(`/api/usuarios/meseros/${meseroId}/desbloquear`, {
    method: "POST",
    body: JSON.stringify({ nuevo_pin: nuevoPin }),
  });
}

export type AdminAccount = {
  id: number;
  username: string;
  role: "ADMIN";
  is_active: boolean;
  created_by: number | null;
  created_at: string;
};

export function createAdmin(username: string, password: string): Promise<AdminAccount> {
  return requestJson<AdminAccount>("/api/usuarios/admins", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function changeOwnPassword(
  passwordActual: string,
  passwordNueva: string,
  passwordNuevaConfirmacion: string
): Promise<void> {
  return requestJson<void>("/api/usuarios/admins/me/password", {
    method: "POST",
    body: JSON.stringify({
      password_actual: passwordActual,
      password_nueva: passwordNueva,
      password_nueva_confirmacion: passwordNuevaConfirmacion,
    }),
  });
}
