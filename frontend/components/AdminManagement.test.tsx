import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AdminManagement } from "./AdminManagement";

vi.mock("@/lib/api/usuarios", () => ({
  createAdmin: vi.fn(),
  changeOwnPassword: vi.fn(),
}));

import { createAdmin, changeOwnPassword } from "@/lib/api/usuarios";

describe("AdminManagement (T54, RF-6, RF-10)", () => {
  beforeEach(() => {
    vi.mocked(createAdmin).mockReset();
    vi.mocked(changeOwnPassword).mockReset();
  });

  it("creates an additional admin and shows the confirmation", async () => {
    vi.mocked(createAdmin).mockResolvedValue({
      id: 3,
      username: "nuevo_admin",
      role: "ADMIN",
      is_active: true,
      created_by: 1,
      created_at: "2026-01-01T00:00:00Z",
    });
    const user = userEvent.setup();
    render(<AdminManagement />);

    await user.type(screen.getByLabelText(/nuevo usuario admin/i), "nuevo_admin");
    await user.type(screen.getByLabelText(/nueva contraseña admin/i), "OtraSegura9");
    await user.click(screen.getByRole("button", { name: /crear admin/i }));

    await waitFor(() => {
      expect(createAdmin).toHaveBeenCalledWith("nuevo_admin", "OtraSegura9");
    });
    expect(await screen.findByText(/admin "nuevo_admin" creado/i)).toBeInTheDocument();
  });

  it("shows the duplicate-username error when creating an admin", async () => {
    vi.mocked(createAdmin).mockRejectedValue({ detail: "Ese nombre de usuario ya existe." });
    const user = userEvent.setup();
    render(<AdminManagement />);

    await user.type(screen.getByLabelText(/nuevo usuario admin/i), "nuevo_admin");
    await user.type(screen.getByLabelText(/nueva contraseña admin/i), "OtraSegura9");
    await user.click(screen.getByRole("button", { name: /crear admin/i }));

    expect(await screen.findByText("Ese nombre de usuario ya existe.")).toBeInTheDocument();
  });

  it("changes the admin's own password", async () => {
    vi.mocked(changeOwnPassword).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<AdminManagement />);

    await user.type(screen.getByLabelText(/contraseña actual/i), "Sup3rSecreta");
    await user.type(screen.getByLabelText(/^contraseña nueva$/i), "NuevaClave9");
    await user.type(screen.getByLabelText(/confirmar contraseña nueva/i), "NuevaClave9");
    await user.click(screen.getByRole("button", { name: /cambiar contraseña/i }));

    await waitFor(() => {
      expect(changeOwnPassword).toHaveBeenCalledWith(
        "Sup3rSecreta",
        "NuevaClave9",
        "NuevaClave9"
      );
    });
    expect(await screen.findByText(/contraseña actualizada/i)).toBeInTheDocument();
  });

  it("shows the API error when the current password is wrong", async () => {
    vi.mocked(changeOwnPassword).mockRejectedValue({
      detail: "La contraseña actual es incorrecta.",
    });
    const user = userEvent.setup();
    render(<AdminManagement />);

    await user.type(screen.getByLabelText(/contraseña actual/i), "wrong");
    await user.type(screen.getByLabelText(/^contraseña nueva$/i), "NuevaClave9");
    await user.type(screen.getByLabelText(/confirmar contraseña nueva/i), "NuevaClave9");
    await user.click(screen.getByRole("button", { name: /cambiar contraseña/i }));

    expect(await screen.findByText("La contraseña actual es incorrecta.")).toBeInTheDocument();
  });

  it("never offers an action to edit or deactivate another admin", () => {
    render(<AdminManagement />);
    const buttons = screen.getAllByRole("button").map((button) => button.textContent);
    expect(buttons).toEqual(["Crear admin", "Cambiar contraseña"]);
  });
});
