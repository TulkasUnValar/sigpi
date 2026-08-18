/**
 * React 19 compatibility spike + shadcn primitive contract tests.
 *
 * Spec (ui-foundation):
 *   GIVEN a fresh shadcn/ui install
 *   WHEN a Button/Input/Dialog is rendered
 *   THEN it is keyboard-focusable and exposes ARIA roles
 *
 *   GIVEN slice-1 spike
 *   WHEN any shadcn component mounts
 *   THEN no React 19 peer-dependency error is thrown
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

describe("Button", () => {
  it("renders as a keyboard-focusable button with an accessible role", () => {
    render(<Button>Guardar</Button>);

    const button = screen.getByRole("button", { name: "Guardar" });
    expect(button).toBeInTheDocument();
    button.focus();
    expect(button).toHaveFocus();
  });

  it("accepts a click handler and fires it", async () => {
    const user = userEvent.setup();
    const onClick = jest.fn();
    render(<Button onClick={onClick}>Aprobar</Button>);

    await user.click(screen.getByRole("button", { name: "Aprobar" }));

    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

describe("Dialog", () => {
  it("exposes role=dialog and stays closed until triggered", async () => {
    const user = userEvent.setup();
    render(
      <Dialog>
        <DialogTrigger asChild>
          <Button>Rechazar</Button>
        </DialogTrigger>
        <DialogContent>
          <DialogTitle>Confirmar rechazo</DialogTitle>
        </DialogContent>
      </Dialog>,
    );

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Rechazar" }));

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(screen.getByText("Confirmar rechazo")).toBeInTheDocument();
  });

  it("closes on Escape — keyboard accessible", async () => {
    const user = userEvent.setup();
    render(
      <Dialog>
        <DialogTrigger asChild>
          <Button>Rechazar</Button>
        </DialogTrigger>
        <DialogContent>
          <DialogTitle>Confirmar rechazo</DialogTitle>
        </DialogContent>
      </Dialog>,
    );

    await user.click(screen.getByRole("button", { name: "Rechazar" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    await user.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});