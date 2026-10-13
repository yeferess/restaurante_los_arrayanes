import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProductosManagement } from "./ProductosManagement";

vi.mock("@/lib/api/menu", () => ({
  listCategories: vi.fn(),
  listProducts: vi.fn(),
  createProduct: vi.fn(),
  updateProduct: vi.fn(),
  setProductAvailability: vi.fn(),
  deleteProduct: vi.fn(),
}));

import {
  listCategories,
  listProducts,
  createProduct,
  updateProduct,
  setProductAvailability,
  deleteProduct,
} from "@/lib/api/menu";

const CATEGORIES = [
  { id: 1, name: "Bebidas" },
  { id: 2, name: "Postres" },
];

const PRODUCTS = [
  {
    id: 10,
    name: "Limonada",
    category: { id: 1, name: "Bebidas" },
    price: "4.50",
    is_available: true,
  },
];

describe("ProductosManagement (T39, RF-2/3/4/5)", () => {
  beforeEach(() => {
    vi.mocked(listCategories).mockReset();
    vi.mocked(listProducts).mockReset();
    vi.mocked(createProduct).mockReset();
    vi.mocked(updateProduct).mockReset();
    vi.mocked(setProductAvailability).mockReset();
    vi.mocked(deleteProduct).mockReset();
    vi.mocked(listCategories).mockResolvedValue(CATEGORIES);
    vi.mocked(listProducts).mockResolvedValue(PRODUCTS);
  });

  it("populates the category field as a dropdown, never free text", async () => {
    render(<ProductosManagement />);
    const select = await screen.findByLabelText(/^categoría$/i);
    expect(select.tagName).toBe("SELECT");
    expect(within(select).getByRole("option", { name: "Bebidas" })).toBeInTheDocument();
    expect(within(select).getByRole("option", { name: "Postres" })).toBeInTheDocument();
  });

  it("shows a message instead of the create form when there are no categories yet", async () => {
    vi.mocked(listCategories).mockResolvedValue([]);
    render(<ProductosManagement />);
    expect(
      await screen.findByText(/crea al menos una categoría/i)
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(/nombre del producto/i)).not.toBeInTheDocument();
  });

  it("creates a product using the selected category id", async () => {
    vi.mocked(createProduct).mockResolvedValue(PRODUCTS[0]);
    const user = userEvent.setup();
    render(<ProductosManagement />);
    await screen.findByLabelText(/^categoría$/i);

    await user.type(screen.getByLabelText(/nombre del producto/i), "Te helado");
    await user.selectOptions(screen.getByLabelText(/^categoría$/i), "2");
    await user.type(screen.getByLabelText(/^precio$/i), "3.5");
    await user.click(screen.getByRole("button", { name: /crear producto/i }));

    await waitFor(() =>
      expect(createProduct).toHaveBeenCalledWith("Te helado", 2, 3.5)
    );
  });

  it("shows the duplicate-name error when creating a product", async () => {
    vi.mocked(createProduct).mockRejectedValue({
      detail: "Ya existe un producto con ese nombre.",
    });
    const user = userEvent.setup();
    render(<ProductosManagement />);
    await screen.findByLabelText(/^categoría$/i);

    await user.type(screen.getByLabelText(/nombre del producto/i), "Limonada");
    await user.type(screen.getByLabelText(/^precio$/i), "4.5");
    await user.click(screen.getByRole("button", { name: /crear producto/i }));

    expect(
      await screen.findByText("Ya existe un producto con ese nombre.")
    ).toBeInTheDocument();
  });

  it("saves an edited price", async () => {
    vi.mocked(updateProduct).mockResolvedValue(PRODUCTS[0]);
    const user = userEvent.setup();
    render(<ProductosManagement />);
    const priceInput = await screen.findByLabelText(/precio \(limonada\)/i);

    await user.clear(priceInput);
    await user.type(priceInput, "5.00");
    await user.click(screen.getByRole("button", { name: /guardar/i }));

    await waitFor(() =>
      expect(updateProduct).toHaveBeenCalledWith(10, {
        name: "Limonada",
        categoryId: 1,
        price: 5,
      })
    );
  });

  it("toggles availability", async () => {
    vi.mocked(setProductAvailability).mockResolvedValue({
      ...PRODUCTS[0],
      is_available: false,
    });
    const user = userEvent.setup();
    render(<ProductosManagement />);
    await screen.findByLabelText(/^categoría$/i);

    await user.click(screen.getByRole("button", { name: /marcar no disponible/i }));

    await waitFor(() => expect(setProductAvailability).toHaveBeenCalledWith(10, false));
  });

  it("deletes a product", async () => {
    vi.mocked(deleteProduct).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<ProductosManagement />);
    await screen.findByLabelText(/^categoría$/i);

    await user.click(screen.getByRole("button", { name: /^eliminar$/i }));

    await waitFor(() => expect(deleteProduct).toHaveBeenCalledWith(10));
  });

  // 002 RF-9 — barra de búsqueda en el menú del admin.
  it("highlights the product row that matches the search, ignoring case and accents", async () => {
    Element.prototype.scrollIntoView = vi.fn();
    vi.mocked(listProducts).mockResolvedValue([
      PRODUCTS[0],
      { id: 11, name: "Canción de la casa", category: { id: 2, name: "Postres" }, price: "20.00", is_available: true },
    ]);
    const user = userEvent.setup();
    const { container } = render(<ProductosManagement />);
    await screen.findByDisplayValue("Canción de la casa");

    await user.type(screen.getByLabelText(/buscar en el menú/i), "cancion");

    expect(container.querySelector("#admin-product-11")).toHaveAttribute("aria-current", "true");
    expect(container.querySelector("#admin-product-10")).not.toHaveAttribute("aria-current");
    expect(screen.getByText(/1 de 1 coincidencia$/i)).toBeInTheDocument();
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
    // Nothing is hidden: the other product is still listed.
    expect(screen.getByDisplayValue("Limonada")).toBeInTheDocument();
  });
});
