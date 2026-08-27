/**
 * Line routes — list under a group, create, detail, and edit. Lines are
 * the leaf level: no children, CRUD only. Writes are gated to
 * director/admin/superadmin (RF-F05).
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

const mockPush = jest.fn();
let mockParams: Record<string, string> = {
  id: "inst-1",
  centerId: "center-1",
  groupId: "group-1",
};

jest.mock("next/navigation", () => ({
  usePathname: () => "/institutions/inst-1/centers/center-1/groups/group-1/lines",
  useParams: () => mockParams,
  useSearchParams: () => new URLSearchParams(),
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
import LinesPage from "@/app/institutions/[id]/centers/[centerId]/groups/[groupId]/lines/page";
import NewLinePage from "@/app/institutions/[id]/centers/[centerId]/groups/[groupId]/lines/new/page";
import LineDetailPage from "@/app/institutions/[id]/centers/[centerId]/groups/[groupId]/lines/[lineId]/page";
import EditLinePage from "@/app/institutions/[id]/centers/[centerId]/groups/[groupId]/lines/[lineId]/edit/page";

const lineRow = {
  id: "line-1",
  institution: "inst-1",
  institution_name: "Universidad Nacional",
  group: "group-1",
  code: "L-DL",
  name: "Línea de Deep Learning",
  description: "Redes profundas.",
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
  mockParams = { id: "inst-1", centerId: "center-1", groupId: "group-1" };
});

describe("LinesPage — list", () => {
  it("fetches and renders the lines of the group", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([lineRow]));

    renderWithProviders(<LinesPage />, ["director"]);

    expect(await screen.findByText("Línea de Deep Learning")).toBeInTheDocument();
    expect(api.api.get).toHaveBeenCalledWith("/api/groups/group-1/lines/", {
      sendInstitutionId: false,
    });
  });

  it("links each line to its nested detail route", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([lineRow]));

    renderWithProviders(<LinesPage />, ["director"]);

    const link = await screen.findByRole("link", { name: "Línea de Deep Learning" });
    expect(link).toHaveAttribute(
      "href",
      "/institutions/inst-1/centers/center-1/groups/group-1/lines/line-1",
    );
  });
});

describe("NewLinePage — create under group", () => {
  it("POSTs to /api/groups/{groupId}/lines/ and navigates to the detail", async () => {
    const user = userEvent.setup();
    (api.api.post as jest.Mock).mockResolvedValue(lineRow);

    renderWithProviders(<NewLinePage />, ["director"]);

    await user.type(screen.getByLabelText("Código"), "L-DL");
    await user.type(screen.getByLabelText("Nombre"), "Línea de Deep Learning");
    await user.click(screen.getByRole("button", { name: "Crear línea de investigación" }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/groups/group-1/lines/",
        expect.objectContaining({ code: "L-DL", name: "Línea de Deep Learning" }),
        { sendInstitutionId: false },
      );
    });
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith(
        "/institutions/inst-1/centers/center-1/groups/group-1/lines/line-1",
      );
    });
  });
});

describe("LineDetailPage", () => {
  it("renders the line fields", async () => {
    mockParams = { id: "inst-1", centerId: "center-1", groupId: "group-1", lineId: "line-1" };
    (api.api.get as jest.Mock).mockResolvedValue(lineRow);

    renderWithProviders(<LineDetailPage />, ["director"]);

    expect(
      await screen.findByRole("heading", { name: "Línea de Deep Learning" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Redes profundas.")).toBeInTheDocument();
    expect(screen.getByText("Activa")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /desactivar/i })).toBeInTheDocument();
  });
});

describe("EditLinePage", () => {
  it("prefills the form and PATCHes /api/lines/{id}/", async () => {
    const user = userEvent.setup();
    mockParams = { id: "inst-1", centerId: "center-1", groupId: "group-1", lineId: "line-1" };
    (api.api.get as jest.Mock).mockResolvedValue(lineRow);
    (api.api.patch as jest.Mock).mockResolvedValue({ ...lineRow, name: "Línea Renombrada" });

    renderWithProviders(<EditLinePage />, ["director"]);

    const nameInput = await screen.findByLabelText("Nombre");
    expect(nameInput).toHaveValue("Línea de Deep Learning");

    await user.clear(nameInput);
    await user.type(nameInput, "Línea Renombrada");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/lines/line-1/",
        expect.objectContaining({ name: "Línea Renombrada" }),
        { sendInstitutionId: false },
      );
    });
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith(
        "/institutions/inst-1/centers/center-1/groups/group-1/lines/line-1",
      );
    });
  });
});
