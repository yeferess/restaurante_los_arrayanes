import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OrderBuilder } from "./OrderBuilder";

vi.mock("@/lib/api/orders", () => ({
  getOrder: vi.fn(),
  addItem: vi.fn(),
  voidItem: vi.fn(),
  sendOrder: vi.fn(),
  fixTable: vi.fn(),
  listTables: vi.fn(),
}));

vi.mock("@/lib/api/menu", () => ({
  getMenu: vi.fn(),
}));

import { getOrder, addItem, voidItem, sendOrder, fixTable, listTables } from "@/lib/api/orders";
import { getMenu } from "@/lib/api/menu";

const DRAFT_ORDER = {
  id: 41,
  table_number: 1,
  waiter_id: 1,
  status: "DRAFT" as const,
  delivered: false,
  items: [],
  total: "0.00",
};

const IN_PROGRESS_ORDER = {
  ...DRAFT_ORDER,
  status: "IN_PROGRESS" as const,
  items: [
    {
      id: 100,
      order_id: 41,
      name: "Limonada",
      unit_price: "4.50",
      quantity: 1,
      note: "",
      line_type: "ORIGINAL" as const,
      is_voided: false,
      void_reason: null,
    },
  ],
};

describe("OrderBuilder (T66, RF-3/4/5/6/7)", () => {
  beforeEach(() => {
    vi.mocked(getOrder).mockReset();
    vi.mocked(addItem).mockReset();
    vi.mocked(voidItem).mockReset();
    vi.mocked(sendOrder).mockReset();
    vi.mocked(fixTable).mockReset();
    vi.mocked(listTables).mockReset();
    vi.mocked(getMenu).mockReset();

    vi.mocked(getOrder).mockResolvedValue(DRAFT_ORDER);
    vi.mocked(getMenu).mockResolvedValue([
      { id: 5, name: "Limonada", category: { id: 1, name: "Bebidas" }, price: "4.50", is_available: true },
    ]);
    vi.mocked(listTables).mockResolvedValue([
      { number: 1, status: "OCCUPIED" },
      { number: 2, status: "FREE" },
    ]);
  });

  it("shows the order and lets the mesero send it", async () => {
    vi.mocked(sendOrder).mockResolvedValue({ ...DRAFT_ORDER, status: "IN_PROGRESS" });
    const user = userEvent.setup();
    render(<OrderBuilder orderId={41} />);

    expect(await screen.findByRole("button", { name: /enviar pedido/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /enviar pedido/i }));

    await waitFor(() => expect(sendOrder).toHaveBeenCalledWith(41));
  });

  it("adds a catalog item", async () => {
    vi.mocked(addItem).mockResolvedValue({
      id: 200,
      order_id: 41,
      name: "Limonada",
      unit_price: "4.50",
      quantity: 1,
      note: "",
      line_type: "ORIGINAL",
      is_voided: false,
      void_reason: null,
    });
    const user = userEvent.setup();
    render(<OrderBuilder orderId={41} />);
    await screen.findByLabelText(/producto/i);

    await user.click(screen.getByRole("button", { name: /^agregar$/i }));

    await waitFor(() =>
      expect(addItem).toHaveBeenCalledWith(41, {
        productId: 5,
        quantity: 1,
        note: undefined,
      })
    );
  });

  it("adds an off-menu item with a note", async () => {
    vi.mocked(addItem).mockResolvedValue({
      id: 201,
      order_id: 41,
      name: "Postre especial",
      unit_price: "6",
      quantity: 1,
      note: "sin azúcar",
      line_type: "ORIGINAL",
      is_voided: false,
      void_reason: null,
    });
    const user = userEvent.setup();
    render(<OrderBuilder orderId={41} />);
    await screen.findByLabelText(/producto/i);

    await user.click(screen.getByLabelText(/fuera de carta/i));
    await user.type(screen.getByLabelText(/^nombre$/i), "Postre especial");
    await user.type(screen.getByLabelText(/^precio$/i), "6");
    await user.type(screen.getByLabelText(/^nota$/i), "sin azúcar");
    await user.click(screen.getByRole("button", { name: /^agregar$/i }));

    await waitFor(() =>
      expect(addItem).toHaveBeenCalledWith(41, {
        name: "Postre especial",
        price: 6,
        quantity: 1,
        note: "sin azúcar",
      })
    );
  });

  it("shows an active item and lets the mesero void it with a reason", async () => {
    vi.mocked(getOrder).mockResolvedValue(IN_PROGRESS_ORDER);
    vi.mocked(voidItem).mockResolvedValue({
      ...IN_PROGRESS_ORDER.items[0],
      is_voided: true,
    });
    vi.spyOn(window, "prompt").mockReturnValue("El cliente cambió de opinión");
    const user = userEvent.setup();
    render(<OrderBuilder orderId={41} />);

    expect(await screen.findByText(/limonada/i, { selector: "span" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /anular/i }));

    await waitFor(() =>
      expect(voidItem).toHaveBeenCalledWith(
        41,
        100,
        "El cliente cambió de opinión"
      )
    );
  });

  it("corrects the table to a free one", async () => {
    vi.mocked(fixTable).mockResolvedValue({ ...DRAFT_ORDER, table_number: 2 });
    const user = userEvent.setup();
    render(<OrderBuilder orderId={41} />);
    await screen.findByLabelText(/mesa destino/i);

    await user.selectOptions(screen.getByLabelText(/mesa destino/i), "2");
    await user.click(screen.getByRole("button", { name: /guardar mesa/i }));

    await waitFor(() => expect(fixTable).toHaveBeenCalledWith(41, 2));
  });

  it("shows the 409 error when adding an item to a charged order", async () => {
    vi.mocked(addItem).mockRejectedValue({
      detail: "Este pedido no admite agregar ítems.",
    });
    const user = userEvent.setup();
    render(<OrderBuilder orderId={41} />);
    await screen.findByLabelText(/producto/i);

    await user.click(screen.getByRole("button", { name: /^agregar$/i }));

    expect(
      await screen.findByText("Este pedido no admite agregar ítems.")
    ).toBeInTheDocument();
  });

  it("shows a print warning immediately when sending the order (T35, RF-9)", async () => {
    vi.mocked(sendOrder).mockResolvedValue({
      ...DRAFT_ORDER,
      status: "IN_PROGRESS",
      print_warning: "Impresora de cocina no detectada.",
    });
    const user = userEvent.setup();
    render(<OrderBuilder orderId={41} />);
    await user.click(await screen.findByRole("button", { name: /enviar pedido/i }));

    expect(
      await screen.findByText("Impresora de cocina no detectada.")
    ).toBeInTheDocument();
  });

  it("shows a print warning immediately after adding an item", async () => {
    vi.mocked(addItem).mockResolvedValue({
      id: 200,
      order_id: 41,
      name: "Limonada",
      unit_price: "4.50",
      quantity: 1,
      note: "",
      line_type: "ORIGINAL",
      is_voided: false,
      void_reason: null,
      print_warning: "Error al imprimir el ticket de cocina.",
    });
    const user = userEvent.setup();
    render(<OrderBuilder orderId={41} />);
    await screen.findByLabelText(/producto/i);

    await user.click(screen.getByRole("button", { name: /^agregar$/i }));

    expect(
      await screen.findByText("Error al imprimir el ticket de cocina.")
    ).toBeInTheDocument();
  });

  it("shows a print warning immediately after voiding an item", async () => {
    vi.mocked(getOrder).mockResolvedValue(IN_PROGRESS_ORDER);
    vi.mocked(voidItem).mockResolvedValue({
      ...IN_PROGRESS_ORDER.items[0],
      is_voided: true,
      print_warning: "Impresora de cocina no detectada.",
    });
    vi.spyOn(window, "prompt").mockReturnValue("El cliente cambió de opinión");
    const user = userEvent.setup();
    render(<OrderBuilder orderId={41} />);

    expect(
      await screen.findByText(/limonada/i, { selector: "span" })
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /anular/i }));

    expect(
      await screen.findByText("Impresora de cocina no detectada.")
    ).toBeInTheDocument();
  });

  it("shows no message when there is no print warning", async () => {
    vi.mocked(sendOrder).mockResolvedValue({
      ...DRAFT_ORDER,
      status: "IN_PROGRESS",
      print_warning: null,
    });
    const user = userEvent.setup();
    render(<OrderBuilder orderId={41} />);
    await user.click(await screen.findByRole("button", { name: /enviar pedido/i }));

    await waitFor(() => expect(sendOrder).toHaveBeenCalled());
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
