import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChargedOrdersPanel } from "./ChargedOrdersPanel";

vi.mock("@/lib/api/orders", () => ({
  listChargedOrders: vi.fn(),
  reprintOrder: vi.fn(),
}));

import { listChargedOrders, reprintOrder } from "@/lib/api/orders";

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
      note: "sin cebolla",
      line_type: "ORIGINAL" as const,
      is_voided: false,
      void_reason: null,
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
    },
  ],
  total: "75000.00",
  has_pending_print: false,
  active_payment: {
    account_name: "Efectivo",
    amount: "75000.00",
    charged_by: "admin1",
    charged_at: "2026-10-11T15:26:09Z",
  },
  daily_number: 8,
  sent_at: "2026-10-11T15:23:09Z",
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
    expect(screen.getByText(/nota: sin cebolla/i)).toBeInTheDocument();
    expect(screen.queryByText(/jugo de mora/i)).not.toBeInTheDocument();
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
