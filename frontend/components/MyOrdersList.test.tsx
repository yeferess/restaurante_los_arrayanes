import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MyOrdersList } from "./MyOrdersList";

vi.mock("@/lib/api/orders", () => ({
  listMyOrders: vi.fn(),
  setDelivered: vi.fn(),
  releaseTable: vi.fn(),
  retryPrint: vi.fn(),
}));

import {
  listMyOrders,
  setDelivered,
  releaseTable,
  retryPrint,
} from "@/lib/api/orders";

const DRAFT_ORDER = {
  id: 41,
  table_number: 1,
  waiter_id: 1,
  status: "DRAFT" as const,
  delivered: false,
  items: [],
  total: "12.00",
  has_pending_print: false,
};

const CHARGED_ORDER = {
  id: 42,
  table_number: 2,
  waiter_id: 1,
  status: "CHARGED" as const,
  delivered: true,
  items: [],
  total: "20.00",
  has_pending_print: false,
};

const UNPRINTED_ORDER = {
  id: 43,
  table_number: 3,
  waiter_id: 1,
  status: "IN_PROGRESS" as const,
  delivered: false,
  items: [],
  total: "15.00",
  has_pending_print: true,
};

describe("MyOrdersList (T67, RF-8/10)", () => {
  beforeEach(() => {
    vi.mocked(listMyOrders).mockReset();
    vi.mocked(setDelivered).mockReset();
    vi.mocked(releaseTable).mockReset();
    vi.mocked(retryPrint).mockReset();
    vi.mocked(listMyOrders).mockResolvedValue([DRAFT_ORDER, CHARGED_ORDER]);
  });

  it("lists the waiter's own orders with table and status", async () => {
    render(<MyOrdersList />);
    expect(await screen.findByText(/mesa 1/i)).toBeInTheDocument();
    expect(screen.getByText(/mesa 2/i)).toBeInTheDocument();
  });

  it("links each order to its detail/builder screen", async () => {
    render(<MyOrdersList />);
    await screen.findByText(/mesa 1/i);
    expect(screen.getByRole("link", { name: /pedido 41/i })).toHaveAttribute(
      "href",
      "/mesero/pedidos/41"
    );
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

  it("releases a paid table", async () => {
    vi.mocked(releaseTable).mockResolvedValue({ number: 2, status: "FREE" });
    const user = userEvent.setup();
    render(<MyOrdersList />);
    await screen.findByText(/mesa 1/i);

    await user.click(screen.getByRole("button", { name: /liberar mesa/i }));

    await waitFor(() => expect(releaseTable).toHaveBeenCalledWith(2));
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
});
