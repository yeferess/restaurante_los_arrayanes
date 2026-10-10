import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DaySummaryPanel } from "./DaySummaryPanel";

vi.mock("@/lib/api/stats", () => ({
  getDaySummary: vi.fn(),
}));

import { getDaySummary } from "@/lib/api/stats";

const SUMMARY = {
  date: "2026-03-10",
  money_total: "20000.00",
  orders_charged_count: 3,
  money_by_account: [{ account_name: "Efectivo", total: "15000.00" }],
  orders_by_waiter: [{ waiter_username: "cgarcia", orders_sent: 4 }],
  top_products: [{ product_name: "Limonada natural", quantity: 10 }],
};

describe("DaySummaryPanel (T23, RF-1/2/3/4)", () => {
  beforeEach(() => {
    vi.mocked(getDaySummary).mockReset();
    vi.mocked(getDaySummary).mockResolvedValue(SUMMARY);
  });

  it("fetches today's summary by default", async () => {
    render(<DaySummaryPanel />);
    await screen.findByText("$20.000,00");
    expect(getDaySummary).toHaveBeenCalledWith(undefined);
  });

  it("shows the money total and the orders charged count", async () => {
    render(<DaySummaryPanel />);
    expect(await screen.findByText("$20.000,00")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("shows the breakdown sections", async () => {
    render(<DaySummaryPanel />);
    expect(await screen.findByText("Efectivo")).toBeInTheDocument();
    expect(screen.getByText("cgarcia")).toBeInTheDocument();
    expect(screen.getByText("Limonada natural")).toBeInTheDocument();
  });

  it("refetches when the date is changed", async () => {
    const user = userEvent.setup();
    render(<DaySummaryPanel />);
    await screen.findByText("$20.000,00");

    await user.clear(screen.getByLabelText(/fecha/i));
    await user.type(screen.getByLabelText(/fecha/i), "2026-03-01");

    await waitFor(() =>
      expect(getDaySummary).toHaveBeenCalledWith("2026-03-01")
    );
  });

  it("shows the error when the request fails", async () => {
    vi.mocked(getDaySummary).mockReset();
    vi.mocked(getDaySummary).mockRejectedValue({ detail: "No autorizado." });
    render(<DaySummaryPanel />);
    expect(await screen.findByText("No autorizado.")).toBeInTheDocument();
  });
});
