import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AdminNoteEditor } from "./AdminNoteEditor";

vi.mock("@/lib/api/orders", () => ({
  setAdminNote: vi.fn(),
}));

import { setAdminNote } from "@/lib/api/orders";

const ORDER = {
  id: 41,
  table_number: 5,
  waiter_id: 1,
  waiter_username: "mesero1",
  status: "IN_PROGRESS" as const,
  delivered: false,
  items: [],
  total: "0.00",
  has_pending_print: false,
  active_payment: null,
  daily_number: 7,
  sent_at: "2026-03-10T20:15:00Z",
  created_at: "2026-03-10T18:55:00Z",
  draft_reminder: false,
  admin_note: "",
};

describe("AdminNoteEditor (003 RF-17)", () => {
  beforeEach(() => {
    vi.mocked(setAdminNote).mockReset();
  });

  it("saves the note and reports it", async () => {
    const user = userEvent.setup();
    const onSaved = vi.fn();
    const updated = { ...ORDER, admin_note: "mesa de cumpleanos" };
    vi.mocked(setAdminNote).mockResolvedValue(updated);
    render(<AdminNoteEditor order={ORDER} onSaved={onSaved} />);

    await user.type(screen.getByLabelText(/nota del pedido/i), "mesa de cumpleanos");
    await user.click(screen.getByRole("button", { name: /guardar/i }));

    expect(setAdminNote).toHaveBeenCalledWith(41, "mesa de cumpleanos");
    expect(await screen.findByText(/nota guardada/i)).toBeInTheDocument();
    expect(onSaved).toHaveBeenCalledWith(updated);
  });

  it("starts with the saved note and keeps 'Guardar' disabled until it changes", () => {
    render(<AdminNoteEditor order={{ ...ORDER, admin_note: "ya pago" }} />);
    expect(screen.getByLabelText(/nota del pedido/i)).toHaveValue("ya pago");
    expect(screen.getByRole("button", { name: /guardar/i })).toBeDisabled();
  });

  it("shows the error when saving fails", async () => {
    const user = userEvent.setup();
    vi.mocked(setAdminNote).mockRejectedValue({
      detail: ["La nota no puede superar los 300 caracteres."],
    });
    render(<AdminNoteEditor order={ORDER} />);
    await user.type(screen.getByLabelText(/nota del pedido/i), "x");
    await user.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/no puede superar/i)).toBeInTheDocument();
  });
});
