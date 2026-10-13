import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MenuMeseroView } from "./MenuMeseroView";

vi.mock("@/lib/api/menu", () => ({
  getMenu: vi.fn(),
}));
vi.mock("@/lib/api/menuSocket", () => ({
  subscribeToMenuUpdates: vi.fn(),
}));

import { getMenu } from "@/lib/api/menu";
import { subscribeToMenuUpdates } from "@/lib/api/menuSocket";

const MENU = [
  {
    id: 1,
    name: "Limonada",
    category: { id: 1, name: "Bebidas" },
    price: "4.50",
    is_available: true,
  },
];

describe("MenuMeseroView (T40, RF-6/7)", () => {
  const closeMock = vi.fn();

  beforeEach(() => {
    vi.mocked(getMenu).mockReset();
    vi.mocked(subscribeToMenuUpdates).mockReset();
    closeMock.mockReset();
    vi.mocked(getMenu).mockResolvedValue(MENU);
    vi.mocked(subscribeToMenuUpdates).mockReturnValue({ close: closeMock });
  });

  it("loads and displays the current menu on mount", async () => {
    render(<MenuMeseroView />);
    expect(await screen.findByText(/limonada/i)).toBeInTheDocument();
  });

  it("shows the price with a thousands separator", async () => {
    vi.mocked(getMenu).mockResolvedValue([
      { ...MENU[0], price: "15000.00" },
    ]);
    render(<MenuMeseroView />);
    expect(await screen.findByText("$15.000,00")).toBeInTheDocument();
  });

  it("subscribes to menu updates and refetches when notified", async () => {
    render(<MenuMeseroView />);
    await screen.findByText(/limonada/i);
    expect(getMenu).toHaveBeenCalledTimes(1);

    const onMenuChanged = vi.mocked(subscribeToMenuUpdates).mock.calls[0][0];
    vi.mocked(getMenu).mockResolvedValue([
      {
        id: 2,
        name: "Jugo de naranja",
        category: { id: 1, name: "Bebidas" },
        price: "5.00",
        is_available: true,
      },
    ]);
    onMenuChanged();

    expect(await screen.findByText(/jugo de naranja/i)).toBeInTheDocument();
    expect(getMenu).toHaveBeenCalledTimes(2);
  });

  it("the manual 'Actualizar menú' button triggers the same refetch", async () => {
    const user = userEvent.setup();
    render(<MenuMeseroView />);
    await screen.findByText(/limonada/i);

    await user.click(screen.getByRole("button", { name: /actualizar menú/i }));
    await waitFor(() => expect(getMenu).toHaveBeenCalledTimes(2));
  });

  it("closes the socket subscription on unmount", async () => {
    const { unmount } = render(<MenuMeseroView />);
    await screen.findByText(/limonada/i);

    unmount();
    expect(closeMock).toHaveBeenCalledTimes(1);
  });

  // 002 RF-9 — barra de búsqueda que resalta sin ocultar el resto.
  describe("menu search", () => {
    const BIG_MENU = [
      { id: 1, name: "Limonada", category: { id: 1, name: "Bebidas" }, price: "4.50", is_available: true },
      { id: 2, name: "Jugo de mora", category: { id: 1, name: "Bebidas" }, price: "5.00", is_available: true },
      { id: 3, name: "Canción de la casa", category: { id: 2, name: "Platos" }, price: "20.00", is_available: true },
      { id: 4, name: "Mora con leche", category: { id: 1, name: "Bebidas" }, price: "6.00", is_available: true },
    ];

    beforeEach(() => {
      vi.mocked(getMenu).mockResolvedValue(BIG_MENU);
      Element.prototype.scrollIntoView = vi.fn();
    });

    it("highlights the matching part ignoring case and accents, keeping every dish", async () => {
      const user = userEvent.setup();
      const { container } = render(<MenuMeseroView />);
      await screen.findByText(/limonada/i);

      await user.type(screen.getByLabelText(/buscar en el menú/i), "CANCION");

      const marks = container.querySelectorAll("mark");
      expect(Array.from(marks).map((m) => m.textContent)).toEqual(["Canción"]);
      expect(screen.getByText(/limonada/i)).toBeInTheDocument();
      expect(screen.getByText(/1 de 1 coincidencia$/i)).toBeInTheDocument();
      expect(container.querySelector("#menu-product-3")).toHaveAttribute("aria-current", "true");
    });

    it("scrolls to the current match and moves between matches with the arrows", async () => {
      const user = userEvent.setup();
      const { container } = render(<MenuMeseroView />);
      await screen.findByText(/limonada/i);

      await user.type(screen.getByLabelText(/buscar en el menú/i), "mora");
      expect(screen.getByText(/1 de 2 coincidencias/i)).toBeInTheDocument();
      expect(container.querySelector("#menu-product-2")).toHaveAttribute("aria-current", "true");
      expect(Element.prototype.scrollIntoView).toHaveBeenCalled();

      await user.click(screen.getByRole("button", { name: /coincidencia siguiente/i }));
      expect(screen.getByText(/2 de 2 coincidencias/i)).toBeInTheDocument();
      expect(container.querySelector("#menu-product-4")).toHaveAttribute("aria-current", "true");

      await user.click(screen.getByRole("button", { name: /coincidencia siguiente/i }));
      expect(container.querySelector("#menu-product-2")).toHaveAttribute("aria-current", "true");

      await user.click(screen.getByRole("button", { name: /coincidencia anterior/i }));
      expect(container.querySelector("#menu-product-4")).toHaveAttribute("aria-current", "true");
    });

    it("Enter jumps to the next match", async () => {
      const user = userEvent.setup();
      const { container } = render(<MenuMeseroView />);
      await screen.findByText(/limonada/i);
      await user.type(screen.getByLabelText(/buscar en el menú/i), "mora{Enter}");
      expect(container.querySelector("#menu-product-4")).toHaveAttribute("aria-current", "true");
    });

    it("says when nothing was found", async () => {
      const user = userEvent.setup();
      const { container } = render(<MenuMeseroView />);
      await screen.findByText(/limonada/i);
      await user.type(screen.getByLabelText(/buscar en el menú/i), "sushi");
      expect(screen.getByText(/no se encontró «sushi»/i)).toBeInTheDocument();
      expect(container.querySelectorAll("mark")).toHaveLength(0);
    });
  });
});
