import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { NextRequest } from "next/server";
import { proxy } from "./proxy";

function requestFor(path: string, cookie?: string) {
  return new NextRequest(new URL(`http://localhost${path}`), {
    headers: cookie ? { cookie } : {},
  });
}

describe("proxy (T48 — route protection, RF-1)", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("redirects to /admin/login when there is no session cookie", async () => {
    const response = await proxy(requestFor("/admin/panel"));
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("http://localhost/admin/login");
  });

  it("redirects to /mesero/login when there is no session cookie", async () => {
    const response = await proxy(requestFor("/mesero/turno"));
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("http://localhost/mesero/login");
  });

  it("lets an admin session through to an admin route", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      new Response(JSON.stringify({ id: 1, username: "ana", role: "ADMIN" }), {
        status: 200,
      })
    );
    const response = await proxy(requestFor("/admin/panel", "sessionid=abc123"));
    expect(response.status).toBe(200);
    expect(response.headers.get("location")).toBeNull();
  });

  it("lets a mesero session through to a mesero route", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      new Response(JSON.stringify({ id: 2, username: "carlos", role: "MESERO" }), {
        status: 200,
      })
    );
    const response = await proxy(requestFor("/mesero/turno", "sessionid=abc123"));
    expect(response.status).toBe(200);
    expect(response.headers.get("location")).toBeNull();
  });

  it("redirects to /admin/login when the session belongs to a mesero", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      new Response(JSON.stringify({ id: 2, username: "carlos", role: "MESERO" }), {
        status: 200,
      })
    );
    const response = await proxy(requestFor("/admin/panel", "sessionid=abc123"));
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("http://localhost/admin/login");
  });

  it("redirects to /mesero/login when the session belongs to an admin", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      new Response(JSON.stringify({ id: 1, username: "ana", role: "ADMIN" }), {
        status: 200,
      })
    );
    const response = await proxy(requestFor("/mesero/turno", "sessionid=abc123"));
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("http://localhost/mesero/login");
  });

  it("redirects when the backend reports the session as invalid/expired", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      new Response(JSON.stringify({ detail: "not authenticated" }), { status: 401 })
    );
    const response = await proxy(requestFor("/admin/panel", "sessionid=stale"));
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("http://localhost/admin/login");
  });

  it("never checks the session for the login pages themselves", async () => {
    const adminLogin = await proxy(requestFor("/admin/login"));
    const meseroLogin = await proxy(requestFor("/mesero/login"));
    expect(adminLogin.status).toBe(200);
    expect(meseroLogin.status).toBe(200);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("does not touch unrelated routes", async () => {
    const response = await proxy(requestFor("/"));
    expect(response.status).toBe(200);
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
