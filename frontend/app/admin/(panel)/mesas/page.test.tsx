import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/lib/api/orders", () => ({
  listTables: vi.fn().mockResolvedValue([]),
  resizeTables: vi.fn(),
}));

import MesasPage from "./page";

describe("/admin/mesas page (T64)", () => {
  it("renders the table count management screen", () => {
    render(<MesasPage />);
    expect(
      screen.getByRole("heading", { name: /gestión de mesas/i })
    ).toBeInTheDocument();
  });
});
