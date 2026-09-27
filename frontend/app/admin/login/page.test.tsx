import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/api/auth", () => ({
  login: vi.fn(),
}));

import AdminLoginPage from "./page";

describe("/admin/login page (T49, RF-1)", () => {
  it("renders only the admin login form", () => {
    render(<AdminLoginPage />);
    expect(screen.getByLabelText(/usuario/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument();
    expect(screen.queryByText(/pin/i)).not.toBeInTheDocument();
  });
});
