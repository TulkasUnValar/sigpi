/**
 * Group routes — list under a center, create, detail with FSM bar,
 * and edit. Writes are gated to director/admin/superadmin (RF-F05).
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

const mockPush = jest.fn();
let mockParams: Record<string, string> = { id: "inst-1", centerId: "center-1" };

jest.mock("next/navigation", () => ({
  usePathname: () => "/institutions/inst-1/centers/center-1/groups",
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
import GroupsPage from "@/app/institutions/[id]/centers/[centerId]/groups/page";
import NewGroupPage from "@/app/institutions/[id]/centers/[centerId]/groups/new/page";
import GroupDetailPage from "@/app/institutions/[id]/centers/[centerId]/groups/[groupId]/page";
import EditGroupPage from "@/app/institutions/[id]/centers/[centerId]/groups/[groupId]/edit/page";

const groupRow = {
  id: "group-1",
  institution: "inst-1",
  institution_name: "Universidad Nacional",
  center: "center-1",
  code: "G-ML",
  name: "Grupo de Machine Learning",
  description: "Aprendizaje automático.",
  status: "active",
  is_active: true,
  created_at: "2026-01-10T09:00:00Z",
  updated_at: "2026-02-01T09:00:00Z",
};

const archivedGroup = {
  ...groupRow,
  id: "group-3",
  name: "Grupo Archivado",
  status: "archived",
  is_active: false,
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
  mockParams = { id: "inst-1", centerId: "center-1" };
});

describe("GroupsPage — list", () => {
  it("fetches and renders the groups of the center", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([groupRow]));

    renderWithProviders(<GroupsPage />, ["director"]);

    expect(await screen.findByText("Grupo de Machine Learning")).toBeInTheDocument();
    expect(api.api.get).toHaveBeenCalledWith("/api/centers/center-1/groups/", {
      sendInstitutionId: false,
    });
  });

  it("links each group to its nested detail route", async () => {
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([groupRow]));

    renderWithProviders(<GroupsPage />, ["director"]);

    const link = await screen.findByRole("link", { name: "Grupo de Machine Learning" });
    expect(link).toHaveAttribute("href", "/institutions/inst-1/centers/center-1/groups/group-1");
  });
});

describe("NewGroupPage — create under center", () => {
  it("POSTs to /api/centers/{centerId}/groups/ and navigates to the detail", async () => {
    const user = userEvent.setup();
    (api.api.post as jest.Mock).mockResolvedValue(groupRow);

    renderWithProviders(<NewGroupPage />, ["director"]);

    await user.type(screen.getByLabelText("Código"), "G-ML");
    await user.type(screen.getByLabelText("Nombre"), "Grupo de Machine Learning");
    await user.click(screen.getByRole("button", { name: "Crear grupo de investigación" }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/centers/center-1/groups/",
        expect.objectContaining({ code: "G-ML", name: "Grupo de Machine Learning" }),
        { sendInstitutionId: false },
      );
    });
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/institutions/inst-1/centers/center-1/groups/group-1");
    });
  });
});

describe("GroupDetailPage", () => {
  it("renders the group fields and exposes FSM actions for a director", async () => {
    mockParams = { id: "inst-1", centerId: "center-1", groupId: "group-1" };
    (api.api.get as jest.Mock).mockResolvedValue(groupRow);

    renderWithProviders(<GroupDetailPage />, ["director"]);

    expect(
      await screen.findByRole("heading", { name: "Grupo de Machine Learning" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Aprendizaje automático.")).toBeInTheDocument();
    expect(screen.getByText("Activa")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /desactivar/i })).toBeInTheDocument();
  });

  it("renders no FSM actions for an archived group (terminal state)", async () => {
    mockParams = { id: "inst-1", centerId: "center-1", groupId: "group-3" };
    (api.api.get as jest.Mock).mockResolvedValue(archivedGroup);

    renderWithProviders(<GroupDetailPage />, ["director"]);

    expect(await screen.findByRole("heading", { name: "Grupo Archivado" })).toBeInTheDocument();
    expect(screen.getByText("Archivada")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /activar|desactivar|archivar/i })).toBeNull();
  });
});

describe("EditGroupPage", () => {
  it("prefills the form and PATCHes /api/groups/{id}/", async () => {
    const user = userEvent.setup();
    mockParams = { id: "inst-1", centerId: "center-1", groupId: "group-1" };
    (api.api.get as jest.Mock).mockResolvedValue(groupRow);
    (api.api.patch as jest.Mock).mockResolvedValue({ ...groupRow, name: "Grupo Renombrado" });

    renderWithProviders(<EditGroupPage />, ["director"]);

    const nameInput = await screen.findByLabelText("Nombre");
    expect(nameInput).toHaveValue("Grupo de Machine Learning");

    await user.clear(nameInput);
    await user.type(nameInput, "Grupo Renombrado");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/groups/group-1/",
        expect.objectContaining({ name: "Grupo Renombrado" }),
        { sendInstitutionId: false },
      );
    });
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/institutions/inst-1/centers/center-1/groups/group-1");
    });
  });
});
