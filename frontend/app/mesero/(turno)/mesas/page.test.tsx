import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/lib/api/orders", () => ({
  listTables: vi.fn().mockResolvedValue([]),
  createOrder: vi.fn(),
}));

import MesasPage from "./page";

describe("/mesero/mesas page (T65)", () => {
  it("renders the table overview screen", () => {
    render(<MesasPage />);
    expect(screen.getByRole("heading", { name: /mesas/i })).toBeInTheDocument();
  });
});
