import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { apiFetch, requestJson, type ApiErrorBody } from "./client";

describe("lib/api/client (shared fetch + CSRF helper)", () => {
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

  it("apiFetch prefixes the backend URL and includes credentials", async () => {
    mockOk({ ok: true });
    await apiFetch("/api/menu");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/menu"),
      expect.objectContaining({ credentials: "include" })
    );
  });

  it("apiFetch attaches X-CSRFToken from the csrftoken cookie on POST", async () => {
    document.cookie = "csrftoken=abc123";
    mockOk({ ok: true });
    await apiFetch("/api/menu/categorias", { method: "POST", body: "{}" });
    expect(global.fetch).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        headers: expect.objectContaining({ "X-CSRFToken": "abc123" }),
      })
    );
  });

  it("apiFetch never attaches X-CSRFToken on GET", async () => {
    document.cookie = "csrftoken=abc123";
    mockOk({ ok: true });
    await apiFetch("/api/menu");
    const [, init] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect((init?.headers as Record<string, string>)["X-CSRFToken"]).toBeUndefined();
  });

  it("apiFetch omits X-CSRFToken on POST when there is no csrftoken cookie", async () => {
    mockOk({ ok: true });
    await apiFetch("/api/menu/categorias", { method: "POST", body: "{}" });
    const [, init] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect((init?.headers as Record<string, string>)["X-CSRFToken"]).toBeUndefined();
  });

  it("requestJson returns the parsed body on success", async () => {
    mockOk({ id: 1, name: "Bebidas" }, 201);
    const result = await requestJson<{ id: number; name: string }>(
      "/api/menu/categorias",
      { method: "POST", body: JSON.stringify({ name: "Bebidas" }) }
    );
    expect(result).toEqual({ id: 1, name: "Bebidas" });
  });

  it("requestJson throws the parsed error body on failure", async () => {
    mockOk({ detail: "Ya existe una categoría con ese nombre." }, 409);
    await expect(
      requestJson<unknown>("/api/menu/categorias", { method: "POST" })
    ).rejects.toEqual({ detail: "Ya existe una categoría con ese nombre." } as ApiErrorBody);
  });

  it("requestJson tolerates an empty (204) body", async () => {
    mockOk(undefined, 204);
    await expect(
      requestJson<void>("/api/menu/productos/1", { method: "DELETE" })
    ).resolves.toBeUndefined();
  });
});
