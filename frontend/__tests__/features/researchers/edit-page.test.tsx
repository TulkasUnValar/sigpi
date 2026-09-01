/**
 * Edit researcher page — PATCH with is_active reactivation toggle.
 *
 * Spec (researchers-ui edit): PATCH /api/researchers/{id}/ is allowed for
 * self (linked user) or admin+ (gated on detail.user); the is_active
 * toggle enables reactivation (no reactivate endpoint exists).
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

const mockPush = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => "/researchers/r-1/edit",
  useParams: () => ({ id: "r-1" }),
  useRouter: () => ({ push: mockPush, prefetch: jest.fn() }),
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
import EditResearcherPage from "@/app/researchers/[id]/edit/page";

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
  bio: "Bio.",
  academic_formation: "Doctorado",
  is_active: false,
  full_name: "Ana Pérez",
  completeness_score: 40,
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
      <EditResearcherPage />
    </QueryClientProvider>,
  );
}

describe("EditResearcherPage", () => {
  beforeEach(() => {
    mockPush.mockClear();
  });

  it("prefills the form from the detail for admin+", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(detail);

    renderPage(["admin"]);

    expect(await screen.findByRole("heading", { name: "Editar investigador" })).toBeInTheDocument();
    expect(screen.getByLabelText("Primer nombre")).toHaveValue("Ana");
    expect(screen.getByLabelText("Número de documento")).toHaveValue("1234567890");
  });

  it("allows the linked self to edit", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(detail);

    renderPage(["researcher"], "u-1");

    expect(await screen.findByRole("button", { name: "Guardar cambios" })).toBeInTheDocument();
  });

  it("blocks a non-linked director", async () => {
    (api.api.get as jest.Mock).mockResolvedValue({ ...detail, user: "u-2" });

    renderPage(["director"], "u-1");

    expect(
      await screen.findByText("No tiene permisos para editar este investigador."),
    ).toBeInTheDocument();
  });

  it("PATCHes with is_active true to reactivate and redirects", async () => {
    const user = userEvent.setup();
    (api.api.get as jest.Mock).mockResolvedValue(detail);
    (api.api.patch as jest.Mock).mockResolvedValue({ ...detail, is_active: true });

    renderPage(["admin"]);
    await screen.findByRole("button", { name: "Guardar cambios" });

    await user.click(screen.getByRole("switch"));
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/researchers/r-1/",
        expect.objectContaining({ is_active: true }),
        { institutionId: "inst-1" },
      );
    });
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/researchers/r-1");
    });
  });
});
