import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PaymentAccountsManagement } from "./PaymentAccountsManagement";

vi.mock("@/lib/api/payments", () => ({
  listAccounts: vi.fn(),
  createAccount: vi.fn(),
  deleteAccount: vi.fn(),
}));

import { listAccounts, createAccount, deleteAccount } from "@/lib/api/payments";

const ACCOUNTS = [
  { id: 1, name: "Efectivo", is_fixed: true },
  { id: 2, name: "Nequi #1234", is_fixed: false },
];

describe("PaymentAccountsManagement (005-cobro, RF-2)", () => {
  beforeEach(() => {
    vi.mocked(listAccounts).mockReset();
    vi.mocked(createAccount).mockReset();
    vi.mocked(deleteAccount).mockReset();
    vi.mocked(listAccounts).mockResolvedValue(ACCOUNTS);
  });

  it("lists the catalog including the fixed Efectivo account", async () => {
    render(<PaymentAccountsManagement />);
    expect(await screen.findByText("Efectivo")).toBeInTheDocument();
    expect(screen.getByText("Nequi #1234")).toBeInTheDocument();
  });

  it("does not offer a delete button for Efectivo", async () => {
    render(<PaymentAccountsManagement />);
    await screen.findByText("Efectivo");
    const rows = screen.getAllByRole("listitem");
    const efectivoRow = rows.find((row) => row.textContent?.includes("Efectivo"));
    expect(efectivoRow).toBeTruthy();
    expect(
      within(efectivoRow as HTMLElement).queryByRole("button", {
        name: /eliminar/i,
      })
    ).not.toBeInTheDocument();
  });

  it("creates a new account", async () => {
    vi.mocked(createAccount).mockResolvedValue({
      id: 3,
      name: "Bancolombia Ahorros",
      is_fixed: false,
    });
    const user = userEvent.setup();
    render(<PaymentAccountsManagement />);
    await screen.findByText("Efectivo");

    await user.type(screen.getByLabelText(/nueva cuenta/i), "Bancolombia Ahorros");
    await user.click(screen.getByRole("button", { name: /crear cuenta/i }));

    await waitFor(() =>
      expect(createAccount).toHaveBeenCalledWith("Bancolombia Ahorros")
    );
  });

  it("shows the 409 error when creating a duplicate account", async () => {
    vi.mocked(createAccount).mockRejectedValue({
      detail: "Ya existe una cuenta con ese nombre.",
    });
    const user = userEvent.setup();
    render(<PaymentAccountsManagement />);
    await screen.findByText("Efectivo");

    await user.type(screen.getByLabelText(/nueva cuenta/i), "Nequi #1234");
    await user.click(screen.getByRole("button", { name: /crear cuenta/i }));

    expect(
      await screen.findByText("Ya existe una cuenta con ese nombre.")
    ).toBeInTheDocument();
  });

  it("deletes an unused account", async () => {
    vi.mocked(deleteAccount).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<PaymentAccountsManagement />);
    await screen.findByText("Nequi #1234");

    await user.click(screen.getByRole("button", { name: /eliminar/i }));

    await waitFor(() => expect(deleteAccount).toHaveBeenCalledWith(2));
  });

  it("shows the 409 error when deleting an account already in use", async () => {
    vi.mocked(deleteAccount).mockRejectedValue({
      detail: "Esta cuenta ya se usó en un cobro y no se puede eliminar.",
    });
    const user = userEvent.setup();
    render(<PaymentAccountsManagement />);
    await screen.findByText("Nequi #1234");

    await user.click(screen.getByRole("button", { name: /eliminar/i }));

    expect(
      await screen.findByText(
        "Esta cuenta ya se usó en un cobro y no se puede eliminar."
      )
    ).toBeInTheDocument();
  });
});
