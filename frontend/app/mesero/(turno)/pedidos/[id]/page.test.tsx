import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "41" }),
}));

vi.mock("@/lib/api/orders", () => ({
  getOrder: vi.fn().mockResolvedValue({
    id: 41,
    table_number: 1,
    waiter_id: 1,
    waiter_username: "mesero1",
    status: "DRAFT",
    delivered: false,
    items: [],
    total: "0.00",
  }),
  addItem: vi.fn(),
  voidItem: vi.fn(),
  sendOrder: vi.fn(),
  fixTable: vi.fn(),
  listTables: vi.fn().mockResolvedValue([]),
  removeItem: vi.fn(),
  deleteOrder: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/lib/api/menu", () => ({
  getMenu: vi.fn().mockResolvedValue([]),
}));

import OrderPage from "./page";

describe("/mesero/pedidos/[id] page (T66)", () => {
  it("renders the order builder for the order in the route", async () => {
    render(<OrderPage />);
    expect(await screen.findByRole("heading", { name: /pedido 41/i })).toBeInTheDocument();
  });
});
