import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChargeOrderModal } from "./ChargeOrderModal";

vi.mock("@/lib/api/payments", () => ({
  listAccounts: vi.fn(),
  voidCharge: vi.fn(),
}));
vi.mock("@/lib/api/orders", () => ({
  chargeOrder: vi.fn(),
}));

import { listAccounts, voidCharge } from "@/lib/api/payments";
import { chargeOrder } from "@/lib/api/orders";

const ORDER = {
  id: 41,
  table_number: 5,
  waiter_id: 1,
  waiter_username: "mesero1",
  status: "IN_PROGRESS" as const,
  delivered: false,
  items: [
    {
      id: 1,
      order_id: 41,
      name: "Limonada natural",
      unit_price: "4.50",
      quantity: 2,
      note: "",
      line_type: "ORIGINAL" as const,
      is_voided: false,
      void_reason: null,
    },
  ],
  total: "9.00",
  has_pending_print: false,
  active_payment: null,
  daily_number: 7,
  sent_at: "2026-03-10T20:15:00Z",
};

const ACCOUNTS = [
  { id: 1, name: "Efectivo", is_fixed: true },
  { id: 2, name: "Nequi #1234", is_fixed: false },
];

describe("ChargeOrderModal (005-cobro, RF-1/3/4)", () => {
  const onClose = vi.fn();
  const onCharged = vi.fn();

  beforeEach(() => {
    vi.mocked(listAccounts).mockReset();
    vi.mocked(chargeOrder).mockReset();
    vi.mocked(voidCharge).mockReset();
    onClose.mockReset();
    onCharged.mockReset();
    vi.mocked(listAccounts).mockResolvedValue(ACCOUNTS);
  });

  it("shows the order total and the list of payment options", async () => {
    render(
      <ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />
    );
    expect((await screen.findAllByText(/9,00/)).length).toBeGreaterThan(0);
    expect(screen.getByRole("option", { name: "Efectivo" })).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "Nequi #1234" })
    ).toBeInTheDocument();
  });

  it("shows the total with a thousands separator", async () => {
    render(
      <ChargeOrderModal
        order={{ ...ORDER, total: "20000.00" }}
        onClose={onClose}
        onCharged={onCharged}
      />
    );
    expect(await screen.findByText("$20.000,00")).toBeInTheDocument();
  });

  it("charges the order and shows a confirmation with an undo option (T29, RF-6)", async () => {
    const charged = {
      ...ORDER,
      status: "CHARGED" as const,
      active_payment: {
        account_name: "Nequi #1234",
        amount: "9.00",
        charged_by: "admin1",
        charged_at: "2026-03-10T20:15:00Z",
      },
    };
    vi.mocked(chargeOrder).mockResolvedValue(charged);
    const user = userEvent.setup();
    render(
      <ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />
    );
    await screen.findByRole("option", { name: "Nequi #1234" });

    await user.selectOptions(screen.getByLabelText(/opción de pago/i), "2");
    await user.click(screen.getByRole("button", { name: /^cobrar$/i }));

    await waitFor(() => expect(chargeOrder).toHaveBeenCalledWith(41, 2));
    expect(await screen.findByText(/nequi #1234/i)).toBeInTheDocument();
    expect(onCharged).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /cerrar/i }));
    expect(onCharged).toHaveBeenCalledWith(charged);
  });

  it("undoes the charge with a reason from the confirmation view", async () => {
    const charged = {
      ...ORDER,
      status: "CHARGED" as const,
      active_payment: {
        account_name: "Efectivo",
        amount: "9.00",
        charged_by: "admin1",
        charged_at: "2026-03-10T20:15:00Z",
      },
    };
    vi.mocked(chargeOrder).mockResolvedValue(charged);
    vi.mocked(voidCharge).mockResolvedValue({
      ...ORDER,
      status: "IN_PROGRESS",
      active_payment: null,
    });
    vi.spyOn(window, "prompt").mockReturnValue("Cuenta equivocada");
    const user = userEvent.setup();
    render(
      <ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />
    );
    await screen.findByRole("option", { name: "Efectivo" });
    await user.click(screen.getByRole("button", { name: /^cobrar$/i }));
    await screen.findByText(/efectivo/i);

    await user.click(screen.getByRole("button", { name: /anular cobro/i }));

    await waitFor(() =>
      expect(voidCharge).toHaveBeenCalledWith(41, "Cuenta equivocada")
    );
    await waitFor(() =>
      expect(onCharged).toHaveBeenCalledWith({
        ...ORDER,
        status: "IN_PROGRESS",
        active_payment: null,
      })
    );
  });

  it("shows the error when undoing the charge fails", async () => {
    const charged = {
      ...ORDER,
      status: "CHARGED" as const,
      active_payment: {
        account_name: "Efectivo",
        amount: "9.00",
        charged_by: "admin1",
        charged_at: "2026-03-10T20:15:00Z",
      },
    };
    vi.mocked(chargeOrder).mockResolvedValue(charged);
    vi.mocked(voidCharge).mockRejectedValue({
      detail: "La mesa ya tiene un pedido nuevo; no se puede anular este cobro.",
    });
    vi.spyOn(window, "prompt").mockReturnValue("Cuenta equivocada");
    const user = userEvent.setup();
    render(
      <ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />
    );
    await screen.findByRole("option", { name: "Efectivo" });
    await user.click(screen.getByRole("button", { name: /^cobrar$/i }));
    await screen.findByText(/efectivo/i);

    await user.click(screen.getByRole("button", { name: /anular cobro/i }));

    expect(
      await screen.findByText(
        "La mesa ya tiene un pedido nuevo; no se puede anular este cobro."
      )
    ).toBeInTheDocument();
  });

  it("shows the error when charging fails", async () => {
    vi.mocked(chargeOrder).mockRejectedValue({
      detail: "Este pedido no admite cobro en este momento.",
    });
    const user = userEvent.setup();
    render(
      <ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />
    );
    await screen.findByRole("option", { name: "Efectivo" });

    await user.click(screen.getByRole("button", { name: /^cobrar$/i }));

    expect(
      await screen.findByText("Este pedido no admite cobro en este momento.")
    ).toBeInTheDocument();
  });

  it("identifies the order by its daily number, not the internal id (T31, 003-RF-14)", async () => {
    render(
      <ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />
    );
    await screen.findByRole("option", { name: "Efectivo" });
    expect(screen.getByText(/N° 7 — Mesa 5/)).toBeInTheDocument();
    expect(screen.getByText(/\d{2}\/\d{2} \d{2}:\d{2}/)).toBeInTheDocument();
    expect(screen.queryByText(/pedido 41/i)).not.toBeInTheDocument();
  });

  it("shows the daily number on the post-charge confirmation too", async () => {
    const charged = {
      ...ORDER,
      status: "CHARGED" as const,
      active_payment: {
        account_name: "Efectivo",
        amount: "9.00",
        charged_by: "admin1",
        charged_at: "2026-03-10T20:15:00Z",
      },
    };
    vi.mocked(chargeOrder).mockResolvedValue(charged);
    const user = userEvent.setup();
    render(
      <ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />
    );
    await screen.findByRole("option", { name: "Efectivo" });

    await user.click(screen.getByRole("button", { name: /^cobrar$/i }));

    expect(await screen.findByText(/N° 7 cobrado/)).toBeInTheDocument();
    expect(screen.queryByText(/pedido 41/i)).not.toBeInTheDocument();
  });

  it("falls back to a blank daily number for a pre-upgrade order", async () => {
    render(
      <ChargeOrderModal
        order={{ ...ORDER, daily_number: null, sent_at: null }}
        onClose={onClose}
        onCharged={onCharged}
      />
    );
    await screen.findByRole("option", { name: "Efectivo" });
    expect(screen.getByText(/Sin número — Mesa 5/)).toBeInTheDocument();
  });

  it("closes without charging on cancel", async () => {
    const user = userEvent.setup();
    render(
      <ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />
    );
    await screen.findByRole("option", { name: "Efectivo" });

    await user.click(screen.getByRole("button", { name: /cancelar/i }));

    expect(onClose).toHaveBeenCalled();
    expect(chargeOrder).not.toHaveBeenCalled();
  });
});
