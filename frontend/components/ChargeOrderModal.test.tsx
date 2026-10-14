import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChargeOrderModal } from "./ChargeOrderModal";

vi.mock("@/lib/api/payments", () => ({
  listAccounts: vi.fn(),
  voidCharge: vi.fn(),
  previewCharge: vi.fn(),
  printReceipt: vi.fn(),
  printBill: vi.fn(),
}));
vi.mock("@/lib/api/orders", () => ({
  chargeOrder: vi.fn(),
  getOrder: vi.fn(),
  setAdminNote: vi.fn(),
}));
vi.mock("@/lib/api/ordersSocket", () => ({
  subscribeToOrderUpdates: vi.fn(),
}));

import {
  listAccounts,
  voidCharge,
  previewCharge,
  printReceipt,
  printBill,
} from "@/lib/api/payments";
import { chargeOrder, getOrder, setAdminNote } from "@/lib/api/orders";
import { subscribeToOrderUpdates } from "@/lib/api/ordersSocket";

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
      line_total: "9.00",
    },
  ],
  total: "9.00",
  has_pending_print: false,
  active_payment: null,
  daily_number: 7,
  sent_at: "2026-03-10T20:15:00Z",
  created_at: "2026-03-10T18:55:00Z",
  draft_reminder: false,
};

const ACCOUNTS = [
  { id: 1, name: "Efectivo", is_fixed: true },
  { id: 2, name: "Nequi #1234", is_fixed: false },
];

