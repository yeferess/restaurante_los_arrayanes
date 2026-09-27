import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TableCountSettings } from "./TableCountSettings";

vi.mock("@/lib/api/orders", () => ({
  listTables: vi.fn(),
  resizeTables: vi.fn(),
}));

import { listTables, resizeTables } from "@/lib/api/orders";

describe("TableCountSettings (T64, RF-1)", () => {
  beforeEach(() => {
    vi.mocked(listTables).mockReset();
    vi.mocked(resizeTables).mockReset();
    vi.mocked(listTables).mockResolvedValue([
      { number: 1, status: "FREE" },
      { number: 2, status: "OCCUPIED" },
    ]);
  });

  it("loads and lists the current tables", async () => {
    render(<TableCountSettings />);
    expect(await screen.findByText(/mesa 1/i)).toBeInTheDocument();
    expect(screen.getByText(/mesa 2/i)).toBeInTheDocument();
  });

  it("resizes the table count", async () => {
    vi.mocked(resizeTables).mockResolvedValue([
      { number: 1, status: "FREE" },
      { number: 2, status: "OCCUPIED" },
      { number: 3, status: "FREE" },
    ]);
    const user = userEvent.setup();
    render(<TableCountSettings />);
    await screen.findByText(/mesa 1/i);

    const input = screen.getByLabelText(/número de mesas/i);
    await user.clear(input);
    await user.type(input, "3");
    await user.click(screen.getByRole("button", { name: /guardar/i }));

    await waitFor(() => expect(resizeTables).toHaveBeenCalledWith(3));
    expect(await screen.findByText(/mesa 3/i)).toBeInTheDocument();
  });

  it("shows the 409 error when a table to remove is not free", async () => {
    vi.mocked(resizeTables).mockRejectedValue({
      detail: "Alguna de las mesas a eliminar no está libre.",
    });
    const user = userEvent.setup();
    render(<TableCountSettings />);
    await screen.findByText(/mesa 1/i);

    const input = screen.getByLabelText(/número de mesas/i);
    await user.clear(input);
    await user.type(input, "1");
    await user.click(screen.getByRole("button", { name: /guardar/i }));

    expect(
      await screen.findByText("Alguna de las mesas a eliminar no está libre.")
    ).toBeInTheDocument();
  });
});
