/**
 * ResearcherList — paginated researchers table.
 *
 * Spec (researchers-ui list): rows render with completeness bars, status
 * badges, row actions (view/edit), and pagination controls; an empty
 * state with a create action renders when there are no researchers.
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ResearcherList } from "@/features/researchers/ResearcherList";
import type { ResearcherList as ResearcherListRow } from "@/features/researchers/types";

jest.mock("next/link", () => {
  return {
    __esModule: true,
    default: ({ href, children }: { href: string; children: React.ReactNode }) => (
      <a href={href}>{children}</a>
    ),
  };
});

const rows: ResearcherListRow[] = [
  {
    id: "r-1",
    full_name: "Ana Pérez",
    institution: "inst-1",
    is_active: true,
    completeness_score: 100,
  },
  {
    id: "r-2",
    full_name: "Luis Gómez",
    institution: "inst-1",
    is_active: false,
    completeness_score: 40,
  },
];

function renderList(overrides: Partial<Parameters<typeof ResearcherList>[0]> = {}) {
  return render(
    <ResearcherList
      researchers={rows}
      loading={false}
      page={1}
      count={2}
      hasNext={false}
      hasPrevious={false}
      onPageChange={jest.fn()}
      {...overrides}
    />,
  );
}

describe("ResearcherList", () => {
  it("renders researcher rows with name, badge and completeness", () => {
    renderList();

    expect(screen.getByText("Ana Pérez")).toBeInTheDocument();
    expect(screen.getByText("Luis Gómez")).toBeInTheDocument();
    // Active researcher shows the shared active badge label.
    expect(screen.getByText("Activa")).toBeInTheDocument();
    // Inactive researcher shows the distinct inactive label.
    expect(screen.getByText("Inactivo")).toBeInTheDocument();
    // Completeness bars render with the score percentage.
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(screen.getByText("40%")).toBeInTheDocument();
  });

  it("links each row to its detail route", () => {
    renderList();

    expect(screen.getByRole("link", { name: "Ana Pérez" })).toHaveAttribute(
      "href",
      "/researchers/r-1",
    );
    expect(screen.getByRole("link", { name: "Luis Gómez" })).toHaveAttribute(
      "href",
      "/researchers/r-2",
    );
  });

  it("shows the edit action per row", () => {
    renderList();

    const editLinks = screen.getAllByRole("link", { name: "Editar" });
    expect(editLinks).toHaveLength(2);
    expect(editLinks[0]).toHaveAttribute("href", "/researchers/r-1/edit");
    expect(editLinks[1]).toHaveAttribute("href", "/researchers/r-2/edit");
  });

  it("renders pagination controls and count", () => {
    renderList();

    expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Siguiente" })).toBeDisabled();
    expect(screen.getByText(/2 investigadores/)).toBeInTheDocument();
  });

  it("calls onPageChange when advancing a page", async () => {
    const user = userEvent.setup();
    const onPageChange = jest.fn();
    renderList({ page: 2, hasPrevious: true, hasNext: true, onPageChange });

    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    expect(onPageChange).toHaveBeenCalledWith(3);
    await user.click(screen.getByRole("button", { name: "Anterior" }));
    expect(onPageChange).toHaveBeenCalledWith(1);
  });

  it("renders an empty state when there are no researchers", () => {
    renderList({ researchers: [], count: 0 });

    expect(screen.getByText("No hay investigadores")).toBeInTheDocument();
  });
});
