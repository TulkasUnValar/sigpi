/**
 * Institution edit page — EntityForm prefilled from the detail, PATCH on
 * submit, redirect back to the detail.
 *
 * Spec (institutions-ui RF-F02):
 *   - PATCH /api/institutions/{id}/ updates the root institution.
 *   - 400 field errors map back into the form.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

const mockPush = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => "/institutions/inst-1/edit",
  useParams: () => ({ id: "inst-1" }),
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
import { ApiError } from "@/lib/errors";
import EditInstitutionPage from "@/app/institutions/[id]/edit/page";

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
      <EditInstitutionPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe("EditInstitutionPage", () => {
  it("prefills the form from the detail", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(institution);

    renderPage(["superadmin"]);

    expect(await screen.findByRole("heading", { name: "Editar institución" })).toBeInTheDocument();
    expect(screen.getByLabelText("Nombre")).toHaveValue("Universidad Nacional");
    expect(screen.getByLabelText("Código")).toHaveValue("UNAL");
    expect(screen.getByLabelText("Dirección")).toHaveValue("Av. Principal 123");
  });

  it("PATCHes the payload and redirects to the detail on success", async () => {
    const user = userEvent.setup();
    (api.api.get as jest.Mock).mockResolvedValue(institution);
    (api.api.patch as jest.Mock).mockResolvedValue({
      ...institution,
      name: "Universidad Nacional Actualizada",
    });

    renderPage(["superadmin"]);

    const nameInput = await screen.findByLabelText("Nombre");
    await user.clear(nameInput);
    await user.type(nameInput, "Universidad Nacional Actualizada");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/institutions/inst-1/",
        expect.objectContaining({ name: "Universidad Nacional Actualizada" }),
        { sendInstitutionId: false },
      );
    });
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/institutions/inst-1");
    });
  });

  it("maps 400 field errors back into the form", async () => {
    const user = userEvent.setup();
    (api.api.get as jest.Mock).mockResolvedValue(institution);
    (api.api.patch as jest.Mock).mockRejectedValue(
      new ApiError("Código inválido.", 400, {
        code: ["Ya existe una institución con este código."],
      }),
    );

    renderPage(["superadmin"]);

    const codeInput = await screen.findByLabelText("Código");
    await user.clear(codeInput);
    await user.type(codeInput, "DUP");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    expect(
      await screen.findByText("Ya existe una institución con este código."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Código")).toHaveValue("DUP");
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("renders an empty state when the institution is not found", async () => {
    (api.api.get as jest.Mock).mockRejectedValue(new Error("Institución no encontrada."));

    renderPage(["superadmin"]);

    expect(await screen.findByText("Institución no encontrada")).toBeInTheDocument();
  });
});
