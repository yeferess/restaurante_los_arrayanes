import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/mesero/mesas",
}));

vi.mock("@/lib/api/auth", () => ({
  logout: vi.fn(),
}));

import TurnoLayout from "./layout";

describe("/mesero/(turno) layout (T40)", () => {
  it("renders its children", () => {
    render(
      <TurnoLayout>
        <p>contenido del turno</p>
      </TurnoLayout>
    );
    expect(screen.getByText("contenido del turno")).toBeInTheDocument();
  });
});
