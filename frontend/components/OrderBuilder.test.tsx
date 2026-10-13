import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OrderBuilder } from "./OrderBuilder";

vi.mock("@/lib/api/orders", () => ({
  getOrder: vi.fn(),
  addItem: vi.fn(),
  voidItem: vi.fn(),
  removeItem: vi.fn(),
  sendOrder: vi.fn(),
  sendAdditions: vi.fn(),
  printOrder: vi.fn(),
  fixTable: vi.fn(),
  listTables: vi.fn(),
  deleteOrder: vi.fn(),
}));

vi.mock("@/lib/api/menu", () => ({
  getMenu: vi.fn(),
}));

import {
  getOrder,
  addItem,
  voidItem,
  removeItem,
  sendOrder,
  sendAdditions,
  printOrder,
  fixTable,
  listTables,
  deleteOrder,
} from "@/lib/api/orders";
import { getMenu } from "@/lib/api/menu";

const DRAFT_ORDER = {
  id: 41,
  table_number: 1,
  waiter_id: 1,
  waiter_username: "mesero1",
  status: "DRAFT" as const,
  delivered: false,
  items: [],
  total: "0.00",
  has_pending_print: false,
  active_payment: null,
  daily_number: null,
  sent_at: null,
  created_at: "2026-03-10T18:55:00Z",
  draft_reminder: false,
};

const DELIVERED_ORDER = {
  ...DRAFT_ORDER,
  status: "IN_PROGRESS" as const,
  delivered: true,
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
      line_total: "4.50",
    },
  ],
};

