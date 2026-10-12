import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OccupiedTablesPanel } from "./OccupiedTablesPanel";

vi.mock("@/lib/api/orders", () => ({
  listOccupiedTables: vi.fn(),
  voidOrder: vi.fn(),
  discardDraft: vi.fn(),
}));
vi.mock("@/lib/api/ordersSocket", () => ({
  subscribeToOrderUpdates: vi.fn(() => ({ close: vi.fn() })),
}));

import { listOccupiedTables, voidOrder, discardDraft } from "@/lib/api/orders";

const DRAFT_ORDER = {
  id: 15,
  table_number: 2,
  waiter_id: 1,
  waiter_username: "samuel",
  status: "DRAFT" as const,
  delivered: false,
  items: [
    {
      id: 1,
      order_id: 15,
      name: "Bandeja paisa",
      unit_price: "25000.00",
      quantity: 2,
      note: "",
      line_type: "ORIGINAL" as const,
      is_voided: false,
      void_reason: null,
      line_total: "50000.00",
    },
  ],
  total: "50000.00",
  has_pending_print: false,
  active_payment: null,
  daily_number: null,
  sent_at: null,
  created_at: "2026-10-11T17:36:05Z",
  draft_reminder: true,
};

const SENT_ORDER = {
  ...DRAFT_ORDER,
  id: 26,
  table_number: 9,
  status: "IN_PROGRESS" as const,
  daily_number: 11,
  sent_at: "2026-10-11T19:31:45Z",
  draft_reminder: false,
};

describe("OccupiedTablesPanel (RF-15)", () => {
  beforeEach(() => {
    vi.mocked(listOccupiedTables).mockReset();
    vi.mocked(voidOrder).mockReset();
    vi.mocked(discardDraft).mockReset();
    vi.mocked(listOccupiedTables).mockResolvedValue([
      { number: 2, order: DRAFT_ORDER, is_stale: true },
    ]);
  });

  it("shows each occupied table with its order, waiter and stale warning", async () => {
    render(<OccupiedTablesPanel />);
    expect(await screen.findByText("Mesa 2")).toBeInTheDocument();
    expect(screen.getByText("Borrador")).toBeInTheDocument();
    expect(screen.getByText(/mesero: samuel/i)).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(
      /hay 1 mesa ocupada desde hace más de 3 horas/i
    );
  });

  it("says so when no table is occupied", async () => {
    vi.mocked(listOccupiedTables).mockResolvedValue([]);
    render(<OccupiedTablesPanel />);
    expect(await screen.findByText(/no hay mesas ocupadas/i)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("discards a draft in one click after confirming, and refreshes", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.mocked(discardDraft).mockResolvedValue({ ...DRAFT_ORDER, status: "VOIDED" });
    render(<OccupiedTablesPanel />);
    await screen.findByText("Mesa 2");
    vi.mocked(listOccupiedTables).mockResolvedValue([]);

    await user.click(screen.getByRole("button", { name: /eliminar borrador/i }));

    expect(discardDraft).toHaveBeenCalledWith(15);
    expect(voidOrder).not.toHaveBeenCalled();
    expect(await screen.findByText(/no hay mesas ocupadas/i)).toBeInTheDocument();
  });

  it("does not discard the draft when the confirmation is cancelled", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<OccupiedTablesPanel />);
    await user.click(await screen.findByRole("button", { name: /eliminar borrador/i }));
    expect(discardDraft).not.toHaveBeenCalled();
  });

  it("voids a sent order with a reason and refreshes", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "prompt").mockReturnValue("se fueron sin pagar");
    vi.mocked(voidOrder).mockResolvedValue({ ...SENT_ORDER, status: "VOIDED" });
    vi.mocked(listOccupiedTables).mockResolvedValue([
      { number: 9, order: SENT_ORDER, is_stale: true },
    ]);
    render(<OccupiedTablesPanel />);
    await screen.findByText("Mesa 9");
    expect(screen.queryByRole("button", { name: /eliminar borrador/i })).not.toBeInTheDocument();
    vi.mocked(listOccupiedTables).mockResolvedValue([]);

    await user.click(screen.getByRole("button", { name: /anular pedido/i }));

    expect(voidOrder).toHaveBeenCalledWith(26, "se fueron sin pagar");
    expect(await screen.findByText(/no hay mesas ocupadas/i)).toBeInTheDocument();
  });

  it("does nothing when the reason prompt is cancelled", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "prompt").mockReturnValue(null);
    vi.mocked(listOccupiedTables).mockResolvedValue([
      { number: 9, order: SENT_ORDER, is_stale: false },
    ]);
    render(<OccupiedTablesPanel />);
    await user.click(await screen.findByRole("button", { name: /anular pedido/i }));
    expect(voidOrder).not.toHaveBeenCalled();
  });
});
