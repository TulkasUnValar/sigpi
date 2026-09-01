/**
 * Researchers list page — paginated table with role-gated create CTA.
 *
 * Spec (researchers-ui list): /researchers renders the paginated list
 * (25/page) with completeness bars, status badges, and an empty state
 * with a create action (director+, level ≤ 3).
 */

import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

jest.mock("next/navigation", () => ({
  usePathname: () => "/researchers",
  useParams: () => ({}),
  useRouter: () => ({ push: jest.fn(), prefetch: jest.fn() }),
}));

jest.mock("next/link", () => {
  return {
    __esModule: true,
    default: ({ href, children }: { href: string; children: React.ReactNode }) => (
      <a href={href}>{children}</a>
    ),
  };
});

jest.mock("next-themes", () => ({
  useTheme: () => ({ theme: "light", setTheme: jest.fn(), themes: [] }),
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
import ResearchersPage from "@/app/researchers/page";

const rows = [
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

function pageOf<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results };
}

function renderPage(roles: string[]) {
  useAuthStore.setState({
    roles,
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ResearchersPage />
    </QueryClientProvider>,
  );
}

describe("ResearchersPage — list", () => {
  it("renders the paginated list with researchers", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf(rows));

    renderPage(["admin"]);

    expect(await screen.findByText("Ana Pérez")).toBeInTheDocument();
    expect(screen.getByText("Luis Gómez")).toBeInTheDocument();
    expect(screen.getByText("Inactivo")).toBeInTheDocument();
    expect(screen.getByText(/2 investigadores/)).toBeInTheDocument();
  });

  it("renders an empty state with a create CTA for director+", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));

    renderPage(["director"]);

    expect(await screen.findByText("No hay investigadores")).toBeInTheDocument();
    const createLinks = screen.getAllByRole("link", { name: "Crear investigador" });
    expect(createLinks.length).toBeGreaterThan(0);
    expect(createLinks[0]).toHaveAttribute("href", "/researchers/new");
  });

  it("hides the create CTA for the researcher role (level 4)", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));

    renderPage(["researcher"]);

    expect(await screen.findByText("No hay investigadores")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Crear investigador" })).not.toBeInTheDocument();
  });

  it("shows skeletons while loading", () => {
    (api.api.get as jest.Mock).mockReturnValue(new Promise(() => undefined));

    renderPage(["admin"]);

    expect(screen.getByRole("heading", { name: "Investigadores" })).toBeInTheDocument();
    expect(document.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });

  it("announces the loading state to assistive technology", () => {
    (api.api.get as jest.Mock).mockReturnValue(new Promise(() => undefined));

    renderPage(["admin"]);

    expect(screen.getByRole("status", { name: /cargando investigadores/i })).toBeInTheDocument();
  });
});
