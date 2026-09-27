import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/lib/api/usuarios", () => ({
  createAdmin: vi.fn(),
  changeOwnPassword: vi.fn(),
}));

import AdminsPage from "./page";

describe("/admin/usuarios/admins page (T54)", () => {
  it("renders the admin management screen", () => {
    render(<AdminsPage />);
    expect(
      screen.getByRole("heading", { name: /gestión de administradores/i })
    ).toBeInTheDocument();
  });
});
