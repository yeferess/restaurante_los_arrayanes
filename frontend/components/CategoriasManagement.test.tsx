import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CategoriasManagement } from "./CategoriasManagement";

vi.mock("@/lib/api/menu", () => ({
  listCategories: vi.fn(),
  createCategory: vi.fn(),
  renameCategory: vi.fn(),
  deleteCategory: vi.fn(),
}));

import {
  listCategories,
  createCategory,
  renameCategory,
  deleteCategory,
} from "@/lib/api/menu";

describe("CategoriasManagement (T38, RF-1)", () => {
  beforeEach(() => {
    vi.mocked(listCategories).mockReset();
    vi.mocked(createCategory).mockReset();
    vi.mocked(renameCategory).mockReset();
    vi.mocked(deleteCategory).mockReset();
    vi.mocked(listCategories).mockResolvedValue([{ id: 1, name: "Bebidas" }]);
  });

  it("loads and lists existing categories on mount", async () => {
    render(<CategoriasManagement />);
    expect(await screen.findByDisplayValue("Bebidas")).toBeInTheDocument();
  });

  it("creates a category and refreshes the list", async () => {
    vi.mocked(createCategory).mockResolvedValue({ id: 2, name: "Postres" });
    const user = userEvent.setup();
    render(<CategoriasManagement />);
    await screen.findByDisplayValue("Bebidas");

    vi.mocked(listCategories).mockResolvedValue([
      { id: 1, name: "Bebidas" },
      { id: 2, name: "Postres" },
    ]);
    await user.type(screen.getByLabelText(/nueva categoría/i), "Postres");
    await user.click(screen.getByRole("button", { name: /crear categoría/i }));

    await waitFor(() => expect(createCategory).toHaveBeenCalledWith("Postres"));
    expect(await screen.findByDisplayValue("Postres")).toBeInTheDocument();
  });

  it("shows the duplicate-name error when creating a category", async () => {
    vi.mocked(createCategory).mockRejectedValue({
      detail: "Ya existe una categoría con ese nombre.",
    });
    const user = userEvent.setup();
    render(<CategoriasManagement />);
    await screen.findByDisplayValue("Bebidas");

    await user.type(screen.getByLabelText(/nueva categoría/i), "bebidas");
    await user.click(screen.getByRole("button", { name: /crear categoría/i }));

    expect(
      await screen.findByText("Ya existe una categoría con ese nombre.")
    ).toBeInTheDocument();
  });

  it("renames a category", async () => {
    vi.mocked(renameCategory).mockResolvedValue({ id: 1, name: "Refrescos" });
    const user = userEvent.setup();
    render(<CategoriasManagement />);
    const input = await screen.findByDisplayValue("Bebidas");

    await user.clear(input);
    await user.type(input, "Refrescos");
    await user.click(screen.getByRole("button", { name: /renombrar/i }));

    await waitFor(() => expect(renameCategory).toHaveBeenCalledWith(1, "Refrescos"));
  });

  it("shows the 409 error when deleting a category with products assigned", async () => {
    vi.mocked(deleteCategory).mockRejectedValue({
      detail: "Reasigna los productos de esta categoría antes de eliminarla.",
    });
    const user = userEvent.setup();
    render(<CategoriasManagement />);
    await screen.findByDisplayValue("Bebidas");

    await user.click(screen.getByRole("button", { name: /eliminar/i }));

    expect(
      await screen.findByText(
        "Reasigna los productos de esta categoría antes de eliminarla."
      )
    ).toBeInTheDocument();
  });

  it("deletes a category successfully", async () => {
    vi.mocked(deleteCategory).mockResolvedValue(undefined);
    vi.mocked(listCategories)
      .mockResolvedValueOnce([{ id: 1, name: "Bebidas" }])
      .mockResolvedValueOnce([]);
    const user = userEvent.setup();
    render(<CategoriasManagement />);
    await screen.findByDisplayValue("Bebidas");

    await user.click(screen.getByRole("button", { name: /eliminar/i }));

    await waitFor(() => expect(deleteCategory).toHaveBeenCalledWith(1));
    await waitFor(() =>
      expect(screen.queryByDisplayValue("Bebidas")).not.toBeInTheDocument()
    );
  });
});