describe("OrderBuilder (T66, RF-3/4/5/6/7)", () => {
  beforeEach(() => {
    vi.mocked(getOrder).mockReset();
    vi.mocked(addItem).mockReset();
    vi.mocked(voidItem).mockReset();
    vi.mocked(removeItem).mockReset();
    vi.mocked(sendOrder).mockReset();
    vi.mocked(sendAdditions).mockReset();
    vi.mocked(printOrder).mockReset();
    vi.mocked(fixTable).mockReset();
    vi.mocked(listTables).mockReset();
    vi.mocked(getMenu).mockReset();
    vi.mocked(deleteOrder).mockReset();
    vi.mocked(deleteOrder).mockResolvedValue(undefined);

    vi.mocked(getOrder).mockResolvedValue(DRAFT_ORDER);
    vi.mocked(getMenu).mockResolvedValue([
      { id: 5, name: "Limonada", category: { id: 1, name: "Bebidas" }, price: "4.50", is_available: true },
    ]);
    vi.mocked(listTables).mockResolvedValue([
      { number: 1, status: "OCCUPIED", active_order_daily_number: null },
      { number: 2, status: "FREE", active_order_daily_number: null },
    ]);
  });

  it("discards an empty draft when the mesero leaves the screen (RF-15)", async () => {
    const { unmount } = render(<OrderBuilder orderId={41} />);
    await screen.findByRole("button", { name: /crear pedido/i });
    unmount();
    expect(deleteOrder).toHaveBeenCalledWith(41);
  });

  it("keeps a draft that already has items when leaving the screen", async () => {
    vi.mocked(getOrder).mockResolvedValue({ ...IN_PROGRESS_ORDER, status: "DRAFT" });
    const { unmount } = render(<OrderBuilder orderId={41} />);
    await screen.findByText(/limonada/i, { selector: "span" });
    unmount();
    expect(deleteOrder).not.toHaveBeenCalled();
  });

  it("keeps a sent order when leaving the screen", async () => {
    vi.mocked(getOrder).mockResolvedValue({ ...DRAFT_ORDER, status: "IN_PROGRESS" });
    const { unmount } = render(<OrderBuilder orderId={41} />);
    await screen.findByText(/en preparación/i);
    unmount();
    expect(deleteOrder).not.toHaveBeenCalled();
  });

  it("shows each line's unit price and total, and the order total (RF-3)", async () => {
    vi.mocked(getOrder).mockResolvedValue({
      ...IN_PROGRESS_ORDER,
      items: [{ ...IN_PROGRESS_ORDER.items[0], quantity: 3, line_total: "13.50" }],
      total: "13.50",
    });
    render(<OrderBuilder orderId={41} />);
    expect(await screen.findByText(/\$4,50 c\/u/)).toBeInTheDocument();
    expect(screen.getAllByText("$13,50")).toHaveLength(2);
    expect(screen.getByText("Total")).toBeInTheDocument();
  });

  it("removes an item from a draft without asking for a reason (RF-2)", async () => {
    const user = userEvent.setup();
    const promptSpy = vi.spyOn(window, "prompt");
    vi.mocked(removeItem).mockResolvedValue(undefined);
    vi.mocked(getOrder).mockResolvedValueOnce({ ...IN_PROGRESS_ORDER, status: "DRAFT" });
    vi.mocked(getOrder).mockResolvedValue(DRAFT_ORDER);
    render(<OrderBuilder orderId={41} />);

    await user.click(await screen.findByRole("button", { name: /^eliminar$/i }));

    expect(removeItem).toHaveBeenCalledWith(41, 100);
    expect(promptSpy).not.toHaveBeenCalled();
    expect(await screen.findByText(/todavía no agregaste ningún ítem/i)).toBeInTheDocument();
  });

  it("shows the error when removing an item fails", async () => {
    const user = userEvent.setup();
    vi.mocked(removeItem).mockRejectedValue({ detail: ["Solo se pueden quitar ítems de un pedido en borrador."] });
    vi.mocked(getOrder).mockResolvedValue({ ...IN_PROGRESS_ORDER, status: "DRAFT" });
    render(<OrderBuilder orderId={41} />);

    await user.click(await screen.findByRole("button", { name: /^eliminar$/i }));

    expect(await screen.findByText(/solo se pueden quitar ítems/i)).toBeInTheDocument();
  });

  it("offers 'Anular' instead of 'Eliminar' once the order was sent", async () => {
    vi.mocked(getOrder).mockResolvedValue(IN_PROGRESS_ORDER);
    render(<OrderBuilder orderId={41} />);
    expect(await screen.findByRole("button", { name: /^anular$/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^eliminar$/i })).not.toBeInTheDocument();
  });

  it("shows the order and lets the mesero create it ('Crear pedido')", async () => {
    vi.mocked(sendOrder).mockResolvedValue({ ...DRAFT_ORDER, status: "IN_PROGRESS" });
    const user = userEvent.setup();
    render(<OrderBuilder orderId={41} />);

    expect(await screen.findByRole("button", { name: /crear pedido/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /crear pedido/i }));

    await waitFor(() => expect(sendOrder).toHaveBeenCalledWith(41));
  });

  it("shows an item's unit price with a thousands separator", async () => {
    vi.mocked(getOrder).mockResolvedValue({
      ...IN_PROGRESS_ORDER,
      items: [{ ...IN_PROGRESS_ORDER.items[0], unit_price: "15000.00" }],
    });
    render(<OrderBuilder orderId={41} />);
    expect(await screen.findByText(/\$15\.000,00/)).toBeInTheDocument();
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
      line_total: "4.50",
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
      line_total: "6.00",
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

  // 003 RF-5, 004 RF-1: crear y imprimir son pasos separados.
  describe("create, send additions and print as separate steps", () => {
    const UNSENT_ADDITION = {
      ...IN_PROGRESS_ORDER.items[0],
      id: 101,
      name: "Jugo de mora",
      unit_price: "6.00",
      line_total: "6.00",
      line_type: "ADDITION" as const,
      pending_send: true,
    };
    const WITH_UNSENT = {
      ...IN_PROGRESS_ORDER,
      items: [IN_PROGRESS_ORDER.items[0], UNSENT_ADDITION],
      total: "4.50",
      pending_additions_count: 1,
      pending_additions_total: "6.00",
      has_unprinted_changes: true,
    };

    it("'Crear pedido' does not print and tells how to print", async () => {
      vi.mocked(sendOrder).mockResolvedValue({
        ...IN_PROGRESS_ORDER,
        print_warning: null,
        has_unprinted_changes: true,
      });
      const user = userEvent.setup();
      render(<OrderBuilder orderId={41} />);
      await user.click(await screen.findByRole("button", { name: /crear pedido/i }));

      expect(await screen.findByText(/pedido creado/i)).toBeInTheDocument();
      expect(printOrder).not.toHaveBeenCalled();
      expect(screen.getByRole("button", { name: /^imprimir pedido$/i })).toBeEnabled();
    });

    it("offers no 'Imprimir pedido' while still a draft", async () => {
      render(<OrderBuilder orderId={41} />);
      await screen.findByRole("button", { name: /crear pedido/i });
      expect(screen.queryByRole("button", { name: /imprimir pedido/i })).not.toBeInTheDocument();
    });

    it("prints and shows the confirmation", async () => {
      vi.mocked(getOrder).mockResolvedValue({ ...IN_PROGRESS_ORDER, has_unprinted_changes: true });
      vi.mocked(printOrder).mockResolvedValue({
        ...IN_PROGRESS_ORDER,
        has_unprinted_changes: false,
        print_warning: null,
      });
      const user = userEvent.setup();
      render(<OrderBuilder orderId={41} />);
      await user.click(await screen.findByRole("button", { name: /^imprimir pedido$/i }));

      expect(printOrder).toHaveBeenCalledWith(41);
      expect(await screen.findByText("Impreso en cocina.")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /todo impreso/i })).toBeDisabled();
    });

    it("shows the printer warning when printing fails (RF-9)", async () => {
      vi.mocked(getOrder).mockResolvedValue({ ...IN_PROGRESS_ORDER, has_unprinted_changes: true });
      vi.mocked(printOrder).mockResolvedValue({
        ...IN_PROGRESS_ORDER,
        has_unprinted_changes: true,
        has_pending_print: true,
        print_warning: "Impresora de cocina no detectada.",
      });
      const user = userEvent.setup();
      render(<OrderBuilder orderId={41} />);
      await user.click(await screen.findByRole("button", { name: /^imprimir pedido$/i }));
      expect(await screen.findByText("Impresora de cocina no detectada.")).toBeInTheDocument();
    });

    it("disables printing when everything is already on paper", async () => {
      vi.mocked(getOrder).mockResolvedValue({ ...IN_PROGRESS_ORDER, has_unprinted_changes: false });
      render(<OrderBuilder orderId={41} />);
      expect(await screen.findByRole("button", { name: /todo impreso/i })).toBeDisabled();
    });

    it("tags an unsent addition, keeps it out of the total and lets it be removed", async () => {
      vi.mocked(getOrder).mockResolvedValue(WITH_UNSENT);
      render(<OrderBuilder orderId={41} />);
      expect(await screen.findByText("Sin enviar")).toBeInTheDocument();
      expect(screen.getByText(/\+ \$6,00 sin enviar/)).toBeInTheDocument();
      expect(screen.getAllByRole("button", { name: /^eliminar$/i })).toHaveLength(1);
      expect(screen.getAllByRole("button", { name: /^anular$/i })).toHaveLength(1);
    });

    it("sends the additions without printing", async () => {
      vi.mocked(getOrder).mockResolvedValue(WITH_UNSENT);
      vi.mocked(sendAdditions).mockResolvedValue({
        ...WITH_UNSENT,
        items: [IN_PROGRESS_ORDER.items[0], { ...UNSENT_ADDITION, pending_send: false }],
        total: "10.50",
        pending_additions_count: 0,
        pending_additions_total: "0.00",
      });
      const user = userEvent.setup();
      render(<OrderBuilder orderId={41} />);
      await user.click(await screen.findByRole("button", { name: /enviar adición \(1\)/i }));

      expect(sendAdditions).toHaveBeenCalledWith(41);
      expect(printOrder).not.toHaveBeenCalled();
      expect(await screen.findByText(/adición enviada/i)).toBeInTheDocument();
      expect(screen.queryByText("Sin enviar")).not.toBeInTheDocument();
    });

    it("after adding to a created order, explains how it reaches the kitchen", async () => {
      vi.mocked(getOrder).mockResolvedValue(IN_PROGRESS_ORDER);
      vi.mocked(addItem).mockResolvedValue({ ...UNSENT_ADDITION, name: "Limonada" });
      const user = userEvent.setup();
      render(<OrderBuilder orderId={41} />);
      await screen.findByLabelText(/^producto$/i);
      await user.click(screen.getByRole("button", { name: /^agregar$/i }));
      expect(await screen.findByText(/toca «enviar adición» o «imprimir pedido»/i)).toBeInTheDocument();
    });

    it("voiding does not print and reminds to print", async () => {
      vi.mocked(getOrder).mockResolvedValue(IN_PROGRESS_ORDER);
      vi.mocked(voidItem).mockResolvedValue({ ...IN_PROGRESS_ORDER.items[0], is_voided: true });
      vi.spyOn(window, "prompt").mockReturnValue("El cliente cambió de opinión");
      const user = userEvent.setup();
      render(<OrderBuilder orderId={41} />);
      await screen.findByText(/limonada/i, { selector: "span" });
      await user.click(screen.getByRole("button", { name: /anular/i }));

      expect(await screen.findByText(/ítem anulado/i)).toBeInTheDocument();
      expect(printOrder).not.toHaveBeenCalled();
    });
  });

  it("shows 'Entregado' instead of 'En preparación' once delivered is marked (T81, RF-8)", async () => {
    vi.mocked(getOrder).mockResolvedValue(DELIVERED_ORDER);
    render(<OrderBuilder orderId={41} />);
    expect(await screen.findByText("Entregado")).toBeInTheDocument();
    expect(screen.queryByText("En preparación")).not.toBeInTheDocument();
  });

  it("still shows 'En preparación' while not yet delivered (T81, RF-8)", async () => {
    vi.mocked(getOrder).mockResolvedValue(IN_PROGRESS_ORDER);
    render(<OrderBuilder orderId={41} />);
    expect(await screen.findByText("En preparación")).toBeInTheDocument();
  });

  it("still shows 'Cobrado' for a charged order, even if delivered (T81, RF-8)", async () => {
    vi.mocked(getOrder).mockResolvedValue({
      ...DELIVERED_ORDER,
      status: "CHARGED",
    });
    render(<OrderBuilder orderId={41} />);
    expect(await screen.findByText("Cobrado")).toBeInTheDocument();
    expect(screen.queryByText("Entregado")).not.toBeInTheDocument();
  });

  // 003 RF-3 — buscador por nombre al agregar un ítem.
  describe("product search", () => {
    const MENU_WITH_ACCENTS = [
      { id: 5, name: "Limonada", category: { id: 1, name: "Bebidas" }, price: "4.50", is_available: true },
      { id: 6, name: "Canción de la casa", category: { id: 2, name: "Platos" }, price: "20.00", is_available: true },
      { id: 7, name: "Jugo de piña", category: { id: 1, name: "Bebidas" }, price: "5.00", is_available: true },
    ];

    beforeEach(() => {
      vi.mocked(getMenu).mockResolvedValue(MENU_WITH_ACCENTS);
      vi.mocked(addItem).mockResolvedValue({
        id: 201, order_id: 41, name: "Canción de la casa", unit_price: "20.00", quantity: 1,
        note: "", line_type: "ORIGINAL", is_voided: false, void_reason: null, line_total: "20.00",
      });
    });

    it("filters by name ignoring case and accents and selects the first match", async () => {
      const user = userEvent.setup();
      render(<OrderBuilder orderId={41} />);
      const search = await screen.findByLabelText(/buscar por nombre/i);

      await user.type(search, "CANCION");

      const select = screen.getByLabelText(/^producto$/i);
      expect(select).toHaveValue("6");
      expect(within(select).getAllByRole("option").map((o) => o.textContent)).toEqual([
        "Canción de la casa",
      ]);
    });

    it("finds ñ when typing n", async () => {
      const user = userEvent.setup();
      render(<OrderBuilder orderId={41} />);
      await user.type(await screen.findByLabelText(/buscar por nombre/i), "pina");
      expect(screen.getByLabelText(/^producto$/i)).toHaveValue("7");
    });

    it("adds the filtered product and clears the search", async () => {
      const user = userEvent.setup();
      render(<OrderBuilder orderId={41} />);
      const search = await screen.findByLabelText(/buscar por nombre/i);
      await user.type(search, "cancion");
      await user.click(screen.getByRole("button", { name: /^agregar$/i }));

      await waitFor(() =>
        expect(addItem).toHaveBeenCalledWith(41, { productId: 6, quantity: 1, note: undefined })
      );
      await waitFor(() => expect(search).toHaveValue(""));
    });

    it("shows a message and disables 'Agregar' when nothing matches", async () => {
      const user = userEvent.setup();
      render(<OrderBuilder orderId={41} />);
      await user.type(await screen.findByLabelText(/buscar por nombre/i), "sushi");

      expect(screen.getByText(/no hay productos que coincidan con «sushi»/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /^agregar$/i })).toBeDisabled();
    });
  });
});
