import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatsSummaryBreakdown } from "./StatsSummaryBreakdown";

describe("StatsSummaryBreakdown (006-estadisticas, RF-2/3/4)", () => {
  it("shows the money-by-account breakdown", () => {
    render(
      <StatsSummaryBreakdown
        moneyByAccount={[{ account_name: "Efectivo", total: "20000.00" }]}
        ordersByWaiter={[]}
        topProducts={[]}
      />
    );
    expect(screen.getByText("Efectivo")).toBeInTheDocument();
    expect(screen.getByText("$20.000,00")).toBeInTheDocument();
  });

  it("shows the orders-by-waiter breakdown", () => {
    render(
      <StatsSummaryBreakdown
        moneyByAccount={[]}
        ordersByWaiter={[{ waiter_username: "cgarcia", orders_sent: 5 }]}
        topProducts={[]}
      />
    );
    expect(screen.getByText("cgarcia")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("shows the top-products ranking", () => {
    render(
      <StatsSummaryBreakdown
        moneyByAccount={[]}
        ordersByWaiter={[]}
        topProducts={[{ product_name: "Limonada natural", quantity: 42 }]}
      />
    );
    expect(screen.getByText("Limonada natural")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("shows an empty message when there is nothing to show", () => {
    render(
      <StatsSummaryBreakdown moneyByAccount={[]} ordersByWaiter={[]} topProducts={[]} />
    );
    expect(screen.getAllByText(/sin datos/i).length).toBeGreaterThan(0);
  });
});
