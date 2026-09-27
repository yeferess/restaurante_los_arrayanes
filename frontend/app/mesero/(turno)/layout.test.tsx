import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
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
