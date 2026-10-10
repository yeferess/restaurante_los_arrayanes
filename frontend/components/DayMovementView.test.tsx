import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DayMovementView } from "./DayMovementView";

vi.mock("@/lib/api/stats", () => ({
  getDayMovement: vi.fn(),
}));

import { getDayMovement } from "@/lib/api/stats";

const MOVEMENT = {
  date: "2026-03-10",
  orders: [
    {
      daily_number: 7,
      waiter: "cgarcia",
      status: "CHARGED",
      total: "32000.00",
    },
  ],
  payments: [
    {
      account_name: "Efectivo",
      amount: "32000.00",
      charged_by: "admin1",
      charged_at: "2026-03-10T20:15:00Z",
      status: "ACTIVE",
    },
  ],
};

describe("DayMovementView (T25, RF-6)", () => {
  beforeEach(() => {
    vi.mocked(getDayMovement).mockReset();
    vi.mocked(getDayMovement).mockResolvedValue(MOVEMENT);
  });

  it("fetches today's movement by default", async () => {
    render(<DayMovementView />);
    await screen.findByText("N° 7");
    expect(getDayMovement).toHaveBeenCalledWith(undefined);
  });

  it("lists the orders sent that day, identified by daily number", async () => {
    render(<DayMovementView />);
    expect(await screen.findByText("N° 7")).toBeInTheDocument();
    expect(screen.getByText("cgarcia")).toBeInTheDocument();
    expect(screen.getByText("Cobrado")).toBeInTheDocument();
  });

  it("lists the payments registered that day", async () => {
    render(<DayMovementView />);
    expect(await screen.findByText("Efectivo")).toBeInTheDocument();
    expect(screen.getByText("admin1")).toBeInTheDocument();
    expect(screen.getByText("Activo")).toBeInTheDocument();
  });

  it("shows a voided payment's status too, for traceability", async () => {
    vi.mocked(getDayMovement).mockResolvedValue({
      ...MOVEMENT,
      payments: [{ ...MOVEMENT.payments[0], status: "VOIDED" }],
    });
    render(<DayMovementView />);
    expect(await screen.findByText("Anulado")).toBeInTheDocument();
  });

  it("refetches when the date is changed", async () => {
    const user = userEvent.setup();
    render(<DayMovementView />);
    await screen.findByText("N° 7");

    await user.clear(screen.getByLabelText(/fecha/i));
    await user.type(screen.getByLabelText(/fecha/i), "2026-03-01");

    await waitFor(() =>
      expect(getDayMovement).toHaveBeenCalledWith("2026-03-01")
    );
  });

  it("shows empty messages for a day with no movement", async () => {
    vi.mocked(getDayMovement).mockResolvedValue({
      date: "2026-03-10",
      orders: [],
      payments: [],
    });
    render(<DayMovementView />);
    expect((await screen.findAllByText(/sin movimiento/i)).length).toBeGreaterThan(0);
  });
});
