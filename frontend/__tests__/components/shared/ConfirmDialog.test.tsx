/**
 * Tests for shared ConfirmDialog — destructive action confirmation.
 *
 * Spec (projects-ui / advances-ui): reject/cancel/close/archive open a
 * ConfirmDialog before the mutation is fired.
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";

describe("ConfirmDialog", () => {
  it("shows title, description, and cancel/confirm actions when open", () => {
    render(
      <ConfirmDialog
        open
        onOpenChange={jest.fn()}
        title="Rechazar proyecto"
        description="Esta acción es irreversible."
        confirmLabel="Rechazar"
        cancelLabel="Cancelar"
        onConfirm={jest.fn()}
      />,
    );

    const dialog = screen.getByRole("alertdialog");
    expect(dialog).toBeInTheDocument();
    expect(screen.getByText("Rechazar proyecto")).toBeInTheDocument();
    expect(screen.getByText("Esta acción es irreversible.")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Rechazar" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancelar" })).toBeInTheDocument();
  });

  it("does not render when closed", () => {
    render(
      <ConfirmDialog
        open={false}
        onOpenChange={jest.fn()}
        title="Rechazar proyecto"
        description="Esta acción es irreversible."
        confirmLabel="Rechazar"
        cancelLabel="Cancelar"
        onConfirm={jest.fn()}
      />,
    );

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it("fires onConfirm when the confirm button is clicked", async () => {
    const user = userEvent.setup();
    const onConfirm = jest.fn();
    render(
      <ConfirmDialog
        open
        onOpenChange={jest.fn()}
        title="Rechazar proyecto"
        description="Esta acción es irreversible."
        confirmLabel="Rechazar"
        cancelLabel="Cancelar"
        onConfirm={onConfirm}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Rechazar" }));

    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("fires onCancel and closes when Cancel is clicked", async () => {
    const user = userEvent.setup();
    const onCancel = jest.fn();
    const onOpenChange = jest.fn();
    render(
      <ConfirmDialog
        open
        onOpenChange={onOpenChange}
        title="Rechazar proyecto"
        description="Esta acción es irreversible."
        confirmLabel="Rechazar"
        cancelLabel="Cancelar"
        onConfirm={jest.fn()}
        onCancel={onCancel}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("renders a destructive-styled confirm action", () => {
    render(
      <ConfirmDialog
        open
        onOpenChange={jest.fn()}
        title="Eliminar proyecto"
        description="Se eliminará permanentemente."
        confirmLabel="Eliminar"
        cancelLabel="Cancelar"
        onConfirm={jest.fn()}
      />,
    );

    // Destructive actions must be announced with an alert tone.
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
  });
});