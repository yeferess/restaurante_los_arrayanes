import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/lib/api/orders", () => ({
  listIncomingOrders: vi.fn().mockResolvedValue([]),
  chargeOrder: vi.fn(),
  voidOrder: vi.fn(),
}));
vi.mock("@/lib/api/ordersSocket", () => ({
  subscribeToOrderUpdates: vi.fn().mockReturnValue({ close: vi.fn() }),
}));

import PedidosPage from "./page";

describe("/admin/pedidos page (T68)", () => {
  it("renders the incoming orders panel", () => {
    render(<PedidosPage />);
    expect(screen.getByRole("heading", { name: /pedidos entrantes/i })).toBeInTheDocument();
  });
});
