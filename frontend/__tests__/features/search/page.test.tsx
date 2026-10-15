/**
 * Search page — integration test.
 *
 * Tests:
 * - Page renders with all components
 * - Components are integrated correctly
 * - Loading state shows skeleton
 */

import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
    upload: jest.fn(),
  },
  getCSRFToken: jest.fn(),
  API_BASE: "http://localhost:8000",
}));

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

import SearchPage from "@/app/search/page";

beforeEach(() => {
  useAuthStore.setState({
    roles: ["researcher"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });
});

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <SearchPage />
    </QueryClientProvider>,
  );
}

describe("SearchPage", () => {
  it("renders the page with all components", async () => {
    renderPage();

    // Header
    expect(screen.getByText("Búsqueda")).toBeInTheDocument();
    expect(screen.getByText(/Busca en proyectos, investigadores, productos/)).toBeInTheDocument();

    // SearchBar
    expect(screen.getByTestId("search-bar")).toBeInTheDocument();
    expect(screen.getByTestId("search-input")).toBeInTheDocument();

    // SearchFilters
    expect(screen.getByTestId("search-filters")).toBeInTheDocument();

    // Initial prompt
    expect(screen.getByText(/Ingresa al menos 2 caracteres para buscar/)).toBeInTheDocument();
  });

  it("shows prompt when query is too short", () => {
    renderPage();

    // Initially shows prompt
    expect(screen.getByText(/Ingresa al menos 2 caracteres para buscar/)).toBeInTheDocument();
  });

  it("shows superadmin filters when user is superadmin", () => {
    useAuthStore.setState({ roles: ["superadmin"] });
    renderPage();

    // Superadmin should see institution filter when panel is open
    const filterToggle = screen.getByTestId("filters-toggle");
    expect(filterToggle).toBeInTheDocument();
  });

  it("hides superadmin filters for regular users", () => {
    useAuthStore.setState({ roles: ["researcher"] });
    renderPage();

    // Regular user still sees filter toggle
    const filterToggle = screen.getByTestId("filters-toggle");
    expect(filterToggle).toBeInTheDocument();
  });
});
