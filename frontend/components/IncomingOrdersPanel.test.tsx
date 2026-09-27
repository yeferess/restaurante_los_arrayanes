import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { IncomingOrdersPanel } from "./IncomingOrdersPanel";

vi.mock("@/lib/api/orders", () => ({
  listIncomingOrders: vi.fn(),
  chargeOrder: vi.fn(),
  voidOrder: vi.fn(),
}));
vi.mock("@/lib/api/ordersSocket", () => ({
  subscribeToOrderUpdates: vi.fn(),
}));

import { listIncomingOrders, chargeOrder, voidOrder } from "@/lib/api/orders";
import { subscribeToOrderUpdates } from "@/lib/api/ordersSocket";

const ORDER_1 = {
  id: 41,
  table_number: 1,
  waiter_id: 1,
  status: "IN_PROGRESS" as const,
  delivered: false,
  items: [],
  total: "12.00",
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
    vi.mocked(subscribeToOrderUpdates).mockReturnValue({ close: closeMock });
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

  it("charges an order", async () => {
    vi.mocked(chargeOrder).mockResolvedValue({ ...ORDER_1, status: "CHARGED" });
    const user = userEvent.setup();
    render(<IncomingOrdersPanel />);
    await screen.findByText(/mesa 1/i);

    await user.click(screen.getByRole("button", { name: /cobrar/i }));

    await waitFor(() => expect(chargeOrder).toHaveBeenCalledWith(41));
  });

  it("shows the 409 error when charging an order that isn't occupied", async () => {
    vi.mocked(chargeOrder).mockRejectedValue({ detail: "La mesa no está ocupada." });
    const user = userEvent.setup();
    render(<IncomingOrdersPanel />);
    await screen.findByText(/mesa 1/i);

    await user.click(screen.getByRole("button", { name: /cobrar/i }));

    expect(await screen.findByText("La mesa no está ocupada.")).toBeInTheDocument();
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
});
