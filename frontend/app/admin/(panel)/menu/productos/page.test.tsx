import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/lib/api/menu", () => ({
  listCategories: vi.fn().mockResolvedValue([]),
  listProducts: vi.fn().mockResolvedValue([]),
  createProduct: vi.fn(),
  updateProduct: vi.fn(),
  setProductAvailability: vi.fn(),
  deleteProduct: vi.fn(),
}));

import ProductosPage from "./page";

describe("/admin/menu/productos page (T39)", () => {
  it("renders the product management screen", () => {
    render(<ProductosPage />);
    expect(
      screen.getByRole("heading", { name: /gestión de productos/i })
    ).toBeInTheDocument();
  });
});
