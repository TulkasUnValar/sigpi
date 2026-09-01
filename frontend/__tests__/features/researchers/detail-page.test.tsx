/**
 * Researcher detail page — header, status, completeness, four tabs,
 * edit/deactivate controls.
 *
 * Spec (researchers-ui detail): /researchers/{id} renders tabs Overview,
 * Affiliations, External profiles, Attachments; Overview shows profile
 * fields, the is_active badge, and the completeness bar.
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

jest.mock("next/navigation", () => ({
  usePathname: () => "/researchers/r-1",
  useParams: () => ({ id: "r-1" }),
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

jest.mock("sonner", () => ({
  toast: { success: jest.fn(), error: jest.fn() },
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
import ResearcherDetailPage from "@/app/researchers/[id]/page";

const detail = {
  id: "r-1",
  user: "u-1",
  institution: "inst-1",
  first_name: "Ana",
  last_name: "Pérez",
  document_type: "CC",
  document_number: "1234567890",
  primary_email: "ana@example.com",
  phone: "+57 300 1234567",
  bio: "Investigadora principal.",
  academic_formation: "Doctorado en Ciencias",
  is_active: true,
  full_name: "Ana Pérez",
  completeness_score: 100,
  affiliations: [],
  external_profiles: [],
  attachments: [],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
};

function makeUser(userId: string | null) {
  if (!userId) return null;
  return {
    id: userId,
    email: "user@example.com",
    auth_source: "local",
    is_superuser: false,
    is_active: true,
    active_institution_id: "inst-1",
    active_role: "admin",
    memberships: [],
  };
}

function renderPage(roles: string[], userId: string | null = "u-1") {
  useAuthStore.setState({
    user: makeUser(userId),
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
      <ResearcherDetailPage />
    </QueryClientProvider>,
  );
}

describe("ResearcherDetailPage", () => {
  it("renders the header, status, completeness and the four tabs", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(detail);

    renderPage(["admin"]);

    expect(await screen.findByRole("heading", { name: "Ana Pérez" })).toBeInTheDocument();
    expect(screen.getByText("Activa")).toBeInTheDocument();
    expect(screen.getByText("Completo")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Resumen" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Afiliaciones" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Perfiles externos" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Adjuntos" })).toBeInTheDocument();
  });

  it("shows the Overview profile fields by default", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(detail);

    renderPage(["admin"]);

    expect(await screen.findByText("ana@example.com")).toBeInTheDocument();
    expect(screen.getByText("1234567890")).toBeInTheDocument();
  });

  it("shows an edit control for admin+", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(detail);

    renderPage(["admin"]);

    expect(await screen.findByRole("link", { name: "Editar" })).toHaveAttribute(
      "href",
      "/researchers/r-1/edit",
    );
  });

  it("shows the deactivate control for admin+ on an active researcher", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(detail);

    renderPage(["admin"]);

    expect(await screen.findByRole("button", { name: /desactivar/i })).toBeInTheDocument();
  });

  it("hides edit and deactivate for a non-linked director", async () => {
    (api.api.get as jest.Mock).mockResolvedValue({ ...detail, user: "u-2" });

    renderPage(["director"], "u-1");

    expect(await screen.findByRole("heading", { name: "Ana Pérez" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Editar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /desactivar/i })).not.toBeInTheDocument();
  });

  it("renders an empty state when the researcher is not found", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(undefined);

    renderPage(["admin"]);

    expect(await screen.findByText("Investigador no encontrado")).toBeInTheDocument();
  });

  it("wires the nested managers into the Affiliations and Profiles tabs", async () => {
    (api.api.get as jest.Mock).mockImplementation((url: string) => {
      if (url.startsWith("/api/researchers/r-1/affiliations")) {
        return Promise.resolve({ count: 0, next: null, previous: null, results: [] });
      }
      if (url.startsWith("/api/researchers/r-1/profiles")) {
        return Promise.resolve({ count: 0, next: null, previous: null, results: [] });
      }
      if (url.startsWith("/api/researchers/r-1/attachments")) {
        return Promise.resolve({ count: 0, next: null, previous: null, results: [] });
      }
      return Promise.resolve(detail);
    });

    renderPage(["admin"]);
    await screen.findByRole("heading", { name: "Ana Pérez" });

    await userEvent.click(screen.getByRole("tab", { name: "Afiliaciones" }));
    expect(await screen.findByText("Nueva afiliación")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("tab", { name: "Perfiles externos" }));
    expect(await screen.findByText("Nuevo perfil externo")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("tab", { name: "Adjuntos" }));
    expect(await screen.findByText("Nuevo adjunto")).toBeInTheDocument();
  });
});
