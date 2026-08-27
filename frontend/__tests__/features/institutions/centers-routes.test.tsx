/**
 * Center routes — list with parent filters, create with facultad nesting,
 * and detail with contact fields.
 *
 * Spec (institutions-ui RF-F03):
 *   - GET /api/institutions/{pk}/centers/ with ?parent_type=&parent= filters.
 *   - POSTing with a facultad selected nests the center under the facultad.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

const mockPush = jest.fn();
let mockParams: Record<string, string> = { id: "inst-1" };
let mockSearchParams: Record<string, string> = {};

jest.mock("next/navigation", () => ({
  usePathname: () => "/institutions/inst-1/centers",
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
import CentersPage from "@/app/institutions/[id]/centers/page";
import NewCenterPage from "@/app/institutions/[id]/centers/new/page";
import CenterDetailPage from "@/app/institutions/[id]/centers/[centerId]/page";

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

const centerRow = {
  id: "center-1",
  institution: "inst-1",
  institution_name: "Universidad Nacional",
  sede: "sede-1",
  facultad: "fac-1",
  code: "C-IA",
  name: "Centro de Inteligencia Artificial",
  description: "Investigación en IA.",
  contact_email: "ia@unal.edu",
  contact_phone: "+57 1 5550400",
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

describe("CentersPage — list", () => {
  it("fetches all centers of the institution", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([centerRow]));

    renderWithProviders(<CentersPage />, ["admin"]);

    expect(await screen.findByText("Centro de Inteligencia Artificial")).toBeInTheDocument();
    expect(api.api.get).toHaveBeenCalledWith("/api/institutions/inst-1/centers/", {
      sendInstitutionId: false,
    });
  });

  it("passes parent_type and parent filters from the search params", async () => {
    mockSearchParams = { parent_type: "facultad", parent: "fac-1" };
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([centerRow]));

    renderWithProviders(<CentersPage />, ["admin"]);

    await screen.findByText("Centro de Inteligencia Artificial");
    expect(api.api.get).toHaveBeenCalledWith(
      "/api/institutions/inst-1/centers/?parent_type=facultad&parent=fac-1",
      { sendInstitutionId: false },
    );
  });
});

describe("NewCenterPage — center→facultad nesting", () => {
  it("loads sede/facultad options and POSTs with the facultad reference", async () => {
    const user = userEvent.setup();
    (api.api.get as jest.Mock)
      .mockResolvedValueOnce(pageOf([sedeRow]))
      .mockResolvedValueOnce(pageOf([facultadRow]));
    (api.api.post as jest.Mock).mockResolvedValue(centerRow);

    renderWithProviders(<NewCenterPage />, ["admin"]);

    await screen.findByRole("option", { name: "Facultad de Ingeniería" });

    await user.selectOptions(screen.getByLabelText("Facultad"), "fac-1");
    await user.type(screen.getByLabelText("Código"), "C-IA");
    await user.type(screen.getByLabelText("Nombre"), "Centro de Inteligencia Artificial");
    await user.click(screen.getByRole("button", { name: "Crear centro de investigación" }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/institutions/inst-1/centers/",
        expect.objectContaining({ facultad: "fac-1", code: "C-IA" }),
        { sendInstitutionId: false },
      );
    });
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/institutions/inst-1/centers/center-1");
    });
  });
});

describe("CenterDetailPage", () => {
  it("renders the center fields including contact data", async () => {
    mockParams = { id: "inst-1", centerId: "center-1" };
    (api.api.get as jest.Mock).mockResolvedValue(centerRow);

    renderWithProviders(<CenterDetailPage />, ["admin"]);

    expect(
      await screen.findByRole("heading", { name: "Centro de Inteligencia Artificial" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Investigación en IA.")).toBeInTheDocument();
    expect(screen.getByText("ia@unal.edu")).toBeInTheDocument();
    expect(screen.getByText("+57 1 5550400")).toBeInTheDocument();
    expect(screen.getByText("Activa")).toBeInTheDocument();
  });
});
