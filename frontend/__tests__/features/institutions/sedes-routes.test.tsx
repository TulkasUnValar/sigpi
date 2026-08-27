/**
 * Sede routes — list, create (admin threshold), detail and edit.
 *
 * Spec (institutions-ui RF-F03/RF-F05):
 *   - Parent institution id comes from the URL, never the body.
 *   - Child writes require admin or superadmin (RoleGuard).
 */

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

const mockPush = jest.fn();
let mockParams: Record<string, string> = { id: "inst-1" };

jest.mock("next/navigation", () => ({
  usePathname: () => "/institutions/inst-1/sedes",
  useParams: () => mockParams,
  useRouter: () => ({ push: mockPush, prefetch: jest.fn() }),
}));

jest.mock("next/link", () => {
  return {
    __esModule: true,
    default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
      <a href={href} {...rest}>
        {children}
      </a>
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
import SedesPage from "@/app/institutions/[id]/sedes/page";
import NewSedePage from "@/app/institutions/[id]/sedes/new/page";
import SedeDetailPage from "@/app/institutions/[id]/sedes/[sedeId]/page";
import EditSedePage from "@/app/institutions/[id]/sedes/[sedeId]/edit/page";

const sedeRow = {
  id: "sede-1",
  institution: "inst-1",
  institution_name: "Universidad Nacional",
  code: "S-BOG",
  name: "Sede Bogotá",
  description: "Campus principal.",
  status: "active",
  is_active: true,
  created_at: "2026-01-10T09:00:00Z",
  updated_at: "2026-02-01T09:00:00Z",
};

function pageOf<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results };
}

function renderWithProviders(ui: React.ReactElement, roles: string[]) {
  useAuthStore.setState({
    roles,
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  jest.clearAllMocks();
  mockParams = { id: "inst-1" };
});

describe("SedesPage — list", () => {
  it("renders sede rows with detail links and codes", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([sedeRow]));

    renderWithProviders(<SedesPage />, ["admin"]);

    expect(await screen.findByText("Sede Bogotá")).toBeInTheDocument();
    expect(screen.getByText("S-BOG")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sede Bogotá" })).toHaveAttribute(
      "href",
      "/institutions/inst-1/sedes/sede-1",
    );
  });

  it("fetches sedes from the nested URL without the tenant header", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([sedeRow]));

    renderWithProviders(<SedesPage />, ["admin"]);

    await screen.findByText("Sede Bogotá");
    expect(api.api.get).toHaveBeenCalledWith("/api/institutions/inst-1/sedes/", {
      sendInstitutionId: false,
    });
  });

  it("shows the create CTA for admins and hides it for directors (RF-F05)", () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([sedeRow]));

    const { unmount } = renderWithProviders(<SedesPage />, ["director"]);
    expect(screen.queryByRole("link", { name: /nueva sede/i })).not.toBeInTheDocument();
    unmount();

    (api.api.get as jest.Mock).mockResolvedValue(pageOf([sedeRow]));
    renderWithProviders(<SedesPage />, ["admin"]);
    expect(screen.getByRole("link", { name: /nueva sede/i })).toBeInTheDocument();
  });
});

describe("NewSedePage — admin creates a sede", () => {
  it("POSTs to the nested URL with the parent from params, then redirects", async () => {
    const user = userEvent.setup();
    (api.api.post as jest.Mock).mockResolvedValue(sedeRow);

    renderWithProviders(<NewSedePage />, ["admin"]);

    await user.type(screen.getByLabelText("Código"), "S-BOG");
    await user.type(screen.getByLabelText("Nombre"), "Sede Bogotá");
    await user.click(screen.getByRole("button", { name: "Crear sede" }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/institutions/inst-1/sedes/",
        expect.objectContaining({ code: "S-BOG", name: "Sede Bogotá" }),
        { sendInstitutionId: false },
      );
    });
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/institutions/inst-1/sedes/sede-1");
    });
  });

  it("denies a director with the RoleGuard alert (RF-F05)", () => {
    renderWithProviders(<NewSedePage />, ["director"]);

    expect(screen.getByRole("alert")).toHaveTextContent(/no tiene permisos/i);
    expect(screen.queryByRole("button", { name: "Crear sede" })).not.toBeInTheDocument();
  });
});

describe("SedeDetailPage", () => {
  it("renders the sede fields and FSM actions for an admin", async () => {
    mockParams = { id: "inst-1", sedeId: "sede-1" };
    (api.api.get as jest.Mock).mockResolvedValue(sedeRow);

    renderWithProviders(<SedeDetailPage />, ["admin"]);

    expect(await screen.findByRole("heading", { name: "Sede Bogotá" })).toBeInTheDocument();
    expect(screen.getByText("S-BOG")).toBeInTheDocument();
    expect(screen.getByText("Campus principal.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /desactivar/i })).toBeInTheDocument();
  });

  it("posts child FSM transitions to /api/sedes/{id}/{action}/", async () => {
    const user = userEvent.setup();
    mockParams = { id: "inst-1", sedeId: "sede-1" };
    (api.api.get as jest.Mock).mockResolvedValue(sedeRow);
    (api.api.post as jest.Mock).mockResolvedValue({ ...sedeRow, status: "deactivated" });

    renderWithProviders(<SedeDetailPage />, ["admin"]);

    await user.click(await screen.findByRole("button", { name: /desactivar/i }));
    const dialog = await screen.findByRole("alertdialog");
    await user.click(within(dialog).getByRole("button", { name: /desactivar/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/sedes/sede-1/deactivate/",
        {},
        { sendInstitutionId: false },
      );
    });
  });

  it("renders an empty state when the sede is not found", async () => {
    mockParams = { id: "inst-1", sedeId: "missing" };
    (api.api.get as jest.Mock).mockRejectedValue(new Error("Sede no encontrada."));

    renderWithProviders(<SedeDetailPage />, ["admin"]);

    expect(await screen.findByText("Sede no encontrada")).toBeInTheDocument();
  });
});

describe("EditSedePage", () => {
  it("prefills the form and PATCHes /api/sedes/{id}/", async () => {
    const user = userEvent.setup();
    mockParams = { id: "inst-1", sedeId: "sede-1" };
    (api.api.get as jest.Mock).mockResolvedValue(sedeRow);
    (api.api.patch as jest.Mock).mockResolvedValue({ ...sedeRow, name: "Sede Actualizada" });

    renderWithProviders(<EditSedePage />, ["admin"]);

    const nameInput = await screen.findByLabelText("Nombre");
    expect(nameInput).toHaveValue("Sede Bogotá");

    await user.clear(nameInput);
    await user.type(nameInput, "Sede Actualizada");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/sedes/sede-1/",
        expect.objectContaining({ name: "Sede Actualizada" }),
        { sendInstitutionId: false },
      );
    });
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/institutions/inst-1/sedes/sede-1");
    });
  });
});