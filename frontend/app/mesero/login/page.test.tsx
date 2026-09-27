import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/api/auth", () => ({
  login: vi.fn(),
}));

import MeseroLoginPage from "./page";

describe("/mesero/login page (T50, RF-1)", () => {
  it("renders only the mesero login form (no admin password field)", () => {
    render(<MeseroLoginPage />);
    expect(screen.getByLabelText(/usuario/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Dígito 1" })).toBeInTheDocument();
    expect(screen.queryByLabelText(/contraseña/i)).not.toBeInTheDocument();
  });
});
