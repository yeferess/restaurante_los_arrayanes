import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

import AdminIndexPage from "./page";

describe("/admin index page", () => {
  it("redirects to /admin/mesas", () => {
    render(<AdminIndexPage />);
    expect(pushMock).toHaveBeenCalledWith("/admin/mesas");
  });
});
