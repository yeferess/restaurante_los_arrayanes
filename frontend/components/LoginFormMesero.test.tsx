import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginFormMesero } from "./LoginFormMesero";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("@/lib/api/auth", () => ({
  login: vi.fn(),
}));

import { login } from "@/lib/api/auth";

describe("LoginFormMesero (T50, RF-1)", () => {
  beforeEach(() => {
    pushMock.mockClear();
    vi.mocked(login).mockReset();
  });

  it("renders a username field and a numeric keypad, with no free-text PIN input", () => {
    render(<LoginFormMesero />);
    expect(screen.getByLabelText(/usuario/i)).toBeInTheDocument();

    for (const digit of ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]) {
      expect(screen.getByRole("button", { name: `Dígito ${digit}` })).toBeInTheDocument();
    }
    expect(screen.queryByRole("textbox", { name: /pin/i })).not.toBeInTheDocument();
    expect(document.querySelector('input[type="password"]')).not.toBeInTheDocument();
  });

  it("builds the PIN from keypad taps and logs in with it, then redirects", async () => {
    vi.mocked(login).mockResolvedValue({ id: 2, username: "carlos", role: "MESERO" });
    const user = userEvent.setup();
    render(<LoginFormMesero />);

    await user.type(screen.getByLabelText(/usuario/i), "carlos");
    for (const digit of ["1", "2", "3", "4"]) {
      await user.click(screen.getByRole("button", { name: `Dígito ${digit}` }));
    }
    await user.click(screen.getByRole("button", { name: /ingresar/i }));

    await waitFor(() => {
      expect(login).toHaveBeenCalledWith("mesero", { username: "carlos", pin: "1234" });
      expect(pushMock).toHaveBeenCalledWith("/mesero");
    });
  });

  it("shows the exact API error message on failure and clears the PIN", async () => {
    vi.mocked(login).mockRejectedValue({
      detail: "Tu cuenta está bloqueada. Habla con un administrador para resolverlo.",
    });
    const user = userEvent.setup();
    render(<LoginFormMesero />);

    await user.type(screen.getByLabelText(/usuario/i), "carlos");
    for (const digit of ["1", "2", "3", "4"]) {
      await user.click(screen.getByRole("button", { name: `Dígito ${digit}` }));
    }
    await user.click(screen.getByRole("button", { name: /ingresar/i }));

    expect(
      await screen.findByText(
        "Tu cuenta está bloqueada. Habla con un administrador para resolverlo."
      )
    ).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("the backspace button removes the last digit", async () => {
    const user = userEvent.setup();
    render(<LoginFormMesero />);

    await user.click(screen.getByRole("button", { name: "Dígito 1" }));
    await user.click(screen.getByRole("button", { name: "Dígito 2" }));
    await user.click(screen.getByRole("button", { name: "Borrar" }));

    expect(screen.getByLabelText(/pin ingresado/i)).toHaveTextContent("•");
  });
});
