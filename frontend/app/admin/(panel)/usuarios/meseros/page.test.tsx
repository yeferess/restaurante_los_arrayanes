import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/lib/api/usuarios", () => ({
  createMesero: vi.fn(),
  resetMeseroPin: vi.fn(),
  deactivateMesero: vi.fn(),
  reactivateMesero: vi.fn(),
  unlockMesero: vi.fn(),
}));

import MeserosPage from "./page";

describe("/admin/usuarios/meseros page (T53)", () => {
  it("renders the mesero management screen", () => {
    render(<MeserosPage />);
    expect(screen.getByRole("heading", { name: /gestión de meseros/i })).toBeInTheDocument();
  });
});
