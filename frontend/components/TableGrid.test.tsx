import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TableGrid } from "./TableGrid";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("@/lib/api/orders", () => ({
  listTables: vi.fn(),
  createOrder: vi.fn(),
  releaseTable: vi.fn(),
}));

import { listTables, createOrder, releaseTable } from "@/lib/api/orders";

describe("TableGrid (T65, RF-1/2/13)", () => {
  beforeEach(() => {
    vi.mocked(listTables).mockReset();
    vi.mocked(createOrder).mockReset();
    vi.mocked(releaseTable).mockReset();
    pushMock.mockReset();
    vi.mocked(listTables).mockResolvedValue([
      { number: 1, status: "FREE", active_order_daily_number: null },
      { number: 2, status: "OCCUPIED", active_order_daily_number: 7 },
      { number: 3, status: "PAID", active_order_daily_number: 5 },
    ]);
  });

  it("shows the status of every table", async () => {
    render(<TableGrid />);
    expect(await screen.findByText(/mesa 1/i)).toBeInTheDocument();
    expect(screen.getByText(/mesa 2/i)).toBeInTheDocument();
    expect(screen.getByText(/mesa 3/i)).toBeInTheDocument();
  });

  it("only offers 'Crear pedido' on free tables", async () => {
    render(<TableGrid />);
    await screen.findByText(/mesa 1/i);
    const buttons = screen.getAllByRole("button", { name: /crear pedido/i });
    expect(buttons).toHaveLength(1);
  });

  it("creates an order on a free table", async () => {
    vi.mocked(createOrder).mockResolvedValue({
      id: 41,
      table_number: 1,
      waiter_id: 1,
      status: "DRAFT",
      delivered: false,
      items: [],
      total: "0.00",
    });
    const user = userEvent.setup();
    render(<TableGrid />);
    await screen.findByText(/mesa 1/i);

    await user.click(screen.getByRole("button", { name: /crear pedido/i }));

    await waitFor(() => expect(createOrder).toHaveBeenCalledWith(1));
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/mesero/pedidos/41"));
  });

  it("only offers 'Liberar mesa' on a paid table", async () => {
    render(<TableGrid />);
    await screen.findByText(/mesa 1/i);
    const buttons = screen.getAllByRole("button", { name: /liberar mesa/i });
    expect(buttons).toHaveLength(1);
  });

  it("releases a paid table and refreshes the grid", async () => {
    vi.mocked(releaseTable).mockResolvedValue({
      number: 3,
      status: "FREE",
      active_order_daily_number: null,
    });
    const user = userEvent.setup();
    render(<TableGrid />);
    await screen.findByText(/mesa 1/i);
    vi.mocked(listTables).mockResolvedValue([
      { number: 1, status: "FREE", active_order_daily_number: null },
      { number: 2, status: "OCCUPIED", active_order_daily_number: 7 },
      { number: 3, status: "FREE", active_order_daily_number: null },
    ]);

    await user.click(screen.getByRole("button", { name: /liberar mesa/i }));

    await waitFor(() => expect(releaseTable).toHaveBeenCalledWith(3));
  });

  it("shows the 409 error when the table is no longer free", async () => {
    vi.mocked(createOrder).mockRejectedValue({
      detail: "La mesa no está libre.",
    });
    const user = userEvent.setup();
    render(<TableGrid />);
    await screen.findByText(/mesa 1/i);

    await user.click(screen.getByRole("button", { name: /crear pedido/i }));

    expect(await screen.findByText("La mesa no está libre.")).toBeInTheDocument();
  });

  it("shows the daily number next to an occupied or paid table (T79, RF-14)", async () => {
    render(<TableGrid />);
    expect(await screen.findByText(/mesa 2/i)).toBeInTheDocument();
    expect(screen.getByText("N° 7")).toBeInTheDocument();
    expect(screen.getByText("N° 5")).toBeInTheDocument();
  });

  it("shows no daily number on a free table, or when it is still null", async () => {
    vi.mocked(listTables).mockResolvedValue([
      { number: 1, status: "FREE", active_order_daily_number: null },
      { number: 2, status: "OCCUPIED", active_order_daily_number: null },
    ]);
    render(<TableGrid />);
    await screen.findByText(/mesa 1/i);
    expect(screen.queryByText(/^N° /)).not.toBeInTheDocument();
  });
});
