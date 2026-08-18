/**
 * Tests for shared Toaster — sonner toast surface wired to theme.
 *
 * Spec (server-state): normalized errors are surfaced to the Toaster.
 */

import { render, screen } from "@testing-library/react";
import { toast } from "sonner";
import { Toaster } from "@/components/shared/Toaster";

describe("Toaster", () => {
  it("renders error toast notifications with Spanish copy", async () => {
    render(<Toaster />);

    toast.error("No se pudo aprobar el proyecto.");

    expect(
      await screen.findByText("No se pudo aprobar el proyecto."),
    ).toBeInTheDocument();
  });

  it("renders success toasts too", async () => {
    render(<Toaster />);

    toast.success("Proyecto aprobado.");

    expect(await screen.findByText("Proyecto aprobado.")).toBeInTheDocument();
  });
});