import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChargedOrdersPanel } from "./ChargedOrdersPanel";

vi.mock("@/lib/api/orders", () => ({
  listChargedOrders: vi.fn(),
  reprintOrder: vi.fn(),
  setAdminNote: vi.fn(),
}));
vi.mock("@/lib/api/payments", () => ({
  printReceipt: vi.fn(),
}));

import { listChargedOrders, reprintOrder } from "@/lib/api/orders";
import { printReceipt } from "@/lib/api/payments";

const CHARGED_ORDER = {
  id: 10,
  table_number: 1,
  waiter_id: 1,
  waiter_username: "yefer",
  status: "CHARGED" as const,
  delivered: true,
  items: [
    {
      id: 1,
      order_id: 10,
      name: "Bandeja paisa",
      unit_price: "25000.00",
      quantity: 3,
      note: "sin cebolla\nuna sin chicharrón",
      line_type: "ORIGINAL" as const,
      is_voided: false,
      void_reason: null,
      line_total: "75000.00",
    },
    {
      id: 2,
      order_id: 10,
      name: "Jugo de mora",
      unit_price: "5000.00",
      quantity: 1,
      note: "",
      line_type: "ORIGINAL" as const,
      is_voided: true,
      void_reason: "se equivoco",
      line_total: "5000.00",
    },
  ],
  total: "75000.00",
  has_pending_print: false,
  active_payment: {
    account_name: "Efectivo",
    subtotal: "75000.00",
    discount: "0.00",
    discount_reason: "",
    amount: "75000.00",
    charged_by: "admin1",
    charged_at: "2026-10-11T15:26:09Z",
  },
  daily_number: 8,
  sent_at: "2026-10-11T15:23:09Z",
  created_at: "2026-03-10T18:55:00Z",
  draft_reminder: false,
};

describe("ChargedOrdersPanel (005, 004 RF-12)", () => {
  beforeEach(() => {
    vi.mocked(listChargedOrders).mockReset();
    vi.mocked(reprintOrder).mockReset();
    vi.mocked(listChargedOrders).mockResolvedValue([CHARGED_ORDER]);
  });

  it("loads today's charged orders with waiter, payment and active items", async () => {
    render(<ChargedOrdersPanel />);
    expect(await screen.findByText("N° 8")).toBeInTheDocument();
    expect(listChargedOrders).toHaveBeenCalledWith(expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/));
    expect(screen.getByText(/mesero: yefer/i)).toBeInTheDocument();
    expect(screen.getByText(/efectivo/i)).toBeInTheDocument();
    expect(screen.getByText("3x Bandeja paisa")).toBeInTheDocument();
    // T99, RF-4: a merged line keeps each note on its own line.
    expect(screen.getByText(/nota: sin cebolla/i).textContent).toBe(
      "Nota: sin cebolla\nuna sin chicharrón"
    );
    expect(screen.queryByText(/jugo de mora/i)).not.toBeInTheDocument();
  });

  it("shows each line's total and, with a discount, subtotal and reason (005 RF-10)", async () => {
    vi.mocked(listChargedOrders).mockResolvedValue([
      {
        ...CHARGED_ORDER,
        active_payment: {
          ...CHARGED_ORDER.active_payment,
          subtotal: "75000.00",
          discount: "5000.00",
          discount_reason: "cliente frecuente",
          amount: "70000.00",
        },
      },
    ]);
    render(<ChargedOrdersPanel />);
    expect(await screen.findByText("$75.000,00")).toBeInTheDocument();
    expect(screen.getByText(/subtotal \$75\.000,00/i)).toBeInTheDocument();
    expect(screen.getByText(/descuento −\$5\.000,00 \(cliente frecuente\)/i)).toBeInTheDocument();
    expect(screen.getByText(/total \$70\.000,00/i)).toBeInTheDocument();
  });

  it("prints the customer receipt (005 RF-11)", async () => {
    const user = userEvent.setup();
    vi.mocked(printReceipt).mockResolvedValue({ print_warning: null });
    render(<ChargedOrdersPanel />);
    await user.click(await screen.findByRole("button", { name: /imprimir comprobante/i }));
    expect(printReceipt).toHaveBeenCalledWith(10);
    expect(await screen.findByText(/comprobante de n° 8 impreso/i)).toBeInTheDocument();
  });

  it("reloads when another date is chosen", async () => {
    render(<ChargedOrdersPanel />);
    await screen.findByText("N° 8");
    vi.mocked(listChargedOrders).mockResolvedValue([]);

    fireEvent.change(screen.getByLabelText(/fecha/i), { target: { value: "2026-10-01" } });

    expect(await screen.findByText(/no hay pedidos cobrados/i)).toBeInTheDocument();
    expect(listChargedOrders).toHaveBeenLastCalledWith("2026-10-01");
  });

  it("reprints a charged order", async () => {
    const user = userEvent.setup();
    vi.mocked(reprintOrder).mockResolvedValue({ ...CHARGED_ORDER, print_warning: null });
    render(<ChargedOrdersPanel />);
    await user.click(await screen.findByRole("button", { name: /reimprimir/i }));
    expect(reprintOrder).toHaveBeenCalledWith(10);
    expect(await screen.findByText(/reimpreso en cocina/i)).toBeInTheDocument();
  });

  it("shows the printer warning when the reprint fails", async () => {
    const user = userEvent.setup();
    vi.mocked(reprintOrder).mockResolvedValue({
      ...CHARGED_ORDER,
      print_warning: "Impresora de cocina no detectada.",
    });
    render(<ChargedOrdersPanel />);
    await user.click(await screen.findByRole("button", { name: /reimprimir/i }));
    expect(await screen.findByText(/impresora de cocina no detectada/i)).toBeInTheDocument();
  });
});
