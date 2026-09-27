import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginFormAdmin } from "./LoginFormAdmin";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("@/lib/api/auth", () => ({
  login: vi.fn(),
}));

import { login } from "@/lib/api/auth";

describe("LoginFormAdmin (T49, RF-1)", () => {
  beforeEach(() => {
    pushMock.mockClear();
    vi.mocked(login).mockReset();
  });

  it("renders username and password fields, and a submit button", () => {
    render(<LoginFormAdmin />);
    expect(screen.getByLabelText(/usuario/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ingresar/i })).toBeInTheDocument();
  });

  it("calls login('admin', ...) with the typed credentials and redirects on success", async () => {
    vi.mocked(login).mockResolvedValue({ id: 1, username: "ana", role: "ADMIN" });
    const user = userEvent.setup();
    render(<LoginFormAdmin />);

    await user.type(screen.getByLabelText(/usuario/i), "ana");
    await user.type(screen.getByLabelText(/contraseña/i), "Sup3rSecreta");
    await user.click(screen.getByRole("button", { name: /ingresar/i }));

    await waitFor(() => {
      expect(login).toHaveBeenCalledWith("admin", {
        username: "ana",
        password: "Sup3rSecreta",
      });
      expect(pushMock).toHaveBeenCalledWith("/admin");
    });
  });

  it("shows the exact API error message on failure, without redirecting", async () => {
    vi.mocked(login).mockRejectedValue({
      detail: "Usuario o contraseña incorrectos. Te quedan 4 intentos antes del bloqueo.",
    });
    const user = userEvent.setup();
    render(<LoginFormAdmin />);

    await user.type(screen.getByLabelText(/usuario/i), "ana");
    await user.type(screen.getByLabelText(/contraseña/i), "wrong");
    await user.click(screen.getByRole("button", { name: /ingresar/i }));

    expect(
      await screen.findByText(
        "Usuario o contraseña incorrectos. Te quedan 4 intentos antes del bloqueo."
      )
    ).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();
  });
});
