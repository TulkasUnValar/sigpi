/**
 * Facultad routes — list with sede filter, create with sede select.
 *
 * Spec (institutions-ui RF-F03):
 *   - GET /api/institutions/{pk}/facultades/ with optional ?sede= filter.
 *   - The sede reference is a selectable form field (never the parent).
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

const mockPush = jest.fn();
let mockParams: Record<string, string> = { id: "inst-1" };
let mockSearchParams: Record<string, string> = {};

jest.mock("next/navigation", () => ({
  usePathname: () => "/institutions/inst-1/facultades",
  useParams: () => mockParams,
  useSearchParams: () => new URLSearchParams(mockSearchParams),
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
import FacultadesPage from "@/app/institutions/[id]/facultades/page";
import NewFacultadPage from "@/app/institutions/[id]/facultades/new/page";

const sedeRow = {
  id: "sede-1",
  institution: "inst-1",
  institution_name: "Universidad Nacional",
  code: "S-BOG",
  name: "Sede Bogotá",
  description: "",
  status: "active",
  is_active: true,
  created_at: "2026-01-10T09:00:00Z",
  updated_at: "2026-02-01T09:00:00Z",
};

const facultadRow = {
  id: "fac-1",
  institution: "inst-1",
  institution_name: "Universidad Nacional",
  sede: "sede-1",
  code: "F-ING",
  name: "Facultad de Ingeniería",
  description: "",
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
  mockSearchParams = {};
});

describe("FacultadesPage — list", () => {
  it("fetches facultades from the nested URL", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([facultadRow]));

    renderWithProviders(<FacultadesPage />, ["admin"]);

    expect(await screen.findByText("Facultad de Ingeniería")).toBeInTheDocument();
    expect(api.api.get).toHaveBeenCalledWith("/api/institutions/inst-1/facultades/", {
      sendInstitutionId: false,
    });
  });

  it("passes the ?sede= filter from the search params", async () => {
    mockSearchParams = { sede: "sede-1" };
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([facultadRow]));

    renderWithProviders(<FacultadesPage />, ["admin"]);

    await screen.findByText("Facultad de Ingeniería");
    expect(api.api.get).toHaveBeenCalledWith("/api/institutions/inst-1/facultades/?sede=sede-1", {
      sendInstitutionId: false,
    });
  });
});

describe("NewFacultadPage", () => {
  it("loads sede options and POSTs with the selected sede reference", async () => {
    const user = userEvent.setup();
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([sedeRow]));
    (api.api.post as jest.Mock).mockResolvedValue(facultadRow);

    renderWithProviders(<NewFacultadPage />, ["admin"]);

    // Wait for the sede options to load.
    await screen.findByRole("option", { name: "Sede Bogotá" });

    await user.selectOptions(screen.getByLabelText("Sede"), "sede-1");
    await user.type(screen.getByLabelText("Código"), "F-ING");
    await user.type(screen.getByLabelText("Nombre"), "Facultad de Ingeniería");
    await user.click(screen.getByRole("button", { name: "Crear facultad" }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/institutions/inst-1/facultades/",
        expect.objectContaining({ sede: "sede-1", code: "F-ING" }),
        { sendInstitutionId: false },
      );
    });
  });
});
