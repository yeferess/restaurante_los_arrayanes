import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MeseroManagement } from "./MeseroManagement";

vi.mock("@/lib/api/usuarios", () => ({
  createMesero: vi.fn(),
  resetMeseroPin: vi.fn(),
  deactivateMesero: vi.fn(),
  reactivateMesero: vi.fn(),
  unlockMesero: vi.fn(),
}));

import {
  createMesero,
  resetMeseroPin,
  deactivateMesero,
  reactivateMesero,
  unlockMesero,
} from "@/lib/api/usuarios";

describe("MeseroManagement (T53, RF-2/3/4/5/7)", () => {
  beforeEach(() => {
    vi.mocked(createMesero).mockReset();
    vi.mocked(resetMeseroPin).mockReset();
    vi.mocked(deactivateMesero).mockReset();
    vi.mocked(reactivateMesero).mockReset();
    vi.mocked(unlockMesero).mockReset();
  });

  it("creates a mesero and shows the confirmation", async () => {
    vi.mocked(createMesero).mockResolvedValue({
      id: 7,
      username: "carlos",
      role: "MESERO",
      is_active: true,
      created_by: 1,
      created_at: "2026-01-01T00:00:00Z",
    });
    const user = userEvent.setup();
    render(<MeseroManagement />);

    await user.type(screen.getByLabelText(/nuevo usuario/i), "carlos");
    await user.type(screen.getByLabelText(/nuevo pin \(crear\)/i), "1234");
    await user.click(screen.getByRole("button", { name: /crear mesero/i }));

    await waitFor(() => {
      expect(createMesero).toHaveBeenCalledWith("carlos", "1234");
    });
    expect(await screen.findByText(/mesero "carlos" creado/i)).toBeInTheDocument();
  });

  it("shows the duplicate-username error when creating a mesero", async () => {
    vi.mocked(createMesero).mockRejectedValue({ detail: "Ese nombre de usuario ya existe." });
    const user = userEvent.setup();
    render(<MeseroManagement />);

    await user.type(screen.getByLabelText(/nuevo usuario/i), "carlos");
    await user.type(screen.getByLabelText(/nuevo pin \(crear\)/i), "1234");
    await user.click(screen.getByRole("button", { name: /crear mesero/i }));

    expect(await screen.findByText("Ese nombre de usuario ya existe.")).toBeInTheDocument();
  });

  it("resets a mesero's PIN", async () => {
    vi.mocked(resetMeseroPin).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<MeseroManagement />);

    await user.type(screen.getByLabelText(/id del mesero \(pin\)/i), "7");
    await user.type(screen.getByLabelText(/nuevo pin \(restablecer\)/i), "9999");
    await user.click(screen.getByRole("button", { name: /restablecer pin/i }));

    await waitFor(() => expect(resetMeseroPin).toHaveBeenCalledWith(7, "9999"));
    expect(await screen.findByText(/pin restablecido/i)).toBeInTheDocument();
  });

  it("deactivates a mesero", async () => {
    vi.mocked(deactivateMesero).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<MeseroManagement />);

    await user.type(screen.getByLabelText(/id del mesero \(desactivar\)/i), "7");
    await user.click(screen.getByRole("button", { name: /^desactivar$/i }));

    await waitFor(() => expect(deactivateMesero).toHaveBeenCalledWith(7));
    expect(await screen.findByText(/mesero desactivado/i)).toBeInTheDocument();
  });

  it("shows the 409 open-tables detail when deactivation is rejected", async () => {
    vi.mocked(deactivateMesero).mockRejectedValue({
      detail: "El mesero tiene mesas o pedidos abiertos.",
    });
    const user = userEvent.setup();
    render(<MeseroManagement />);

    await user.type(screen.getByLabelText(/id del mesero \(desactivar\)/i), "7");
    await user.click(screen.getByRole("button", { name: /^desactivar$/i }));

    expect(
      await screen.findByText("El mesero tiene mesas o pedidos abiertos.")
    ).toBeInTheDocument();
  });

  it("reactivates a mesero", async () => {
    vi.mocked(reactivateMesero).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<MeseroManagement />);

    await user.type(screen.getByLabelText(/id del mesero \(reactivar\)/i), "7");
    await user.click(screen.getByRole("button", { name: /^reactivar$/i }));

    await waitFor(() => expect(reactivateMesero).toHaveBeenCalledWith(7));
    expect(await screen.findByText(/mesero reactivado/i)).toBeInTheDocument();
  });

  it("unlocks a mesero with a new PIN", async () => {
    vi.mocked(unlockMesero).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<MeseroManagement />);

    await user.type(screen.getByLabelText(/id del mesero \(desbloquear\)/i), "7");
    await user.type(screen.getByLabelText(/pin de desbloqueo/i), "5555");
    await user.click(screen.getByRole("button", { name: /^desbloquear$/i }));

    await waitFor(() => expect(unlockMesero).toHaveBeenCalledWith(7, "5555"));
    expect(await screen.findByText(/mesero desbloqueado/i)).toBeInTheDocument();
  });

  it("shows the 409 not-locked detail when unlocking is rejected", async () => {
    vi.mocked(unlockMesero).mockRejectedValue({ detail: "Esta cuenta no está bloqueada." });
    const user = userEvent.setup();
    render(<MeseroManagement />);

    await user.type(screen.getByLabelText(/id del mesero \(desbloquear\)/i), "7");
    await user.type(screen.getByLabelText(/pin de desbloqueo/i), "5555");
    await user.click(screen.getByRole("button", { name: /^desbloquear$/i }));

    expect(await screen.findByText("Esta cuenta no está bloqueada.")).toBeInTheDocument();
  });
});
