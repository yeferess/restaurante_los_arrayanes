import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MyOrdersList } from "./MyOrdersList";

vi.mock("@/lib/api/orders", () => ({
  listMyOrders: vi.fn(),
  listTables: vi.fn(),
  setDelivered: vi.fn(),
  releaseTable: vi.fn(),
  retryPrint: vi.fn(),
  reprintOrder: vi.fn(),
  deleteOrder: vi.fn(),
}));

import {
  listMyOrders,
  listTables,
  setDelivered,
  releaseTable,
  retryPrint,
  reprintOrder,
  deleteOrder,
} from "@/lib/api/orders";

const DRAFT_ORDER = {
  id: 41,
  table_number: 1,
  waiter_id: 1,
  waiter_username: "mesero1",
  status: "DRAFT" as const,
  delivered: false,
  items: [],
  total: "12.00",
  has_pending_print: false,
  active_payment: null,
  daily_number: null,
  sent_at: null,
};

const CHARGED_ORDER = {
  id: 42,
  table_number: 2,
  waiter_id: 1,
  waiter_username: "mesero1",
  status: "CHARGED" as const,
  delivered: true,
  items: [],
  total: "20.00",
  has_pending_print: false,
  active_payment: null,
  daily_number: 5,
  sent_at: "2026-03-10T20:15:00Z",
};

const UNPRINTED_ORDER = {
  id: 43,
  table_number: 3,
  waiter_id: 1,
  waiter_username: "mesero1",
  status: "IN_PROGRESS" as const,
  delivered: false,
  items: [],
  total: "15.00",
  has_pending_print: true,
  active_payment: null,
  daily_number: 12,
  sent_at: "2026-03-10T21:00:00Z",
};

const DELIVERED_ORDER = {
  id: 44,
  table_number: 1,
  waiter_id: 1,
  waiter_username: "mesero1",
  status: "IN_PROGRESS" as const,
  delivered: true,
  items: [],
  total: "18.00",
  has_pending_print: false,
  active_payment: null,
  daily_number: 13,
  sent_at: "2026-03-10T21:10:00Z",
};

const VOIDED_DELIVERED_ORDER = {
  id: 45,
  table_number: 1,
  waiter_id: 1,
  waiter_username: "mesero1",
  status: "VOIDED" as const,
  delivered: true,
  items: [],
  total: "18.00",
  has_pending_print: false,
  active_payment: null,
  daily_number: 14,
  sent_at: "2026-03-10T21:20:00Z",
};

