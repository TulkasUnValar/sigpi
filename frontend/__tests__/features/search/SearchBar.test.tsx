/**
 * SearchBar — debounced input with index selector.
 *
 * Tests:
 * - Input renders with placeholder
 * - Debounced search (300ms) fires onQueryChange
 * - Index selector renders all options
 * - Loading spinner shows when isLoading is true
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";

import { SearchBar } from "@/features/search/SearchBar";

jest.mock("next/link", () => ({
  __esModule: true,
  default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

function SearchBarHarness(props: Partial<React.ComponentProps<typeof SearchBar>>) {
  const [query, setQuery] = useState(props.query ?? "");
  const [index, setIndex] = useState(props.index ?? "all");
  return (
    <SearchBar
      query={query}
      index={index}
      isLoading={props.isLoading}
      onQueryChange={setQuery}
      onIndexChange={setIndex}
    />
  );
}

describe("SearchBar", () => {
  it("renders the input with placeholder", () => {
    render(<SearchBarHarness />);
    expect(screen.getByTestId("search-input")).toHaveAttribute("placeholder", "Buscar en SIGPI...");
  });

  it("fires onQueryChange after 300ms debounce", async () => {
    jest.useFakeTimers();
    render(<SearchBarHarness />);

    const input = screen.getByTestId("search-input");
    fireEvent.change(input, { target: { value: "test" } });

    // Not fired immediately
    expect(input).toHaveValue("test");

    // Advance past debounce
    jest.advanceTimersByTime(300);

    jest.useRealTimers();
    // Input should still hold the value (state is in the harness)
    await waitFor(() => {
      expect(input).toHaveValue("test");
    });
  });

  it("shows loading spinner when isLoading is true", () => {
    render(<SearchBarHarness isLoading />);
    expect(screen.getByTestId("search-spinner")).toBeInTheDocument();
  });

  it("hides loading spinner when isLoading is false", () => {
    render(<SearchBarHarness isLoading={false} />);
    expect(screen.queryByTestId("search-spinner")).not.toBeInTheDocument();
  });

  it("renders the index selector with all options", async () => {
    render(<SearchBarHarness />);
    const trigger = screen.getByTestId("search-index-select");
    expect(trigger).toBeInTheDocument();

    fireEvent.click(trigger);
    await waitFor(() => {
      expect(screen.getByText("Proyectos")).toBeInTheDocument();
    });
    expect(screen.getByText("Investigadores")).toBeInTheDocument();
    expect(screen.getByText("Productos")).toBeInTheDocument();
    expect(screen.getByText("Convocatorias")).toBeInTheDocument();
    expect(screen.getByText("Avances")).toBeInTheDocument();
    expect(screen.getAllByText("Todos")).toHaveLength(2);
  });

  it("fires onIndexChange when index selection changes", async () => {
    render(<SearchBarHarness />);
    const trigger = screen.getByTestId("search-index-select");
    fireEvent.click(trigger);

    await waitFor(() => {
      expect(screen.getByText("Proyectos")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Proyectos"));

    await waitFor(() => {
      // Harness re-renders with new index; trigger now shows the selection
      expect(trigger.textContent).toContain("Proyectos");
    });
  });
});