describe("ChargeOrderModal (005-cobro, RF-1/3/4)", () => {
  const onClose = vi.fn();
  const onCharged = vi.fn();
  const closeSocket = vi.fn();

  beforeEach(() => {
    vi.mocked(listAccounts).mockReset();
    vi.mocked(chargeOrder).mockReset();
    vi.mocked(voidCharge).mockReset();
    vi.mocked(previewCharge).mockReset();
    vi.mocked(printReceipt).mockReset();
    vi.mocked(printBill).mockReset();
    onClose.mockReset();
    onCharged.mockReset();
    vi.mocked(listAccounts).mockResolvedValue(ACCOUNTS);
    // By default the fresh copy never arrives, so each test sees its prop.
    vi.mocked(getOrder).mockReset();
    vi.mocked(getOrder).mockReturnValue(new Promise(() => {}));
    closeSocket.mockReset();
    vi.mocked(subscribeToOrderUpdates).mockReset();
    vi.mocked(subscribeToOrderUpdates).mockReturnValue({ close: closeSocket });
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

  it("shows each line's backend total, not a computed one (RF-4)", async () => {
    render(
      <ChargeOrderModal
        order={{ ...ORDER, items: [{ ...ORDER.items[0], line_total: "123.00" }] }}
        onClose={onClose}
        onCharged={onCharged}
      />
    );
    expect(await screen.findByText("$123,00")).toBeInTheDocument();
  });

  it("previews the total to pay and charges with the discount (RF-10)", async () => {
    vi.mocked(previewCharge).mockResolvedValue({
      subtotal: "9.00",
      discount: "2",
      total: "7.00",
    });
    vi.mocked(chargeOrder).mockResolvedValue({
      ...ORDER,
      status: "CHARGED" as const,
      active_payment: {
        account_name: "Efectivo",
        subtotal: "9.00",
        discount: "2.00",
        discount_reason: "cliente frecuente",
        amount: "7.00",
        charged_by: "admin1",
        charged_at: "2026-03-10T20:15:00Z",
      },
    });
    const user = userEvent.setup();
    render(<ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />);
    await screen.findByRole("option", { name: "Efectivo" });

    await user.type(screen.getByLabelText(/descuento \(opcional/i), "2");
    await user.type(screen.getByLabelText(/motivo del descuento/i), "cliente frecuente");

    expect(await screen.findByText("$7,00")).toBeInTheDocument();
    expect(previewCharge).toHaveBeenLastCalledWith(41, 2);

    await user.click(screen.getByRole("button", { name: /^cobrar$/i }));

    await waitFor(() =>
      expect(chargeOrder).toHaveBeenCalledWith(
        41,
        1,
        { amount: 2, reason: "cliente frecuente" },
        "9.00"
      )
    );
    expect(await screen.findByText(/descuento −\$2,00 \(cliente frecuente\)/i)).toBeInTheDocument();
  });

  it("blocks charging while the discount is invalid", async () => {
    vi.mocked(previewCharge).mockRejectedValue({
      detail: ["El descuento no puede ser mayor que el total del pedido."],
    });
    const user = userEvent.setup();
    render(<ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />);
    await screen.findByRole("option", { name: "Efectivo" });

    await user.type(screen.getByLabelText(/descuento \(opcional/i), "99");

    expect(await screen.findByText(/no puede ser mayor/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^cobrar$/i })).toBeDisabled();
  });

  it("shows the admin note in an editable field (003 RF-17)", async () => {
    render(
      <ChargeOrderModal
        order={{ ...ORDER, admin_note: "mesa de cumpleanos" }}
        onClose={onClose}
        onCharged={onCharged}
      />
    );
    expect(await screen.findByLabelText(/nota del pedido/i)).toHaveValue("mesa de cumpleanos");
  });

  it("offers the note field even when the order has no note yet", async () => {
    render(<ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />);
    expect(await screen.findByLabelText(/nota del pedido/i)).toHaveValue("");
  });

  it("saves the note from the charge window", async () => {
    vi.mocked(setAdminNote).mockReset();
    vi.mocked(setAdminNote).mockResolvedValue({ ...ORDER, admin_note: "paga con tarjeta" });
    const user = userEvent.setup();
    render(<ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />);

    await user.type(await screen.findByLabelText(/nota del pedido/i), "paga con tarjeta");
    await user.click(screen.getByRole("button", { name: /guardar/i }));

    expect(setAdminNote).toHaveBeenCalledWith(41, "paga con tarjeta");
    expect(await screen.findByText(/nota guardada/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/nota del pedido/i)).toHaveValue("paga con tarjeta");
  });

  it("shows the latest note when the fresh copy of the order arrives", async () => {
    vi.mocked(getOrder).mockResolvedValue({ ...ORDER, admin_note: "nota nueva" });
    render(<ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />);
    await waitFor(() =>
      expect(screen.getByLabelText(/nota del pedido/i)).toHaveValue("nota nueva")
    );
  });

  it("prints the customer receipt after charging (RF-11)", async () => {
    vi.mocked(chargeOrder).mockResolvedValue({
      ...ORDER,
      status: "CHARGED" as const,
      active_payment: {
        account_name: "Efectivo",
        subtotal: "9.00",
        discount: "0.00",
        discount_reason: "",
        amount: "9.00",
        charged_by: "admin1",
        charged_at: "2026-03-10T20:15:00Z",
      },
    });
    vi.mocked(printReceipt).mockResolvedValue({ print_warning: null });
    const user = userEvent.setup();
    render(<ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />);
    await screen.findByRole("option", { name: "Efectivo" });
    await user.click(screen.getByRole("button", { name: /^cobrar$/i }));

    await user.click(await screen.findByRole("button", { name: /imprimir comprobante/i }));

    expect(printReceipt).toHaveBeenCalledWith(41);
    expect(await screen.findByText(/comprobante impreso/i)).toBeInTheDocument();
  });

  it("charges the order and shows a confirmation with an undo option (T29, RF-6)", async () => {
    const charged = {
      ...ORDER,
      status: "CHARGED" as const,
      active_payment: {
        account_name: "Nequi #1234",
        subtotal: "9.00",
        discount: "0.00",
        discount_reason: "",
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

    await waitFor(() => expect(chargeOrder).toHaveBeenCalledWith(41, 2, undefined, "9.00"));
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
        subtotal: "9.00",
        discount: "0.00",
        discount_reason: "",
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
        subtotal: "9.00",
        discount: "0.00",
        discount_reason: "",
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
        subtotal: "9.00",
        discount: "0.00",
        discount_reason: "",
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

  // 005 RF-12 / T94 — la ventana de cobrar nunca muestra una copia vieja.
  it("re-fetches the order on open and shows an addition made meanwhile (RF-12)", async () => {
    const withAddition = {
      ...ORDER,
      items: [
        ...ORDER.items,
        { ...ORDER.items[0], id: 2, name: "Churrasco", line_type: "ADDITION" as const, line_total: "32.00", quantity: 1, unit_price: "32.00" },
      ],
      total: "41.00",
    };
    vi.mocked(getOrder).mockResolvedValue(withAddition);
    render(<ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />);

    expect(await screen.findByText(/churrasco/i)).toBeInTheDocument();
    expect(screen.getByText("$41,00")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/el pedido cambió/i);
    expect(getOrder).toHaveBeenCalledWith(41);
  });

  it("updates itself when an order change is notified while open (RF-12)", async () => {
    render(<ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />);
    await screen.findByRole("option", { name: "Efectivo" });
    expect(screen.queryByText(/el pedido cambió/i)).not.toBeInTheDocument();

    vi.mocked(getOrder).mockResolvedValue({ ...ORDER, total: "15.00" });
    const onOrdersChanged = vi.mocked(subscribeToOrderUpdates).mock.calls[0][0];
    onOrdersChanged();

    expect(await screen.findByText("$15,00")).toBeInTheDocument();
    expect(screen.getByText(/el pedido cambió/i)).toBeInTheDocument();
  });

  it("sends the total on screen and reloads when the backend says it changed (RF-12)", async () => {
    vi.mocked(chargeOrder).mockRejectedValue({
      detail: ["El pedido cambió mientras se cobraba (se agregaron o anularon ítems). Revisa los ítems y el total antes de cobrar."],
    });
    const user = userEvent.setup();
    render(<ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />);
    await screen.findByRole("option", { name: "Efectivo" });

    vi.mocked(getOrder).mockResolvedValue({ ...ORDER, total: "41.00" });
    await user.click(screen.getByRole("button", { name: /^cobrar$/i }));

    expect(chargeOrder).toHaveBeenCalledWith(41, 1, undefined, "9.00");
    expect(await screen.findByText(/cambió mientras se cobraba/i)).toBeInTheDocument();
    expect(await screen.findByText("$41,00")).toBeInTheDocument();
  });

  it("closes the order subscription when the window closes", () => {
    const { unmount } = render(
      <ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />
    );
    unmount();
    expect(closeSocket).toHaveBeenCalled();
  });

  describe("bill before paying (T39, RF-13)", () => {
    it("prints the bill without a discount and keeps the window open", async () => {
      vi.mocked(printBill).mockResolvedValue({ print_warning: null });
      const user = userEvent.setup();
      render(<ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />);
      await screen.findByRole("option", { name: "Efectivo" });

      await user.click(screen.getByRole("button", { name: /imprimir cuenta/i }));

      expect(printBill).toHaveBeenCalledWith(41, undefined);
      expect(await screen.findByText("Cuenta impresa.")).toBeInTheDocument();
      expect(chargeOrder).not.toHaveBeenCalled();
      expect(onClose).not.toHaveBeenCalled();
      expect(screen.getByRole("button", { name: /^cobrar$/i })).toBeInTheDocument();
    });

    it("prints the bill with the discount typed in the window", async () => {
      vi.mocked(previewCharge).mockResolvedValue({ subtotal: "9.00", discount: "2", total: "7.00" });
      vi.mocked(printBill).mockResolvedValue({ print_warning: null });
      const user = userEvent.setup();
      render(<ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />);
      await screen.findByRole("option", { name: "Efectivo" });

      await user.type(screen.getByLabelText(/descuento \(opcional/i), "2");
      expect(await screen.findByText("$7,00")).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: /imprimir cuenta/i }));

      expect(printBill).toHaveBeenCalledWith(41, 2);
    });

    it("shows the printer warning", async () => {
      vi.mocked(printBill).mockResolvedValue({ print_warning: "Impresora no detectada." });
      const user = userEvent.setup();
      render(<ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />);
      await screen.findByRole("option", { name: "Efectivo" });
      await user.click(screen.getByRole("button", { name: /imprimir cuenta/i }));
      expect(await screen.findByText("Impresora no detectada.")).toBeInTheDocument();
    });

    it("cannot print the bill while the discount is invalid", async () => {
      vi.mocked(previewCharge).mockRejectedValue({
        detail: ["El descuento no puede ser mayor que el total del pedido."],
      });
      const user = userEvent.setup();
      render(<ChargeOrderModal order={ORDER} onClose={onClose} onCharged={onCharged} />);
      await screen.findByRole("option", { name: "Efectivo" });
      await user.type(screen.getByLabelText(/descuento \(opcional/i), "99");
      expect(await screen.findByText(/no puede ser mayor/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /imprimir cuenta/i })).toBeDisabled();
    });
  });
});
