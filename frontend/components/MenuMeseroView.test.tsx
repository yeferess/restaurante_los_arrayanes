import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MenuMeseroView } from "./MenuMeseroView";

vi.mock("@/lib/api/menu", () => ({
  getMenu: vi.fn(),
}));
vi.mock("@/lib/api/menuSocket", () => ({
  subscribeToMenuUpdates: vi.fn(),
}));

import { getMenu } from "@/lib/api/menu";
import { subscribeToMenuUpdates } from "@/lib/api/menuSocket";

const MENU = [
  {
    id: 1,
    name: "Limonada",
    category: { id: 1, name: "Bebidas" },
    price: "4.50",
    is_available: true,
  },
];

describe("MenuMeseroView (T40, RF-6/7)", () => {
  const closeMock = vi.fn();

  beforeEach(() => {
    vi.mocked(getMenu).mockReset();
    vi.mocked(subscribeToMenuUpdates).mockReset();
    closeMock.mockReset();
    vi.mocked(getMenu).mockResolvedValue(MENU);
    vi.mocked(subscribeToMenuUpdates).mockReturnValue({ close: closeMock });
  });

  it("loads and displays the current menu on mount", async () => {
    render(<MenuMeseroView />);
    expect(await screen.findByText(/limonada/i)).toBeInTheDocument();
  });

  it("shows the price with a thousands separator", async () => {
    vi.mocked(getMenu).mockResolvedValue([
      { ...MENU[0], price: "15000.00" },
    ]);
    render(<MenuMeseroView />);
    expect(await screen.findByText("$15.000,00")).toBeInTheDocument();
  });

  it("subscribes to menu updates and refetches when notified", async () => {
    render(<MenuMeseroView />);
    await screen.findByText(/limonada/i);
    expect(getMenu).toHaveBeenCalledTimes(1);

    const onMenuChanged = vi.mocked(subscribeToMenuUpdates).mock.calls[0][0];
    vi.mocked(getMenu).mockResolvedValue([
      {
        id: 2,
        name: "Jugo de naranja",
        category: { id: 1, name: "Bebidas" },
        price: "5.00",
        is_available: true,
      },
    ]);
    onMenuChanged();

    expect(await screen.findByText(/jugo de naranja/i)).toBeInTheDocument();
    expect(getMenu).toHaveBeenCalledTimes(2);
  });

  it("the manual 'Actualizar menú' button triggers the same refetch", async () => {
    const user = userEvent.setup();
    render(<MenuMeseroView />);
    await screen.findByText(/limonada/i);

    await user.click(screen.getByRole("button", { name: /actualizar menú/i }));
    await waitFor(() => expect(getMenu).toHaveBeenCalledTimes(2));
  });

  it("closes the socket subscription on unmount", async () => {
    const { unmount } = render(<MenuMeseroView />);
    await screen.findByText(/limonada/i);

    unmount();
    expect(closeMock).toHaveBeenCalledTimes(1);
  });
});
