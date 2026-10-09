import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

import MeseroIndexPage from "./page";

describe("/mesero index page", () => {
  it("redirects to /mesero/mesas", () => {
    render(<MeseroIndexPage />);
    expect(pushMock).toHaveBeenCalledWith("/mesero/mesas");
  });
});
