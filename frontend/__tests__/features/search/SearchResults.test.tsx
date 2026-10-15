/**
 * SearchResults — paginated results with highlighting.
 *
 * Tests:
 * - Renders result list with hits
 * - Displays highlighting from _formatted fields
 * - Shows "no results" empty state
 * - Pagination controls work correctly
 * - Links to detail pages
 */

import { fireEvent, render, screen } from "@testing-library/react";
import type { SearchResults as SearchResultsModel } from "@/features/search/types";

jest.mock("next/link", () => ({
  __esModule: true,
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string | { pathname: string };
    children: React.ReactNode;
  }) => (
    <a href={typeof href === "string" ? href : href.pathname} {...rest}>
      {children}
    </a>
  ),
}));

import { SearchResults } from "@/features/search/SearchResults";

const mockOnPageChange = jest.fn();

describe("SearchResults", () => {
  beforeEach(() => {
    mockOnPageChange.mockClear();
  });

  it("returns null when results is undefined", () => {
    const { container } = render(
      <SearchResults results={undefined} offset={0} limit={25} onPageChange={mockOnPageChange} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders empty state when no hits", () => {
    const results: SearchResultsModel = {
      hits: [],
      query: "test",
      processingTimeMs: 10,
      estimatedTotalHits: 0,
      offset: 0,
      limit: 25,
    };

    render(
      <SearchResults results={results} offset={0} limit={25} onPageChange={mockOnPageChange} />,
    );

    expect(screen.getByText(/No se encontraron resultados para/)).toBeInTheDocument();
    expect(screen.queryByTestId("search-prev")).not.toBeInTheDocument();
    expect(screen.queryByTestId("search-next")).not.toBeInTheDocument();
  });

  it("renders hit list with titles", () => {
    const results: SearchResultsModel = {
      hits: [
        { id: "1", title: "Project Alpha", description: "First project" },
        { id: "2", title: "Project Beta", description: "Second project" },
      ],
      query: "project",
      processingTimeMs: 5,
      estimatedTotalHits: 2,
      offset: 0,
      limit: 25,
    };

    render(
      <SearchResults results={results} offset={0} limit={25} onPageChange={mockOnPageChange} />,
    );

    expect(screen.getByText(/resultados para/)).toBeInTheDocument();
    expect(screen.getAllByText(/project/i)).toHaveLength(5); // query text + 2 titles + 2 descriptions
    expect(screen.getAllByTestId("search-hit")).toHaveLength(2);
  });

  it("renders highlighting from _formatted fields", () => {
    const results: SearchResultsModel = {
      hits: [
        {
          id: "1",
          title: "Project Alpha",
          description: "A great project about AI",
          _formatted: {
            title: "<mark>Project</mark> Alpha",
            description: "A great project about <mark>AI</mark>",
          },
        },
      ],
      query: "project AI",
      processingTimeMs: 5,
      estimatedTotalHits: 1,
      offset: 0,
      limit: 25,
    };

    const { container } = render(
      <SearchResults results={results} offset={0} limit={25} onPageChange={mockOnPageChange} />,
    );

    // Highlighted HTML should be rendered
    const markElements = container.querySelectorAll("mark");
    expect(markElements.length).toBeGreaterThan(0);
  });

  it("falls back to name when title is missing", () => {
    const results: SearchResultsModel = {
      hits: [{ id: "1", name: "Researcher Name", description: "Bio" }],
      query: "researcher",
      processingTimeMs: 5,
      estimatedTotalHits: 1,
      offset: 0,
      limit: 25,
    };

    render(
      <SearchResults results={results} offset={0} limit={25} onPageChange={mockOnPageChange} />,
    );

    expect(screen.getByText("Researcher Name")).toBeInTheDocument();
  });

  it("shows pagination controls when results exceed limit", () => {
    const results: SearchResultsModel = {
      hits: [{ id: "1", title: "Project" }],
      query: "project",
      processingTimeMs: 5,
      estimatedTotalHits: 50,
      offset: 0,
      limit: 25,
    };

    render(
      <SearchResults results={results} offset={0} limit={25} onPageChange={mockOnPageChange} />,
    );

    expect(screen.getByTestId("search-next")).toBeInTheDocument();
    expect(screen.getByTestId("search-prev")).toBeDisabled();
    expect(screen.getByText("1–25 de 50")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("search-next"));
    expect(mockOnPageChange).toHaveBeenCalledWith(25);
  });

  it("enables previous button when offset > 0", () => {
    const results: SearchResultsModel = {
      hits: [{ id: "1", title: "Project" }],
      query: "project",
      processingTimeMs: 5,
      estimatedTotalHits: 50,
      offset: 25,
      limit: 25,
    };

    render(
      <SearchResults results={results} offset={25} limit={25} onPageChange={mockOnPageChange} />,
    );

    expect(screen.getByTestId("search-prev")).not.toBeDisabled();
    expect(screen.getByText("26–50 de 50")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("search-prev"));
    expect(mockOnPageChange).toHaveBeenCalledWith(0);
  });

  it("disables next button on last page", () => {
    const results: SearchResultsModel = {
      hits: [{ id: "1", title: "Project" }],
      query: "project",
      processingTimeMs: 5,
      estimatedTotalHits: 25,
      offset: 0,
      limit: 25,
    };

    render(
      <SearchResults results={results} offset={0} limit={25} onPageChange={mockOnPageChange} />,
    );

    expect(screen.getByTestId("search-next")).toBeDisabled();
  });

  it("links to detail pages", () => {
    const results: SearchResultsModel = {
      hits: [
        { id: "proj-1", title: "Project", _index: "projects" },
        { id: "res-1", title: "Researcher", _index: "researchers" },
      ],
      query: "test",
      processingTimeMs: 5,
      estimatedTotalHits: 2,
      offset: 0,
      limit: 25,
    };

    render(
      <SearchResults results={results} offset={0} limit={25} onPageChange={mockOnPageChange} />,
    );

    const links = screen.getAllByTestId("search-hit");
    expect(links[0].getAttribute("href")).toBe("/projects/proj-1");
    expect(links[1].getAttribute("href")).toBe("/researchers/res-1");
  });
});
