import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AdminShell } from "./AdminShell";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  usePathname: () => "/admin/mesas",
}));

vi.mock("@/lib/api/auth", () => ({
  logout: vi.fn(),
}));

import { logout } from "@/lib/api/auth";

describe("AdminShell", () => {
  beforeEach(() => {
    pushMock.mockClear();
    vi.mocked(logout).mockReset();
  });

  it("renders every admin section as a link and the page content", () => {
    render(
      <AdminShell>
        <p>contenido del panel</p>
      </AdminShell>
    );
    expect(screen.getByText("contenido del panel")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /mesas/i })).toHaveAttribute(
      "href",
      "/admin/mesas"
    );
    expect(screen.getByRole("link", { name: /categorías/i })).toHaveAttribute(
      "href",
      "/admin/menu/categorias"
    );
    expect(screen.getByRole("link", { name: /productos/i })).toHaveAttribute(
      "href",
      "/admin/menu/productos"
    );
    expect(screen.getByRole("link", { name: /^cuentas$/i })).toHaveAttribute(
      "href",
      "/admin/menu/cuentas"
    );
    expect(screen.getByRole("link", { name: /^admins$/i })).toHaveAttribute(
      "href",
      "/admin/usuarios/admins"
    );
    expect(screen.getByRole("link", { name: /meseros/i })).toHaveAttribute(
      "href",
      "/admin/usuarios/meseros"
    );
    expect(screen.getByRole("link", { name: /nuevo pedido/i })).toHaveAttribute(
      "href",
      "/admin/pedidos/nuevo"
    );
    expect(screen.getByRole("link", { name: /entrantes/i })).toHaveAttribute(
      "href",
      "/admin/pedidos"
    );
    expect(screen.getByRole("link", { name: /cobrados/i })).toHaveAttribute(
      "href",
      "/admin/pedidos/cobrados"
    );
    expect(screen.getByRole("link", { name: /estadísticas/i })).toHaveAttribute(
      "href",
      "/admin/estadisticas"
    );
  });

  it("marks the current section as active", () => {
    render(
      <AdminShell>
        <p>contenido</p>
      </AdminShell>
    );
    expect(screen.getByRole("link", { name: /mesas/i })).toHaveAttribute(
      "aria-current",
      "page"
    );
  });

  it("logs out and redirects to the admin login on 'Cerrar sesión'", async () => {
    vi.mocked(logout).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(
      <AdminShell>
        <p>contenido</p>
      </AdminShell>
    );

    await user.click(screen.getByRole("button", { name: /cerrar sesión/i }));

    await waitFor(() => {
      expect(logout).toHaveBeenCalled();
      expect(pushMock).toHaveBeenCalledWith("/admin/login");
    });
  });
});
