import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AdminNewOrder } from "./AdminNewOrder";

const { router } = vi.hoisted(() => ({ router: { push: vi.fn() } }));

vi.mock("next/navigation", () => ({
  useRouter: () => router,
}));

vi.mock("@/lib/api/orders", () => ({
  createOrder: vi.fn(),
  listMyOrders: vi.fn(),
  listTables: vi.fn(),
}));

import { createOrder, listMyOrders, listTables } from "@/lib/api/orders";

const BASE_ORDER = {
  id: 70,
  table_number: null,
  waiter_id: 9,
  waiter_username: "admin_caja",
  status: "DRAFT" as const,
  delivered: false,
  items: [],
  total: "0.00",
  has_pending_print: false,
  active_payment: null,
  daily_number: null,
  sent_at: null,
  created_at: "2026-10-13T15:00:00Z",
  draft_reminder: false,
};

// 003 RF-18 — el admin crea pedidos desde el computador.
describe("AdminNewOrder (T98, 003 RF-18)", () => {
  beforeEach(() => {
    router.push.mockReset();
    vi.mocked(createOrder).mockReset();
    vi.mocked(listTables).mockResolvedValue([
      { number: 1, status: "OCCUPIED", active_order_daily_number: 3 },
      { number: 2, status: "FREE", active_order_daily_number: null },
    ]);
    vi.mocked(listMyOrders).mockResolvedValue([]);
  });

  it("creates a counter order and opens it", async () => {
    vi.mocked(createOrder).mockResolvedValue(BASE_ORDER);
    const user = userEvent.setup();
    render(<AdminNewOrder />);

    await user.click(screen.getByRole("button", { name: /mostrador \/ para llevar/i }));

    expect(createOrder).toHaveBeenCalledWith(null);
    await waitFor(() => expect(router.push).toHaveBeenCalledWith("/admin/pedidos/nuevo/70"));
  });

  it("offers only the free tables and creates an order on one", async () => {
    vi.mocked(createOrder).mockResolvedValue({ ...BASE_ORDER, id: 71, table_number: 2 });
    const user = userEvent.setup();
    render(<AdminNewOrder />);

    await user.click(await screen.findByRole("button", { name: "Mesa 2" }));
    expect(screen.queryByRole("button", { name: "Mesa 1" })).not.toBeInTheDocument();
    expect(createOrder).toHaveBeenCalledWith(2);
    await waitFor(() => expect(router.push).toHaveBeenCalledWith("/admin/pedidos/nuevo/71"));
  });

  it("lists the admin's own open orders to keep editing them", async () => {
    vi.mocked(listMyOrders).mockResolvedValue([
      { ...BASE_ORDER, id: 72, status: "IN_PROGRESS", daily_number: 8, total: "6000.00" },
      { ...BASE_ORDER, id: 73, status: "CHARGED", daily_number: 7 },
    ]);
    render(<AdminNewOrder />);

    const link = await screen.findByRole("link", { name: /n° 8 · mostrador/i });
    expect(link).toHaveAttribute("href", "/admin/pedidos/nuevo/72");
    expect(screen.queryByRole("link", { name: /n° 7/i })).not.toBeInTheDocument();
  });

  it("shows the error when creating fails", async () => {
    vi.mocked(createOrder).mockRejectedValue({ detail: "La mesa no está libre." });
    const user = userEvent.setup();
    render(<AdminNewOrder />);
    await user.click(await screen.findByRole("button", { name: "Mesa 2" }));
    expect(await screen.findByText("La mesa no está libre.")).toBeInTheDocument();
  });
});
