/**
 * Institution detail page — EntityDetail with StatusBadge + FsmActionBar.
 *
 * Spec (institutions-ui RF-F02/RF-F04):
 *   - Detail loads without an active institution.
 *   - FSM actions render for the current role and state.
 */

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

jest.mock("next/navigation", () => ({
  usePathname: () => "/institutions/inst-1",
  useParams: () => ({ id: "inst-1" }),
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
import InstitutionDetailPage from "@/app/institutions/[id]/page";

const institution = {
  id: "inst-1",
  name: "Universidad Nacional",
  code: "UNAL",
  description: "Institución pública.",
  address: "Av. Principal 123",
  contact_email: "contacto@unal.edu",
  contact_phone: "+57 1 5550100",
  logo_url: "",
  status: "active",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-02-01T00:00:00Z",
};

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
      <InstitutionDetailPage />
    </QueryClientProvider>,
  );
}

describe("InstitutionDetailPage", () => {
  it("renders the institution fields and status badge", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(institution);

    renderPage(["superadmin"]);

    expect(
      await screen.findByRole("heading", { name: "Universidad Nacional" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Activa")).toBeInTheDocument();
    expect(screen.getByText("UNAL")).toBeInTheDocument();
    expect(screen.getByText("Institución pública.")).toBeInTheDocument();
    expect(screen.getByText("Av. Principal 123")).toBeInTheDocument();
    expect(screen.getByText("contacto@unal.edu")).toBeInTheDocument();
  });

  it("fetches the detail without the institution header", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(institution);

    renderPage(["superadmin"]);

    await screen.findByRole("heading", { name: "Universidad Nacional" });
    expect(api.api.get).toHaveBeenCalledWith("/api/institutions/inst-1/", {
      sendInstitutionId: false,
    });
  });

  it("renders FSM actions for a superadmin on an active node", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(institution);

    renderPage(["superadmin"]);

    expect(await screen.findByRole("button", { name: /desactivar/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /archivar/i })).toBeInTheDocument();
  });

  it("confirms a destructive FSM action before POSTing", async () => {
    const user = userEvent.setup();
    (api.api.get as jest.Mock).mockResolvedValue(institution);
    (api.api.post as jest.Mock).mockResolvedValue({
      ...institution,
      status: "deactivated",
    });

    renderPage(["superadmin"]);

    await user.click(await screen.findByRole("button", { name: /desactivar/i }));

    const dialog = await screen.findByRole("alertdialog");
    expect(api.api.post).not.toHaveBeenCalled();

    await user.click(within(dialog).getByRole("button", { name: /desactivar/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/institutions/inst-1/deactivate/",
        {},
        { sendInstitutionId: false },
      );
    });
  });

  it("renders an empty state when the institution is not found", async () => {
    (api.api.get as jest.Mock).mockRejectedValue(new Error("Institución no encontrada."));

    renderPage(["superadmin"]);

    expect(await screen.findByText("Institución no encontrada")).toBeInTheDocument();
  });

  it("shows skeletons while loading", () => {
    (api.api.get as jest.Mock).mockReturnValue(new Promise(() => undefined));

    renderPage(["superadmin"]);

    expect(document.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });
});
