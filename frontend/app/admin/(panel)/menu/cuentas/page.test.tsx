import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/lib/api/payments", () => ({
  listAccounts: vi.fn().mockResolvedValue([]),
  createAccount: vi.fn(),
  deleteAccount: vi.fn(),
}));

import CuentasPage from "./page";

describe("/admin/menu/cuentas page (005-cobro, RF-2)", () => {
  it("renders the payment accounts management screen", () => {
    render(<CuentasPage />);
    expect(
      screen.getByRole("heading", { name: /opciones de pago/i })
    ).toBeInTheDocument();
  });
});
