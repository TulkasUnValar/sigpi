/**
 * Institutions list page — tree rendering, EmptyState bootstrap, and
 * role-gated create CTA.
 *
 * Spec (institutions-ui RF-F01/RF-F02):
 *   - Root institutions render as a tree.
 *   - Zero institutions → EmptyState with create CTA; no activeInstitution
 *     is required.
 */

import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

jest.mock("next/navigation", () => ({
  usePathname: () => "/institutions",
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
import InstitutionsPage from "@/app/institutions/page";

const institutionRows = [
  {
    id: "inst-1",
    name: "Universidad Nacional",
    code: "UNAL",
    description: "",
    address: "",
    contact_email: "",
    contact_phone: "",
    logo_url: "",
    status: "active",
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "inst-2",
    name: "Universidad del Valle",
    code: "UVAL",
    description: "",
    address: "",
    contact_email: "",
    contact_phone: "",
    logo_url: "",
    status: "deactivated",
    is_active: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

function renderPage(roles: string[]) {
  useAuthStore.setState({
    roles,
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: null,
    institutions: [],
    centers: [],
  });

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <InstitutionsPage />
    </QueryClientProvider>,
  );
}

describe("InstitutionsPage — list", () => {
  it("loads without an active institution and renders the tree", async () => {
    (api.api.get as jest.Mock).mockResolvedValue({
      count: 2,
      next: null,
      previous: null,
      results: institutionRows,
    });

    renderPage(["superadmin"]);

    expect(
      await screen.findByRole("tree", { name: "Estructura institucional" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Universidad Nacional")).toBeInTheDocument();
    expect(screen.getByText("Universidad del Valle")).toBeInTheDocument();
    expect(screen.getByText("Activa")).toBeInTheDocument();
    expect(screen.getByText("Desactivada")).toBeInTheDocument();
  });

  it("renders the empty state with a create CTA when there are no institutions", async () => {
    (api.api.get as jest.Mock).mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });

    renderPage(["superadmin"]);

    expect(await screen.findByText("No hay instituciones")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Crear institución" })).toHaveAttribute(
      "href",
      "/institutions/new",
    );
  });

  it("hides the create CTA for non-superadmin roles", async () => {
    (api.api.get as jest.Mock).mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });

    renderPage(["director"]);

    expect(await screen.findByText("No hay instituciones")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Crear institución" })).not.toBeInTheDocument();
    expect(
      screen.getAllByText("No tiene permisos para ver este contenido.").length,
    ).toBeGreaterThan(0);
  });

  it("shows skeletons while loading", () => {
    (api.api.get as jest.Mock).mockReturnValue(new Promise(() => undefined));

    renderPage(["superadmin"]);

    expect(screen.getByRole("heading", { name: "Estructura institucional" })).toBeInTheDocument();
    expect(document.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });
});
