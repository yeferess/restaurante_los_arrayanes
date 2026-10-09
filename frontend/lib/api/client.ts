// Shared fetch client for lib/api/*.ts. Centralizes the backend base URL
// and CSRF token attachment (Django's session-cookie auth requires the
// `csrftoken` cookie echoed back as an X-CSRFToken header on any
// non-safe method) so this logic exists in exactly one place.

export const BACKEND_API_URL =
  process.env.NEXT_PUBLIC_BACKEND_API_URL ?? "http://127.0.0.1:8000";

export type ApiErrorBody = { detail?: string | string[] };

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

export function getCsrfToken(): string | undefined {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : undefined;
}

export function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const method = (init?.method ?? "GET").toUpperCase();
  const csrfToken = SAFE_METHODS.has(method) ? undefined : getCsrfToken();
  return fetch(`${BACKEND_API_URL}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
    },
    ...init,
  });
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(path, init);
  const text = await response.text();
  const data = text ? JSON.parse(text) : undefined;

  if (!response.ok) {
    throw (data ?? { detail: "Error inesperado." }) as ApiErrorBody;
  }
  return data as T;
}
