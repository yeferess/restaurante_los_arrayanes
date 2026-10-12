import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { IncomingOrdersPanel } from "./IncomingOrdersPanel";

vi.mock("@/lib/api/orders", () => ({
  listIncomingOrders: vi.fn(),
  chargeOrder: vi.fn(),
  voidOrder: vi.fn(),
  reprintOrder: vi.fn(),
  listOccupiedTables: vi.fn(),
}));
vi.mock("@/lib/api/ordersSocket", () => ({
  subscribeToOrderUpdates: vi.fn(),
}));
vi.mock("./ChargeOrderModal", () => ({
  ChargeOrderModal: ({ order, onClose, onCharged }: any) => (
    <div data-testid="charge-modal">
      <span>Modal para pedido {order.id}</span>
      <button onClick={onClose}>cerrar-modal</button>
      <button onClick={() => onCharged({ ...order, status: "CHARGED" })}>
        simular-cobro-exitoso
      </button>
    </div>
  ),
}));

import {
  listIncomingOrders,
  listOccupiedTables,
  chargeOrder,
  voidOrder,
  reprintOrder,
} from "@/lib/api/orders";
import { subscribeToOrderUpdates } from "@/lib/api/ordersSocket";

const ORDER_1 = {
  id: 41,
  table_number: 1,
  waiter_id: 1,
  waiter_username: "mesero1",
  status: "IN_PROGRESS" as const,
  delivered: false,
  items: [],
  total: "12.00",
  has_pending_print: false,
  active_payment: null,
  daily_number: 9,
  sent_at: "2026-03-10T19:00:00Z",
  created_at: "2026-03-10T18:55:00Z",
  draft_reminder: false,
};

