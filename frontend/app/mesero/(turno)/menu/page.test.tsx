import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/lib/api/menu", () => ({
  getMenu: vi.fn().mockResolvedValue([]),
}));
vi.mock("@/lib/api/menuSocket", () => ({
  subscribeToMenuUpdates: vi.fn().mockReturnValue({ close: vi.fn() }),
}));

import MenuPage from "./page";

describe("/mesero/menu page (T40)", () => {
  it("renders the mesero menu view", () => {
    render(<MenuPage />);
    expect(screen.getByRole("heading", { name: /menú/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /actualizar menú/i })
    ).toBeInTheDocument();
  });
});
