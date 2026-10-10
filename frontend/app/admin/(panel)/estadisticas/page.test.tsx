import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/lib/api/stats", () => ({
  getDaySummary: vi.fn().mockResolvedValue({
    date: "2026-03-10",
    money_total: "0.00",
    orders_charged_count: 0,
    money_by_account: [],
    orders_by_waiter: [],
    top_products: [],
  }),
  getRangeSummary: vi.fn(),
  getDayMovement: vi.fn().mockResolvedValue({
    date: "2026-03-10",
    orders: [],
    payments: [],
  }),
}));

import EstadisticasPage from "./page";

describe("/admin/estadisticas page (T26, 006-estadisticas)", () => {
  it("renders the day summary, range filter and day movement sections", () => {
    render(<EstadisticasPage />);
    expect(
      screen.getByRole("heading", { name: /resumen del día/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /rango de fechas/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /movimiento del día/i })
    ).toBeInTheDocument();
  });
});
