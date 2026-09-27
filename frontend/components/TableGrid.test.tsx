import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TableGrid } from "./TableGrid";

vi.mock("@/lib/api/orders", () => ({
  listTables: vi.fn(),
  createOrder: vi.fn(),
}));

import { listTables, createOrder } from "@/lib/api/orders";

describe("TableGrid (T65, RF-1/2/13)", () => {
  beforeEach(() => {
    vi.mocked(listTables).mockReset();
    vi.mocked(createOrder).mockReset();
    vi.mocked(listTables).mockResolvedValue([
      { number: 1, status: "FREE" },
      { number: 2, status: "OCCUPIED" },
      { number: 3, status: "PAID" },
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
    expect(await screen.findByText(/pedido 41 creado/i)).toBeInTheDocument();
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
});
