import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/lib/api/orders", () => ({
  listMyOrders: vi.fn().mockResolvedValue([]),
  listTables: vi.fn().mockResolvedValue([]),
  setDelivered: vi.fn(),
  releaseTable: vi.fn(),
}));

import MyOrdersPage from "./page";

describe("/mesero/pedidos page (T67)", () => {
  it("renders the own-orders screen", () => {
    render(<MyOrdersPage />);
    expect(screen.getByRole("heading", { name: /mis pedidos/i })).toBeInTheDocument();
  });
});
