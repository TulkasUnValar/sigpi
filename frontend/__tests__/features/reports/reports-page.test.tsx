/**
 * Reports page — protected /reports entry point.
 *
 * Spec (frontend-reports RF-001):
 *   - GIVEN an authenticated user with CanGenerateReport
 *   - THEN /reports renders the hub inside the authenticated shell.
 *   - GIVEN a user without CanGenerateReport
 *   - THEN access is denied with NO API calls (role-gated at the page).
 */

import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

const mockUsePathname = jest.fn(() => "/reports");

jest.mock("next/navigation", () => ({
  usePathname: () => mockUsePathname(),
  useRouter: () => ({ push: jest.fn(), replace: jest.fn(), prefetch: jest.fn() }),
}));

jest.mock("next/link", () => {
  return {
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
  };
});

jest.mock("next-themes", () => ({
  useTheme: () => ({ theme: "light", setTheme: jest.fn(), themes: ["light", "dark"] }),
}));

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

import * as api from "@/lib/api";
import ReportsPage from "@/app/reports/page";

function setAuth(roles: string[]) {
  useAuthStore.setState({
    roles,
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <ReportsPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  mockUsePathname.mockReturnValue("/reports");
  useAuthStore.setState({
    roles: [],
    isAuthenticated: false,
    isLoading: false,
    activeInstitution: null,
    institutions: [],
  });
});

describe("/reports page", () => {
  it("renders the hub inside the authenticated shell for an allowed role", async () => {
    setAuth(["director_centro"]);
    (api.api.get as jest.Mock).mockImplementation((path: string) => {
      if (path.includes("/api/projects/"))
        return Promise.resolve({ count: 1, next: null, previous: null, results: [] });
      if (path.includes("/api/researchers/"))
        return Promise.resolve({ count: 0, next: null, previous: null, results: [] });
      if (path.includes("/api/institutions/") && path.includes("/centers/"))
        return Promise.resolve([]);
      return Promise.resolve({ count: 0, next: null, previous: null, results: [] });
    });

    renderPage();

    expect(await screen.findByRole("heading", { name: "Informes" })).toBeInTheDocument();
    // The authenticated shell is present (sidebar navigation).
    expect(screen.getByRole("link", { name: "Proyectos" })).toBeInTheDocument();
  });

  it("denies access with an alert and NO api calls for a non-allowed role", async () => {
    setAuth(["researcher"]);
    renderPage();

    expect(
      await screen.findByText("No tiene permisos para generar informes."),
    ).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/permisos/i);
    expect(api.api.get).not.toHaveBeenCalled();
    expect(api.api.post).not.toHaveBeenCalled();
  });
});
