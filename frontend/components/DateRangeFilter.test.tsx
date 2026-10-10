import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DateRangeFilter } from "./DateRangeFilter";

vi.mock("@/lib/api/stats", () => ({
  getRangeSummary: vi.fn(),
}));

import { getRangeSummary } from "@/lib/api/stats";

const SUMMARY = {
  from: "2026-03-01",
  to: "2026-03-10",
  money_total: "100000.00",
  orders_sent_count: 12,
  money_by_account: [{ account_name: "Efectivo", total: "60000.00" }],
  orders_by_waiter: [{ waiter_username: "cgarcia", orders_sent: 6 }],
  top_products: [{ product_name: "Limonada natural", quantity: 20 }],
};

describe("DateRangeFilter (T24, RF-5)", () => {
  beforeEach(() => {
    vi.mocked(getRangeSummary).mockReset();
  });

  it("does not fetch anything before the admin picks a range", () => {
    render(<DateRangeFilter />);
    expect(getRangeSummary).not.toHaveBeenCalled();
  });

  it("fetches and shows the range summary on submit", async () => {
    vi.mocked(getRangeSummary).mockResolvedValue(SUMMARY);
    const user = userEvent.setup();
    render(<DateRangeFilter />);

    await user.type(screen.getByLabelText(/desde/i), "2026-03-01");
    await user.type(screen.getByLabelText(/hasta/i), "2026-03-10");
    await user.click(screen.getByRole("button", { name: /consultar/i }));

    await waitFor(() =>
      expect(getRangeSummary).toHaveBeenCalledWith("2026-03-01", "2026-03-10")
    );
    expect(await screen.findByText("$100.000,00")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
  });

  it("shows the 400 error when 'desde' is after 'hasta'", async () => {
    vi.mocked(getRangeSummary).mockRejectedValue({
      detail: "from no puede ser posterior a to.",
    });
    const user = userEvent.setup();
    render(<DateRangeFilter />);

    await user.type(screen.getByLabelText(/desde/i), "2026-03-10");
    await user.type(screen.getByLabelText(/hasta/i), "2026-03-01");
    await user.click(screen.getByRole("button", { name: /consultar/i }));

    expect(
      await screen.findByText("from no puede ser posterior a to.")
    ).toBeInTheDocument();
  });
});
