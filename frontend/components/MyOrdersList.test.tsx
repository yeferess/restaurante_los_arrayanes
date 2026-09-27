import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MyOrdersList } from "./MyOrdersList";

vi.mock("@/lib/api/orders", () => ({
  listMyOrders: vi.fn(),
  setDelivered: vi.fn(),
  releaseTable: vi.fn(),
}));

import { listMyOrders, setDelivered, releaseTable } from "@/lib/api/orders";

const DRAFT_ORDER = {
  id: 41,
  table_number: 1,
  waiter_id: 1,
  status: "DRAFT" as const,
  delivered: false,
  items: [],
  total: "12.00",
};

const CHARGED_ORDER = {
  id: 42,
  table_number: 2,
  waiter_id: 1,
  status: "CHARGED" as const,
  delivered: true,
  items: [],
  total: "20.00",
};

describe("MyOrdersList (T67, RF-8/10)", () => {
  beforeEach(() => {
    vi.mocked(listMyOrders).mockReset();
    vi.mocked(setDelivered).mockReset();
    vi.mocked(releaseTable).mockReset();
    vi.mocked(listMyOrders).mockResolvedValue([DRAFT_ORDER, CHARGED_ORDER]);
  });

  it("lists the waiter's own orders with table and status", async () => {
    render(<MyOrdersList />);
    expect(await screen.findByText(/mesa 1/i)).toBeInTheDocument();
    expect(screen.getByText(/mesa 2/i)).toBeInTheDocument();
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
});
