/**
 * New researcher page — role-gated create form.
 *
 * Spec (researchers-ui create): director+ (level ≤ 3) can POST
 * /api/researchers/; success redirects to /researchers/{id}; a duplicate
 * document 400 surfaces as a field error and does not redirect.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";
import { ApiError } from "@/lib/errors";

const mockPush = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => "/researchers/new",
  useParams: () => ({}),
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
import NewResearcherPage from "@/app/researchers/new/page";

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
      <NewResearcherPage />
    </QueryClientProvider>,
  );
}

async function fillForm(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Primer nombre"), "Ana");
  await user.type(screen.getByLabelText("Apellidos"), "Pérez");
  await user.selectOptions(screen.getByLabelText("Tipo de documento"), "CC");
  await user.type(screen.getByLabelText("Número de documento"), "1234567890");
  await user.type(screen.getByLabelText("Correo electrónico"), "ana@example.com");
}

describe("NewResearcherPage", () => {
  beforeEach(() => {
    mockPush.mockClear();
  });

  it("shows the create form for a director (level ≤ 3)", () => {
    renderPage(["director"]);

    expect(screen.getByRole("heading", { name: "Nuevo investigador" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Crear investigador" })).toBeInTheDocument();
  });

  it("hides the form for the researcher role (level 4)", () => {
    renderPage(["researcher"]);

    expect(screen.getByText("No tiene permisos para ver este contenido.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Crear investigador" })).not.toBeInTheDocument();
  });

  it("POSTs and redirects to the detail route on success", async () => {
    const user = userEvent.setup();
    (api.api.post as jest.Mock).mockResolvedValue({ id: "r-new", full_name: "Ana Pérez" });

    renderPage(["director"]);
    await fillForm(user);
    await user.click(screen.getByRole("button", { name: "Crear investigador" }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/researchers/",
        expect.objectContaining({ first_name: "Ana", document_number: "1234567890" }),
        { institutionId: "inst-1" },
      );
    });
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/researchers/r-new");
    });
  });

  it("keeps the form on a duplicate-document 400 (no redirect)", async () => {
    const user = userEvent.setup();
    (api.api.post as jest.Mock).mockRejectedValue(
      new ApiError("", 400, {
        document_number: ["Ya existe un investigador con este documento."],
      }),
    );

    renderPage(["director"]);
    await fillForm(user);
    await user.click(screen.getByRole("button", { name: "Crear investigador" }));

    expect(
      await screen.findByText(/ya existe un investigador con este documento/i),
    ).toBeInTheDocument();
    expect(mockPush).not.toHaveBeenCalled();
  });
});