describe("MyOrdersList (T67, RF-8/10)", () => {
  beforeEach(() => {
    vi.mocked(listMyOrders).mockReset();
    vi.mocked(setDelivered).mockReset();
    vi.mocked(releaseTable).mockReset();
    vi.mocked(retryPrint).mockReset();
    vi.mocked(deleteOrder).mockReset();
    vi.mocked(listTables).mockReset();
    vi.mocked(listMyOrders).mockResolvedValue([DRAFT_ORDER, CHARGED_ORDER]);
    vi.mocked(listTables).mockResolvedValue([
      { number: 1, status: "OCCUPIED", active_order_daily_number: null },
      { number: 2, status: "PAID", active_order_daily_number: null },
      { number: 3, status: "OCCUPIED", active_order_daily_number: null },
    ]);
  });

  it("lists the waiter's own orders with table and status", async () => {
    render(<MyOrdersList />);
    expect(await screen.findByText(/mesa 1/i)).toBeInTheDocument();
    expect(screen.getByText(/mesa 2/i)).toBeInTheDocument();
  });

  it("links each order to its detail/builder screen", async () => {
    render(<MyOrdersList />);
    await screen.findByText(/mesa 1/i);
    expect(screen.getByRole("link", { name: /borrador/i })).toHaveAttribute(
      "href",
      "/mesero/pedidos/41"
    );
  });

  it("shows the daily number with its sent-at timestamp instead of the internal id (T80, RF-14)", async () => {
    render(<MyOrdersList />);
    await screen.findByText(/mesa 2/i);
    expect(screen.getByRole("link", { name: "N° 5" })).toHaveAttribute(
      "href",
      "/mesero/pedidos/42"
    );
    expect(screen.getByText(/\d{2}\/\d{2} \d{2}:\d{2}/)).toBeInTheDocument();
    expect(screen.queryByText(/pedido 42/i)).not.toBeInTheDocument();
  });

  it("shows 'Borrador' for an order that was never sent, with no daily number", async () => {
    render(<MyOrdersList />);
    await screen.findByText(/mesa 1/i);
    expect(screen.getByRole("link", { name: "Borrador" })).toBeInTheDocument();
  });

  it("toggles the delivered flag", async () => {
    vi.mocked(setDelivered).mockResolvedValue({ ...DRAFT_ORDER, delivered: true });
    const user = userEvent.setup();
    render(<MyOrdersList />);
    await screen.findByText(/mesa 1/i);

    await user.click(screen.getAllByRole("button", { name: /entregado/i })[0]);

    await waitFor(() => expect(setDelivered).toHaveBeenCalledWith(41, true));
  });

  it("only offers 'Liberar mesa' on a charged order's paid table", async () => {
    render(<MyOrdersList />);
    await screen.findByText(/mesa 1/i);
    const buttons = screen.getAllByRole("button", { name: /liberar mesa/i });
    expect(buttons).toHaveLength(1);
  });

  it("releases a paid table and the button disappears after refreshing", async () => {
    vi.mocked(releaseTable).mockResolvedValue({ number: 2, status: "FREE", active_order_daily_number: null });
    const user = userEvent.setup();
    render(<MyOrdersList />);
    await screen.findByText(/mesa 1/i);
    vi.mocked(listTables).mockResolvedValue([
      { number: 1, status: "OCCUPIED", active_order_daily_number: null },
      { number: 2, status: "FREE", active_order_daily_number: null },
      { number: 3, status: "OCCUPIED", active_order_daily_number: null },
    ]);

    await user.click(screen.getByRole("button", { name: /liberar mesa/i }));

    await waitFor(() => expect(releaseTable).toHaveBeenCalledWith(2));
    await waitFor(() =>
      expect(
        screen.queryByRole("button", { name: /liberar mesa/i })
      ).not.toBeInTheDocument()
    );
  });

  it("hides 'Liberar mesa' once the table was already freed", async () => {
    vi.mocked(listTables).mockResolvedValue([
      { number: 1, status: "OCCUPIED", active_order_daily_number: null },
      { number: 2, status: "FREE", active_order_daily_number: null },
      { number: 3, status: "OCCUPIED", active_order_daily_number: null },
    ]);
    render(<MyOrdersList />);
    await screen.findByText(/mesa 1/i);
    expect(
      screen.queryByRole("button", { name: /liberar mesa/i })
    ).not.toBeInTheDocument();
  });

  it("only offers 'Eliminar' on a draft order", async () => {
    render(<MyOrdersList />);
    await screen.findByText(/mesa 1/i);
    const buttons = screen.getAllByRole("button", { name: /^eliminar$/i });
    expect(buttons).toHaveLength(1);
  });

  it("deletes a draft order and refreshes the list", async () => {
    vi.mocked(deleteOrder).mockResolvedValue(undefined);
    vi.mocked(listMyOrders).mockResolvedValueOnce([DRAFT_ORDER, CHARGED_ORDER]);
    const user = userEvent.setup();
    render(<MyOrdersList />);
    await screen.findByText(/mesa 1/i);
    vi.mocked(listMyOrders).mockResolvedValue([CHARGED_ORDER]);

    await user.click(screen.getByRole("button", { name: /^eliminar$/i }));

    await waitFor(() => expect(deleteOrder).toHaveBeenCalledWith(41));
    await waitFor(() => expect(screen.queryByText(/mesa 1/i)).not.toBeInTheDocument());
  });

  it("shows the error when deleting a draft fails", async () => {
    vi.mocked(deleteOrder).mockRejectedValue({
      detail: "Solo se puede eliminar un pedido en borrador.",
    });
    const user = userEvent.setup();
    render(<MyOrdersList />);
    await screen.findByText(/mesa 1/i);

    await user.click(screen.getByRole("button", { name: /^eliminar$/i }));

    expect(
      await screen.findByText("Solo se puede eliminar un pedido en borrador.")
    ).toBeInTheDocument();
  });

  it("shows the error when releasing an already-free table", async () => {
    vi.mocked(releaseTable).mockRejectedValue({ detail: "La mesa no está pagada." });
    const user = userEvent.setup();
    render(<MyOrdersList />);
    await screen.findByText(/mesa 1/i);

    await user.click(screen.getByRole("button", { name: /liberar mesa/i }));

    expect(await screen.findByText("La mesa no está pagada.")).toBeInTheDocument();
  });

  it("shows a 'not printed' badge and retry button when has_pending_print is true (T33, RF-9/10)", async () => {
    vi.mocked(listMyOrders).mockResolvedValue([UNPRINTED_ORDER]);
    render(<MyOrdersList />);
    expect(await screen.findByText(/no impreso en cocina/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /reintentar impresión/i })
    ).toBeInTheDocument();
  });

  it("shows neither the badge nor the retry button when has_pending_print is false", async () => {
    render(<MyOrdersList />);
    await screen.findByText(/mesa 1/i);
    expect(screen.queryByText(/no impreso en cocina/i)).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /reintentar impresión/i })
    ).not.toBeInTheDocument();
  });

  it("hides the retry button once the order is charged, even with a pending ticket", async () => {
    vi.mocked(listMyOrders).mockResolvedValue([
      { ...CHARGED_ORDER, has_pending_print: true },
    ]);
    render(<MyOrdersList />);
    await screen.findByText(/mesa 2/i);
    expect(
      screen.queryByRole("button", { name: /reintentar impresión/i })
    ).not.toBeInTheDocument();
  });

  it("retries printing and refreshes the indicator", async () => {
    vi.mocked(listMyOrders).mockResolvedValue([UNPRINTED_ORDER]);
    vi.mocked(retryPrint).mockResolvedValue({
      ...UNPRINTED_ORDER,
      has_pending_print: false,
      print_warning: null,
    });
    const user = userEvent.setup();
    render(<MyOrdersList />);
    await screen.findByText(/no impreso en cocina/i);

    await user.click(screen.getByRole("button", { name: /reintentar impresión/i }));

    await waitFor(() => expect(retryPrint).toHaveBeenCalledWith(43));
    await waitFor(() =>
      expect(screen.queryByText(/no impreso en cocina/i)).not.toBeInTheDocument()
    );
  });

  it("shows the error when a retry fails again", async () => {
    vi.mocked(listMyOrders).mockResolvedValue([UNPRINTED_ORDER]);
    vi.mocked(retryPrint).mockRejectedValue({
      detail: "Impresora de cocina no detectada.",
    });
    const user = userEvent.setup();
    render(<MyOrdersList />);
    await screen.findByText(/no impreso en cocina/i);

    await user.click(screen.getByRole("button", { name: /reintentar impresión/i }));

    expect(
      await screen.findByText("Impresora de cocina no detectada.")
    ).toBeInTheDocument();
  });

  it("shows the total with a thousands separator", async () => {
    vi.mocked(listMyOrders).mockResolvedValue([
      { ...DRAFT_ORDER, total: "20000.00" },
    ]);
    render(<MyOrdersList />);
    expect(await screen.findByText("$20.000,00")).toBeInTheDocument();
  });

  it("shows 'Entregado' instead of 'En preparación' once delivered is marked (T81, RF-8)", async () => {
    vi.mocked(listMyOrders).mockResolvedValue([DELIVERED_ORDER]);
    render(<MyOrdersList />);
    expect(await screen.findByText("Entregado")).toBeInTheDocument();
    expect(screen.queryByText("En preparación")).not.toBeInTheDocument();
  });

  it("still shows 'En preparación' while not yet delivered (T81, RF-8)", async () => {
    vi.mocked(listMyOrders).mockResolvedValue([UNPRINTED_ORDER]);
    render(<MyOrdersList />);
    expect(await screen.findByText("En preparación")).toBeInTheDocument();
    expect(screen.queryByText("Entregado")).not.toBeInTheDocument();
  });

  it("still shows 'Cobrado' for a charged order, even if delivered (T81, RF-8)", async () => {
    render(<MyOrdersList />);
    expect(await screen.findByText("Cobrado")).toBeInTheDocument();
    expect(screen.queryByText("Entregado")).not.toBeInTheDocument();
  });

  it("still shows 'Anulado' for a voided order, even if delivered (T81, RF-8)", async () => {
    vi.mocked(listMyOrders).mockResolvedValue([VOIDED_DELIVERED_ORDER]);
    render(<MyOrdersList />);
    expect(await screen.findByText("Anulado")).toBeInTheDocument();
    expect(screen.queryByText("Entregado")).not.toBeInTheDocument();
  });

  it("offers 'Reimprimir pedido' only on an order in preparation (RF-12)", async () => {
    vi.mocked(listMyOrders).mockResolvedValue([DRAFT_ORDER, UNPRINTED_ORDER, CHARGED_ORDER]);
    render(<MyOrdersList />);
    await screen.findAllByText(/mesa/i);
    expect(screen.getAllByRole("button", { name: /reimprimir pedido/i })).toHaveLength(1);
  });

  it("reprints the order and confirms it", async () => {
    const user = userEvent.setup();
    vi.mocked(listMyOrders).mockResolvedValue([UNPRINTED_ORDER]);
    vi.mocked(reprintOrder).mockResolvedValue({ ...UNPRINTED_ORDER, print_warning: null });
    render(<MyOrdersList />);
    await user.click(await screen.findByRole("button", { name: /reimprimir pedido/i }));
    expect(reprintOrder).toHaveBeenCalledWith(UNPRINTED_ORDER.id);
    expect(await screen.findByText(/reimpreso en cocina/i)).toBeInTheDocument();
  });

  it("shows the printer warning when the reprint fails", async () => {
    const user = userEvent.setup();
    vi.mocked(listMyOrders).mockResolvedValue([UNPRINTED_ORDER]);
    vi.mocked(reprintOrder).mockResolvedValue({
      ...UNPRINTED_ORDER,
      print_warning: "Impresora de cocina no detectada.",
    });
    render(<MyOrdersList />);
    await user.click(await screen.findByRole("button", { name: /reimprimir pedido/i }));
    expect(await screen.findByText(/impresora de cocina no detectada/i)).toBeInTheDocument();
  });
});
