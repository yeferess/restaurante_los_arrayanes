import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/components/SessionHeartbeat", () => ({
  SessionHeartbeat: () => <div data-testid="session-heartbeat" />,
}));

import PanelLayout from "./layout";

describe("/admin/(panel) layout (T52, RF-8)", () => {
  it("mounts SessionHeartbeat alongside the page content", () => {
    render(
      <PanelLayout>
        <p>contenido del panel</p>
      </PanelLayout>
    );
    expect(screen.getByTestId("session-heartbeat")).toBeInTheDocument();
    expect(screen.getByText("contenido del panel")).toBeInTheDocument();
  });
});
