import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/lib/api/menu", () => ({
  listCategories: vi.fn().mockResolvedValue([]),
  createCategory: vi.fn(),
  renameCategory: vi.fn(),
  deleteCategory: vi.fn(),
}));

import CategoriasPage from "./page";

describe("/admin/menu/categorias page (T38)", () => {
  it("renders the category management screen", () => {
    render(<CategoriasPage />);
    expect(
      screen.getByRole("heading", { name: /gestión de categorías/i })
    ).toBeInTheDocument();
  });
});
