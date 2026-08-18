/**
 * Tests for shared EmptyState — empty-data placeholder.
 */

import { render, screen } from "@testing-library/react";
import { FolderOpen } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";

describe("EmptyState", () => {
  it("renders title and description", () => {
    render(
      <EmptyState
        title="Sin proyectos"
        description="No hay proyectos para mostrar en esta institución."
      />,
    );

    expect(screen.getByText("Sin proyectos")).toBeInTheDocument();
    expect(
      screen.getByText("No hay proyectos para mostrar en esta institución."),
    ).toBeInTheDocument();
  });

  it("renders the provided icon", () => {
    render(
      <EmptyState
        title="Sin avances"
        description="Este proyecto aún no tiene avances."
        icon={FolderOpen}
      />,
    );

    expect(screen.getByLabelText("Sin avances")).toBeInTheDocument();
  });

  it("renders a custom action node", () => {
    render(
      <EmptyState
        title="Sin avances"
        description="Este proyecto aún no tiene avances."
        action={<button>Crear avance</button>}
      />,
    );

    expect(
      screen.getByRole("button", { name: "Crear avance" }),
    ).toBeInTheDocument();
  });
});