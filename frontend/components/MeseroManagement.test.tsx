import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MeseroManagement } from "./MeseroManagement";

vi.mock("@/lib/api/usuarios", () => ({
  listMeseros: vi.fn(),
  createMesero: vi.fn(),
  resetMeseroPin: vi.fn(),
  deactivateMesero: vi.fn(),
  reactivateMesero: vi.fn(),
  unlockMesero: vi.fn(),
}));

import {
  listMeseros,
  createMesero,
  resetMeseroPin,
  deactivateMesero,
  reactivateMesero,
  unlockMesero,
} from "@/lib/api/usuarios";

const MESEROS = [
  {
    id: 7,
    username: "carlos",
    role: "MESERO" as const,
    is_active: true,
    created_by: 1,
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: 8,
    username: "ines",
    role: "MESERO" as const,
    is_active: false,
    created_by: 1,
    created_at: "2026-01-01T00:00:00Z",
  },
];

describe("MeseroManagement (T53, RF-2/3/4/5/7)", () => {
  beforeEach(() => {
    vi.mocked(listMeseros).mockReset();
    vi.mocked(createMesero).mockReset();
    vi.mocked(resetMeseroPin).mockReset();
    vi.mocked(deactivateMesero).mockReset();
    vi.mocked(reactivateMesero).mockReset();
    vi.mocked(unlockMesero).mockReset();
    vi.mocked(listMeseros).mockResolvedValue(MESEROS);
  });

  it("creates a mesero and shows the confirmation", async () => {
    vi.mocked(createMesero).mockResolvedValue({
      id: 9,
      username: "nuevo",
      role: "MESERO",
      is_active: true,
      created_by: 1,
      created_at: "2026-01-01T00:00:00Z",
    });
    const user = userEvent.setup();
    render(<MeseroManagement />);
    await screen.findAllByText(/carlos/i);

    await user.type(screen.getByLabelText(/nuevo usuario/i), "nuevo");
    await user.type(screen.getByLabelText(/nuevo pin \(crear\)/i), "1234");
    await user.click(screen.getByRole("button", { name: /crear mesero/i }));

    await waitFor(() => {
      expect(createMesero).toHaveBeenCalledWith("nuevo", "1234");
    });
    expect(await screen.findByText(/mesero "nuevo" creado/i)).toBeInTheDocument();
  });

  it("shows the duplicate-username error when creating a mesero", async () => {
    vi.mocked(createMesero).mockRejectedValue({ detail: "Ese nombre de usuario ya existe." });
    const user = userEvent.setup();
    render(<MeseroManagement />);
    await screen.findAllByText(/carlos/i);

    await user.type(screen.getByLabelText(/nuevo usuario/i), "carlos");
    await user.type(screen.getByLabelText(/nuevo pin \(crear\)/i), "1234");
    await user.click(screen.getByRole("button", { name: /crear mesero/i }));

    expect(await screen.findByText("Ese nombre de usuario ya existe.")).toBeInTheDocument();
  });

  it("lists every mesero in the dropdowns, including inactive ones", async () => {
    render(<MeseroManagement />);
    const options = await screen.findAllByRole("option", { name: /carlos/i });
    expect(options.length).toBeGreaterThan(0);
    expect(screen.getAllByRole("option", { name: /ines/i }).length).toBeGreaterThan(0);
  });

  it("resets a mesero's PIN using the dropdown", async () => {
    vi.mocked(resetMeseroPin).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<MeseroManagement />);
    await screen.findAllByText(/carlos/i);

    await user.selectOptions(screen.getByLabelText(/mesero \(restablecer pin\)/i), "7");
    await user.type(screen.getByLabelText(/nuevo pin \(restablecer\)/i), "9999");
    await user.click(screen.getByRole("button", { name: /restablecer pin/i }));

    await waitFor(() => expect(resetMeseroPin).toHaveBeenCalledWith(7, "9999"));
    expect(await screen.findByText(/pin restablecido/i)).toBeInTheDocument();
  });

  it("deactivates a mesero using the dropdown", async () => {
    vi.mocked(deactivateMesero).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<MeseroManagement />);
    await screen.findAllByText(/carlos/i);

    await user.selectOptions(screen.getByLabelText(/mesero \(desactivar\)/i), "7");
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
    await screen.findAllByText(/carlos/i);

    await user.selectOptions(screen.getByLabelText(/mesero \(desactivar\)/i), "7");
    await user.click(screen.getByRole("button", { name: /^desactivar$/i }));

    expect(
      await screen.findByText("El mesero tiene mesas o pedidos abiertos.")
    ).toBeInTheDocument();
  });

  it("reactivates a mesero using the dropdown", async () => {
    vi.mocked(reactivateMesero).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<MeseroManagement />);
    await screen.findAllByText(/carlos/i);

    await user.selectOptions(screen.getByLabelText(/mesero \(reactivar\)/i), "8");
    await user.click(screen.getByRole("button", { name: /^reactivar$/i }));

    await waitFor(() => expect(reactivateMesero).toHaveBeenCalledWith(8));
    expect(await screen.findByText(/mesero reactivado/i)).toBeInTheDocument();
  });

  it("unlocks a mesero with a new PIN using the dropdown", async () => {
    vi.mocked(unlockMesero).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<MeseroManagement />);
    await screen.findAllByText(/carlos/i);

    await user.selectOptions(screen.getByLabelText(/mesero \(desbloquear\)/i), "7");
    await user.type(screen.getByLabelText(/pin de desbloqueo/i), "5555");
    await user.click(screen.getByRole("button", { name: /^desbloquear$/i }));

    await waitFor(() => expect(unlockMesero).toHaveBeenCalledWith(7, "5555"));
    expect(await screen.findByText(/mesero desbloqueado/i)).toBeInTheDocument();
  });

  it("shows the 409 not-locked detail when unlocking is rejected", async () => {
    vi.mocked(unlockMesero).mockRejectedValue({ detail: "Esta cuenta no está bloqueada." });
    const user = userEvent.setup();
    render(<MeseroManagement />);
    await screen.findAllByText(/carlos/i);

    await user.selectOptions(screen.getByLabelText(/mesero \(desbloquear\)/i), "7");
    await user.type(screen.getByLabelText(/pin de desbloqueo/i), "5555");
    await user.click(screen.getByRole("button", { name: /^desbloquear$/i }));

    expect(await screen.findByText("Esta cuenta no está bloqueada.")).toBeInTheDocument();
  });
});