describe("IncomingOrdersPanel (T68, soporte RF-9/11)", () => {
  const closeMock = vi.fn();

  beforeEach(() => {
    vi.mocked(listIncomingOrders).mockReset();
    vi.mocked(chargeOrder).mockReset();
    vi.mocked(voidOrder).mockReset();
    vi.mocked(subscribeToOrderUpdates).mockReset();
    closeMock.mockReset();
    vi.mocked(listIncomingOrders).mockResolvedValue([ORDER_1]);
    vi.mocked(listOccupiedTables).mockReset();
    vi.mocked(listOccupiedTables).mockResolvedValue([]);
    vi.mocked(subscribeToOrderUpdates).mockReturnValue({ close: closeMock });
  });

  it("warns about tables occupied for too long (RF-15)", async () => {
    vi.mocked(listOccupiedTables).mockResolvedValue([
      { number: 1, order: ORDER_1, is_stale: true },
      { number: 2, order: null, is_stale: false },
    ]);
    render(<IncomingOrdersPanel />);
    expect(
      await screen.findByText(/hay 1 mesa ocupada desde hace más de 3 horas/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /revisar en mesas/i })).toHaveAttribute(
      "href",
      "/admin/mesas"
    );
  });

  it("shows no stale-table warning when every occupation is recent", async () => {
    vi.mocked(listOccupiedTables).mockResolvedValue([
      { number: 1, order: ORDER_1, is_stale: false },
    ]);
    render(<IncomingOrdersPanel />);
    await screen.findByText(/mesa 1/i);
    expect(screen.queryByText(/más de 3 horas/i)).not.toBeInTheDocument();
  });

  it("shows the waiter who sent each order", async () => {
    render(<IncomingOrdersPanel />);
    expect(await screen.findByText("Mesero: mesero1")).toBeInTheDocument();
  });

  it("loads and displays incoming orders on mount", async () => {
    render(<IncomingOrdersPanel />);
    expect(await screen.findByText(/mesa 1/i)).toBeInTheDocument();
    expect(listIncomingOrders).toHaveBeenCalledTimes(1);
  });

  it("refetches when the socket notifies a change", async () => {
    render(<IncomingOrdersPanel />);
    await screen.findByText(/mesa 1/i);

    const onOrdersChanged = vi.mocked(subscribeToOrderUpdates).mock.calls[0][0];
    vi.mocked(listIncomingOrders).mockResolvedValue([
      { ...ORDER_1, id: 55, table_number: 3 },
    ]);
    onOrdersChanged();

    expect(await screen.findByText(/mesa 3/i)).toBeInTheDocument();
  });

  it("the manual 'Actualizar' button triggers the same refetch", async () => {
    const user = userEvent.setup();
    render(<IncomingOrdersPanel />);
    await screen.findByText(/mesa 1/i);

    await user.click(screen.getByRole("button", { name: /actualizar/i }));
    await waitFor(() => expect(listIncomingOrders).toHaveBeenCalledTimes(2));
  });

  it("closes the socket subscription on unmount", async () => {
    const { unmount } = render(<IncomingOrdersPanel />);
    await screen.findByText(/mesa 1/i);
    unmount();
    expect(closeMock).toHaveBeenCalledTimes(1);
  });

  it("opens the charge modal for the clicked order (T28, RF-1)", async () => {
    const user = userEvent.setup();
    render(<IncomingOrdersPanel />);
    await screen.findByText(/mesa 1/i);

    await user.click(screen.getByRole("button", { name: /^cobrar$/i }));

    expect(await screen.findByTestId("charge-modal")).toBeInTheDocument();
    expect(screen.getByText(/modal para pedido 41/i)).toBeInTheDocument();
  });

  it("closes the charge modal without refetching on cancel", async () => {
    const user = userEvent.setup();
    render(<IncomingOrdersPanel />);
    await screen.findByText(/mesa 1/i);
    await user.click(screen.getByRole("button", { name: /^cobrar$/i }));
    await screen.findByTestId("charge-modal");
    vi.mocked(listIncomingOrders).mockClear();

    await user.click(screen.getByText("cerrar-modal"));

    expect(screen.queryByTestId("charge-modal")).not.toBeInTheDocument();
    expect(listIncomingOrders).not.toHaveBeenCalled();
  });

  it("refetches and closes the modal after a successful charge", async () => {
    const user = userEvent.setup();
    render(<IncomingOrdersPanel />);
    await screen.findByText(/mesa 1/i);
    await user.click(screen.getByRole("button", { name: /^cobrar$/i }));
    await screen.findByTestId("charge-modal");
    vi.mocked(listIncomingOrders).mockClear();
    vi.mocked(listIncomingOrders).mockResolvedValue([]);

    await user.click(screen.getByText("simular-cobro-exitoso"));

    await waitFor(() => expect(listIncomingOrders).toHaveBeenCalledTimes(1));
    expect(screen.queryByTestId("charge-modal")).not.toBeInTheDocument();
  });

  it("voids a full order with a reason", async () => {
    vi.mocked(voidOrder).mockResolvedValue({ ...ORDER_1, status: "VOIDED" });
    vi.spyOn(window, "prompt").mockReturnValue("Cliente se retiró sin pagar");
    const user = userEvent.setup();
    render(<IncomingOrdersPanel />);
    await screen.findByText(/mesa 1/i);

    await user.click(screen.getByRole("button", { name: /anular pedido/i }));

    await waitFor(() =>
      expect(voidOrder).toHaveBeenCalledWith(41, "Cliente se retiró sin pagar")
    );
  });

  it("does not call voidOrder when the reason prompt is cancelled", async () => {
    vi.spyOn(window, "prompt").mockReturnValue(null);
    const user = userEvent.setup();
    render(<IncomingOrdersPanel />);
    await screen.findByText(/mesa 1/i);

    await user.click(screen.getByRole("button", { name: /anular pedido/i }));

    expect(voidOrder).not.toHaveBeenCalled();
  });

  it("shows a read-only 'not printed' badge when has_pending_print is true (T34, RF-10)", async () => {
    vi.mocked(listIncomingOrders).mockResolvedValue([
      { ...ORDER_1, has_pending_print: true },
    ]);
    render(<IncomingOrdersPanel />);
    expect(await screen.findByText(/no impreso en cocina/i)).toBeInTheDocument();
  });

  it("shows no badge and no retry control when has_pending_print is false", async () => {
    render(<IncomingOrdersPanel />);
    await screen.findByText(/mesa 1/i);
    expect(screen.queryByText(/no impreso en cocina/i)).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /reintentar/i })
    ).not.toBeInTheDocument();
  });

  it("shows the total with a thousands separator", async () => {
    vi.mocked(listIncomingOrders).mockResolvedValue([
      { ...ORDER_1, total: "20000.00" },
    ]);
    render(<IncomingOrdersPanel />);
    expect(await screen.findByText("$20.000,00")).toBeInTheDocument();
  });

  it("shows the daily number with its sent-at timestamp instead of the internal id (T80, RF-14)", async () => {
    render(<IncomingOrdersPanel />);
    await screen.findByText(/mesa 1/i);
    expect(screen.getByText("N° 9")).toBeInTheDocument();
    expect(screen.getByText(/\d{2}\/\d{2} \d{2}:\d{2}/)).toBeInTheDocument();
    expect(screen.queryByText(/^pedido 41$/i)).not.toBeInTheDocument();
  });

  it("lets the admin reprint an incoming order (RF-12)", async () => {
    const user = userEvent.setup();
    vi.mocked(reprintOrder).mockResolvedValue({ ...ORDER_1, print_warning: null });
    render(<IncomingOrdersPanel />);
    await user.click(await screen.findByRole("button", { name: /^reimprimir$/i }));
    expect(reprintOrder).toHaveBeenCalledWith(ORDER_1.id);
    expect(await screen.findByText(/reimpreso en cocina/i)).toBeInTheDocument();
  });
});
