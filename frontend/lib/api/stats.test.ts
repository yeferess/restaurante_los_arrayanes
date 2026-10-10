import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { getDaySummary, getRangeSummary, getDayMovement } from "./stats";

describe("lib/api/stats (006-estadisticas)", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  function mockOk(body: unknown, status = 200) {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(JSON.stringify(body), { status })
    );
  }

  function mockError(body: unknown, status: number) {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(JSON.stringify(body), { status })
    );
  }

  it("getDaySummary gets /api/estadisticas/resumen without a date by default", async () => {
    mockOk({
      date: "2026-03-10",
      money_total: "0.00",
      orders_charged_count: 0,
      money_by_account: [],
      orders_by_waiter: [],
      top_products: [],
    });
    await getDaySummary();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/estadisticas/resumen"),
      expect.objectContaining({ credentials: "include" })
    );
    expect(global.fetch).not.toHaveBeenCalledWith(
      expect.stringContaining("date="),
      expect.anything()
    );
  });

  it("getDaySummary appends ?date= when given one", async () => {
    mockOk({
      date: "2026-03-10",
      money_total: "0.00",
      orders_charged_count: 0,
      money_by_account: [],
      orders_by_waiter: [],
      top_products: [],
    });
    await getDaySummary("2026-03-10");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/estadisticas/resumen?date=2026-03-10"),
      expect.anything()
    );
  });

  it("getRangeSummary gets /api/estadisticas/rango with from/to and propagates a 400", async () => {
    mockOk({
      from: "2026-03-01",
      to: "2026-03-10",
      money_total: "0.00",
      orders_sent_count: 0,
      money_by_account: [],
      orders_by_waiter: [],
      top_products: [],
    });
    await getRangeSummary("2026-03-01", "2026-03-10");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining(
        "/api/estadisticas/rango?from=2026-03-01&to=2026-03-10"
      ),
      expect.anything()
    );

    mockError({ detail: "from no puede ser posterior a to." }, 400);
    await expect(
      getRangeSummary("2026-03-10", "2026-03-01")
    ).rejects.toEqual({ detail: "from no puede ser posterior a to." });
  });

  it("getDayMovement gets /api/estadisticas/movimiento", async () => {
    mockOk({ date: "2026-03-10", orders: [], payments: [] });
    await getDayMovement("2026-03-10");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/estadisticas/movimiento?date=2026-03-10"),
      expect.anything()
    );
  });
});
