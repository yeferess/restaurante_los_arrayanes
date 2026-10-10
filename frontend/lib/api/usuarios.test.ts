import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  createMesero,
  listMeseros,
  resetMeseroPin,
  deactivateMesero,
  reactivateMesero,
  unlockMesero,
  createAdmin,
  changeOwnPassword,
} from "./usuarios";

describe("lib/api/usuarios (T55, RF-2/4/5/6/7/10)", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    vi.restoreAllMocks();
  });

  function mockOk(body: unknown, status = 200) {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(body === undefined ? null : JSON.stringify(body), { status })
    );
  }

  function mockError(body: unknown, status: number) {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(JSON.stringify(body), { status })
    );
  }

  it("createMesero posts to /api/usuarios/meseros with credentials included", async () => {
    mockOk(
      {
        id: 7,
        username: "carlos",
        role: "MESERO",
        is_active: true,
        created_by: 1,
        created_at: "2026-01-01T00:00:00Z",
      },
      201
    );
    const result = await createMesero("carlos", "1234");

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/usuarios/meseros"),
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        body: JSON.stringify({ username: "carlos", pin: "1234" }),
      })
    );
    expect(result.id).toBe(7);
  });

  it("createMesero propagates the exact API error on a 409", async () => {
    mockError({ detail: "Ese nombre de usuario ya existe." }, 409);
    await expect(createMesero("carlos", "1234")).rejects.toEqual({
      detail: "Ese nombre de usuario ya existe.",
    });
  });

  it("listMeseros gets /api/usuarios/meseros", async () => {
    mockOk([
      {
        id: 7,
        username: "juan",
        role: "MESERO",
        is_active: true,
        created_by: 1,
        created_at: "2026-01-01T00:00:00Z",
      },
    ]);
    const result = await listMeseros();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/usuarios/meseros"),
      expect.objectContaining({ credentials: "include" })
    );
    expect(result[0].username).toBe("juan");
  });

  it("resetMeseroPin posts nuevo_pin to the reset-pin endpoint", async () => {
    mockOk(undefined);
    await resetMeseroPin(7, "9999");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/usuarios/meseros/7/reset-pin"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ nuevo_pin: "9999" }),
      })
    );
  });

  it("deactivateMesero posts to the desactivar endpoint and propagates a 409 detail", async () => {
    mockError({ detail: "El mesero tiene mesas o pedidos abiertos." }, 409);
    await expect(deactivateMesero(7)).rejects.toEqual({
      detail: "El mesero tiene mesas o pedidos abiertos.",
    });
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/usuarios/meseros/7/desactivar"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("reactivateMesero posts to the reactivar endpoint", async () => {
    mockOk(undefined);
    await reactivateMesero(7);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/usuarios/meseros/7/reactivar"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("unlockMesero posts nuevo_pin to the desbloquear endpoint", async () => {
    mockOk(undefined);
    await unlockMesero(7, "5555");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/usuarios/meseros/7/desbloquear"),
      expect.objectContaining({ body: JSON.stringify({ nuevo_pin: "5555" }) })
    );
  });

  it("createMesero sends the csrftoken cookie as an X-CSRFToken header", async () => {
    document.cookie = "csrftoken=abc123";
    mockOk(
      {
        id: 7,
        username: "carlos",
        role: "MESERO",
        is_active: true,
        created_by: 1,
        created_at: "2026-01-01T00:00:00Z",
      },
      201
    );
    await createMesero("carlos", "1234");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/usuarios/meseros"),
      expect.objectContaining({
        headers: expect.objectContaining({ "X-CSRFToken": "abc123" }),
      })
    );
  });

  it("createAdmin posts to /api/usuarios/admins", async () => {
    mockOk(
      {
        id: 3,
        username: "nuevo_admin",
        role: "ADMIN",
        is_active: true,
        created_by: 1,
        created_at: "2026-01-01T00:00:00Z",
      },
      201
    );
    const result = await createAdmin("nuevo_admin", "OtraSegura9");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/usuarios/admins"),
      expect.objectContaining({
        body: JSON.stringify({ username: "nuevo_admin", password: "OtraSegura9" }),
      })
    );
    expect(result.role).toBe("ADMIN");
  });

  it("createAdmin propagates a weak-password 400 error", async () => {
    mockError({ detail: ["Password must be at least 8 characters long."] }, 400);
    await expect(createAdmin("nuevo_admin", "weak")).rejects.toEqual({
      detail: ["Password must be at least 8 characters long."],
    });
  });

  it("changeOwnPassword posts the three password fields to admins/me/password", async () => {
    mockOk(undefined);
    await changeOwnPassword("Sup3rSecreta", "NuevaClave9", "NuevaClave9");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/usuarios/admins/me/password"),
      expect.objectContaining({
        body: JSON.stringify({
          password_actual: "Sup3rSecreta",
          password_nueva: "NuevaClave9",
          password_nueva_confirmacion: "NuevaClave9",
        }),
      })
    );
  });

  it("changeOwnPassword propagates the wrong-current-password error", async () => {
    mockError({ detail: "La contraseña actual es incorrecta." }, 400);
    await expect(
      changeOwnPassword("wrong", "NuevaClave9", "NuevaClave9")
    ).rejects.toEqual({ detail: "La contraseña actual es incorrecta." });
  });
});
