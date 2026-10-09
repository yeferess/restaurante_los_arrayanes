import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MeseroShell } from "./MeseroShell";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  usePathname: () => "/mesero/mesas",
}));

vi.mock("@/lib/api/auth", () => ({
  logout: vi.fn(),
}));

import { logout } from "@/lib/api/auth";

describe("MeseroShell", () => {
  beforeEach(() => {
    pushMock.mockClear();
    vi.mocked(logout).mockReset();
  });

  it("renders the three tabs as links and the page content", () => {
    render(
      <MeseroShell>
        <p>contenido del turno</p>
      </MeseroShell>
    );
    expect(screen.getByText("contenido del turno")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /mesas/i })).toHaveAttribute(
      "href",
      "/mesero/mesas"
    );
    expect(screen.getByRole("link", { name: /pedidos/i })).toHaveAttribute(
      "href",
      "/mesero/pedidos"
    );
    expect(screen.getByRole("link", { name: /menú/i })).toHaveAttribute(
      "href",
      "/mesero/menu"
    );
  });

  it("marks the current tab as active", () => {
    render(
      <MeseroShell>
        <p>contenido</p>
      </MeseroShell>
    );
    expect(screen.getByRole("link", { name: /mesas/i })).toHaveAttribute(
      "aria-current",
      "page"
    );
  });

  it("logs out and redirects to the mesero login", async () => {
    vi.mocked(logout).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(
      <MeseroShell>
        <p>contenido</p>
      </MeseroShell>
    );

    await user.click(screen.getByRole("button", { name: /cerrar sesión/i }));

    await waitFor(() => {
      expect(logout).toHaveBeenCalled();
      expect(pushMock).toHaveBeenCalledWith("/mesero/login");
    });
  });
});
