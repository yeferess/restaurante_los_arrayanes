import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { login, logout, session, heartbeat } from "./auth";

describe("lib/api/auth (T51, RF-1, RF-8, RF-9)", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  function mockFetchOnce(body: unknown, status = 200) {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(JSON.stringify(body), { status })
    );
  }

  it("login('admin', ...) posts to /api/auth/admin/login with credentials included", async () => {
    mockFetchOnce({ id: 1, username: "ana", role: "ADMIN" });
    const result = await login("admin", { username: "ana", password: "Sup3rSecreta" });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/auth/admin/login"),
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        body: JSON.stringify({ username: "ana", password: "Sup3rSecreta" }),
      })
    );
    expect(result).toEqual({ id: 1, username: "ana", role: "ADMIN" });
  });

  it("login('mesero', ...) posts to /api/auth/mesero/login", async () => {
    mockFetchOnce({ id: 2, username: "carlos", role: "MESERO" });
    await login("mesero", { username: "carlos", pin: "1234" });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/auth/mesero/login"),
      expect.objectContaining({
        body: JSON.stringify({ username: "carlos", pin: "1234" }),
      })
    );
  });

  it("login propagates the exact API error body on failure", async () => {
    mockFetchOnce(
      { detail: "Usuario o contraseña incorrectos. Te quedan 4 intentos antes del bloqueo.", intentos_restantes: 4 },
      401
    );
    await expect(login("admin", { username: "ana", password: "wrong" })).rejects.toEqual({
      detail: "Usuario o contraseña incorrectos. Te quedan 4 intentos antes del bloqueo.",
      intentos_restantes: 4,
    });
  });

  it("logout() posts to /api/auth/logout", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(null, { status: 204 })
    );
    await expect(logout()).resolves.toBeUndefined();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/auth/logout"),
      expect.objectContaining({ method: "POST", credentials: "include" })
    );
  });

  it("logout() propagates the API error on failure", async () => {
    mockFetchOnce({ detail: "Sesión expirada por inactividad." }, 401);
    await expect(logout()).rejects.toEqual({ detail: "Sesión expirada por inactividad." });
  });

  it("session() gets /api/auth/session and returns the user info", async () => {
    mockFetchOnce({ id: 1, username: "ana", role: "ADMIN" });
    const result = await session();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/auth/session"),
      expect.objectContaining({ credentials: "include" })
    );
    expect(result).toEqual({ id: 1, username: "ana", role: "ADMIN" });
  });

  it("session() propagates the API error when there is no session", async () => {
    mockFetchOnce({ detail: "not authenticated" }, 401);
    await expect(session()).rejects.toEqual({ detail: "not authenticated" });
  });

  it("heartbeat() posts to /api/auth/heartbeat and returns the expiry", async () => {
    mockFetchOnce({ expira_en_seg: 1800 });
    const result = await heartbeat();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/auth/heartbeat"),
      expect.objectContaining({ method: "POST", credentials: "include" })
    );
    expect(result).toEqual({ expira_en_seg: 1800 });
  });

  it("heartbeat() propagates the API error on failure", async () => {
    mockFetchOnce({ detail: "Sesión expirada por inactividad." }, 401);
    await expect(heartbeat()).rejects.toEqual({ detail: "Sesión expirada por inactividad." });
  });
});
