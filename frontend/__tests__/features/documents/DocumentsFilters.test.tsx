/**
 * @jest-environment jsdom
 */
import { fireEvent, render, screen } from "@testing-library/react";

jest.mock("@/features/documents/queries", () => ({
  useDocumentTypes: () => ({
    data: [{ code: "acta", name: "Acta de inicio" }],
  }),
}));

import {
  DocumentsFilters,
  type DocumentsFiltersState,
} from "@/features/documents/DocumentsFilters";

function renderFilters(filters: DocumentsFiltersState = {}) {
  const onChange = jest.fn();
  render(<DocumentsFilters filters={filters} onChange={onChange} />);
  return { onChange };
}

/** The selects carry no accessible name, so they are addressed by position. */
const SELECT = { type: 0, entity: 1, signed: 2 } as const;

function choose(select: keyof typeof SELECT, option: string) {
  const trigger = screen.getAllByRole("combobox")[SELECT[select]] as HTMLElement;
  fireEvent.keyDown(trigger, { key: "ArrowDown" });
  fireEvent.keyDown(screen.getByRole("option", { name: option }), {
    key: "Enter",
  });
}

describe("DocumentsFilters", () => {
  it("emits the typed search text, keeping the other filters", () => {
    const { onChange } = renderFilters({ doc_type: "acta" });

    fireEvent.change(screen.getByPlaceholderText("Buscar por nombre..."), {
      target: { value: "informe" },
    });

    expect(onChange).toHaveBeenCalledWith({ doc_type: "acta", search: "informe" });
  });

  it("drops the search filter when the input is emptied", () => {
    const { onChange } = renderFilters({ search: "informe" });

    fireEvent.change(screen.getByPlaceholderText("Buscar por nombre..."), {
      target: { value: "" },
    });

    expect(onChange).toHaveBeenCalledWith({ search: undefined });
  });

  it("emits the selected document type", () => {
    const { onChange } = renderFilters();

    choose("type", "Acta de inicio");

    expect(onChange).toHaveBeenCalledWith({ doc_type: "acta" });
  });

  it("emits the selected entity type", () => {
    const { onChange } = renderFilters();

    choose("entity", "Proyecto");

    expect(onChange).toHaveBeenCalledWith({ entity_type: "project" });
  });

  it.each([
    ["Firmados", true],
    ["Sin firmar", false],
  ])("maps the signed option %s to %s", (option, expected) => {
    const { onChange } = renderFilters();

    choose("signed", option);

    expect(onChange).toHaveBeenCalledWith({ is_signed: expected });
  });

  it("hides the clear button when no filter is active", () => {
    renderFilters();

    expect(screen.queryByRole("button", { name: /limpiar/i })).not.toBeInTheDocument();
  });

  it("clears every filter, including a false signed filter", () => {
    const { onChange } = renderFilters({ is_signed: false });

    fireEvent.click(screen.getByRole("button", { name: /limpiar/i }));

    expect(onChange).toHaveBeenCalledWith({});
  });
});
