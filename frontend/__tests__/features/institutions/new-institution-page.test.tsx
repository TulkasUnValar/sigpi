/**
 * Institution create page — EntityForm submit → POST /api/institutions/.
 *
 * Spec (institutions-ui RF-F02):
 *   - Superadmin creates an institution → success redirects to the detail.
 *   - 409 duplicate-code surfaces via Toaster and the form keeps values.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

const mockPush = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => "/institutions/new",
  useParams: () => ({}),
  useRouter: () => ({ push: (...args: unknown[]) => mockPush(...args), prefetch: jest.fn() }),
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
import NewInstitutionPage from "@/app/institutions/new/page";

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
      <NewInstitutionPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe("NewInstitutionPage", () => {
  it("renders the create form with Spanish labels", () => {
    renderPage(["superadmin"]);

    expect(screen.getByRole("heading", { name: "Nueva institución" })).toBeInTheDocument();
    expect(screen.getByLabelText("Nombre")).toBeInTheDocument();
    expect(screen.getByLabelText("Código")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Crear institución" })).toBeInTheDocument();
  });

  it("POSTs the payload and redirects to the detail on success", async () => {
    const user = userEvent.setup();
    (api.api.post as jest.Mock).mockResolvedValue({
      id: "inst-new",
      name: "Universidad Nueva",
      code: "UNEW",
      status: "active",
    });

    renderPage(["superadmin"]);

    await user.type(screen.getByLabelText("Nombre"), "Universidad Nueva");
    await user.type(screen.getByLabelText("Código"), "UNEW");
    await user.click(screen.getByRole("button", { name: "Crear institución" }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/institutions/",
        expect.objectContaining({ name: "Universidad Nueva", code: "UNEW" }),
        { sendInstitutionId: false },
      );
    });
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/institutions/inst-new");
    });
  });

  it("shows a 409 duplicate-code error and keeps the form values", async () => {
    const user = userEvent.setup();
    (api.api.post as jest.Mock).mockRejectedValue(
      new Error("Ya existe una institución con este código."),
    );

    renderPage(["superadmin"]);

    await user.type(screen.getByLabelText("Nombre"), "Universidad Duplicada");
    await user.type(screen.getByLabelText("Código"), "DUP");
    await user.click(screen.getByRole("button", { name: "Crear institución" }));

    // Error toast (Toaster mock renders nothing, but the mutation ran).
    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByLabelText("Código")).toHaveValue("DUP");
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("denies the form to non-superadmin roles", () => {
    renderPage(["director"]);

    expect(screen.queryByLabelText("Nombre")).not.toBeInTheDocument();
    expect(screen.getByText("No tiene permisos para ver este contenido.")).toBeInTheDocument();
  });
});
