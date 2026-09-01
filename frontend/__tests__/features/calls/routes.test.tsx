/**
 * Calls routes — /calls, /calls/new, /calls/[id], /calls/[id]/edit.
 *
 * Spec (calls-ui):
 *   - /calls renders the paginated list with a director-gated create CTA.
 *   - /calls/new renders the create form; valid internal submits omit
 *     external_entity and redirect to /calls/{id}.
 *   - /calls/{id} renders the detail header with StatusBadge and the four tabs.
 *   - /calls/{id}/edit renders the edit form with read-only status/institution.
 *   - The auth boundary (middleware) redirects every /calls route to /login
 *     without a session cookie.
 */

import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

const mockPush = jest.fn();
let mockParams: Record<string, string> = { id: "call-1" };

jest.mock("next/navigation", () => ({
  usePathname: () => "/calls",
  useParams: () => mockParams,
  useRouter: () => ({ push: mockPush, prefetch: jest.fn() }),
}));

jest.mock("next/link", () => {
  return {
    __esModule: true,
    default: ({
      href,
      children,
      ...rest
    }: {
      href: string | { pathname: string };
      children: React.ReactNode;
    }) => (
      <a href={typeof href === "string" ? href : href.pathname} {...rest}>
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
import CallsPage from "@/app/calls/page";
import NewCallPage from "@/app/calls/new/page";
import CallDetailPage from "@/app/calls/[id]/page";
import EditCallPage from "@/app/calls/[id]/edit/page";

const callRow = {
  id: "call-1",
  title: "Convocatoria IA",
  status: "abierta",
  call_type: "internal",
  created_at: "2026-01-01T00:00:00Z",
};

const callDetail = {
  id: "call-1",
  institution: "inst-1",
  title: "Convocatoria IA",
  description: "Investigación en inteligencia artificial.",
  call_type: "internal",
  external_entity: "",
  submission_start: "2026-02-01",
  submission_end: "2026-03-01",
  evaluation_start: "2026-03-15",
  evaluation_end: "2026-04-15",
  status: "abierta",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
};

function pageOf<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results };
}

function setAuthRoles(roles: string[]) {
  useAuthStore.setState({
    roles,
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });
}

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  jest.clearAllMocks();
  mockParams = { id: "call-1" };
});

describe("/calls — list route", () => {
  it("renders paginated rows with status badge and call_type label", async () => {
    setAuthRoles(["director"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([callRow]));

    renderWithProviders(<CallsPage />);

    expect(await screen.findByText("Convocatoria IA")).toBeInTheDocument();
    expect(screen.getByText("Abierta")).toBeInTheDocument();
    expect(screen.getByText("Interna")).toBeInTheDocument();
  });

  it("shows the create CTA only to director+ roles", async () => {
    setAuthRoles(["researcher"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));

    renderWithProviders(<CallsPage />);

    expect(await screen.findByText("No hay convocatorias")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Nueva convocatoria" })).not.toBeInTheDocument();
  });

  it("shows the create CTA to a director_centro (alias role)", async () => {
    setAuthRoles(["director_centro"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));

    renderWithProviders(<CallsPage />);

    expect(await screen.findByRole("link", { name: "Nueva convocatoria" })).toBeInTheDocument();
  });
});

describe("/calls/new — create route", () => {
  it("renders the create form fields", async () => {
    setAuthRoles(["director"]);

    renderWithProviders(<NewCallPage />);

    expect(screen.getByLabelText(/título/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/descripción/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/tipo de convocatoria/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/inicio de postulación/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/cierre de postulación/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/inicio de evaluación/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/fin de evaluación/i)).toBeInTheDocument();
  });

  it("submits a valid internal call omitting external_entity and redirects", async () => {
    setAuthRoles(["director"]);
    (api.api.post as jest.Mock).mockResolvedValue({ ...callDetail, id: "call-9" });

    renderWithProviders(<NewCallPage />);

    await userEvent.type(screen.getByLabelText(/título/i), "Nueva convocatoria");
    await userEvent.type(screen.getByLabelText(/descripción/i), "Descripción de prueba");
    fireEvent.click(screen.getByLabelText(/tipo de convocatoria/i));
    fireEvent.click(await screen.findByRole("option", { name: "Interna" }));

    fireEvent.click(screen.getByRole("button", { name: /crear convocatoria/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/calls/",
        expect.objectContaining({
          title: "Nueva convocatoria",
          call_type: "internal",
        }),
      );
    });
    const postedBody = (api.api.post as jest.Mock).mock.calls[0][1] as Record<string, unknown>;
    expect("external_entity" in postedBody).toBe(false);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/calls/call-9"));
  });

  it("surfaces a field error when an external call lacks an entity and does not redirect", async () => {
    setAuthRoles(["director"]);

    renderWithProviders(<NewCallPage />);

    await userEvent.type(screen.getByLabelText(/título/i), "Convocatoria externa");
    await userEvent.type(screen.getByLabelText(/descripción/i), "Descripción");
    fireEvent.click(screen.getByLabelText(/tipo de convocatoria/i));
    fireEvent.click(await screen.findByRole("option", { name: "Externa" }));

    fireEvent.click(screen.getByRole("button", { name: /crear convocatoria/i }));

    expect(await screen.findByText(/entidad externa es obligatoria/i)).toBeInTheDocument();
    expect(api.api.post).not.toHaveBeenCalled();
    expect(mockPush).not.toHaveBeenCalled();
  });
});

describe("/calls/[id] — detail route", () => {
  it("renders the header with StatusBadge and the four tabs", async () => {
    setAuthRoles(["director"]);
    (api.api.get as jest.Mock).mockResolvedValue(callDetail);

    renderWithProviders(<CallDetailPage />);

    expect(await screen.findByRole("heading", { name: "Convocatoria IA" })).toBeInTheDocument();
    expect(screen.getByText("Abierta")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Resumen" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Documentos" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Proyectos" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Historial" })).toBeInTheDocument();
  });

  it("shows the Overview data for the active tab", async () => {
    setAuthRoles(["director"]);
    (api.api.get as jest.Mock).mockResolvedValue(callDetail);

    renderWithProviders(<CallDetailPage />);

    expect(await screen.findByText("Investigación en inteligencia artificial.")).toBeInTheDocument();
    expect(screen.getByText("Interna")).toBeInTheDocument();
    expect(screen.getByText(/2026-02-01/)).toBeInTheDocument();
    expect(screen.getByText(/2026-04-15/)).toBeInTheDocument();
  });
});

describe("/calls/[id]/edit — edit route", () => {
  it("renders the form with read-only status and institution", async () => {
    setAuthRoles(["director"]);
    (api.api.get as jest.Mock).mockResolvedValue(callDetail);

    renderWithProviders(<EditCallPage />);

    expect(await screen.findByLabelText(/título/i)).toHaveValue("Convocatoria IA");
    const statusField = screen.getByLabelText(/estado/i);
    expect(statusField).toHaveValue("Abierta");
    expect(statusField).toBeDisabled();
    expect(screen.getByText(/institución/i)).toBeInTheDocument();
  });

  it("PATCHes changes and redirects back to the detail page", async () => {
    setAuthRoles(["director"]);
    (api.api.get as jest.Mock).mockResolvedValue(callDetail);
    (api.api.patch as jest.Mock).mockResolvedValue({ ...callDetail, title: "Convocatoria IA v2" });

    renderWithProviders(<EditCallPage />);

    const titleInput = await screen.findByLabelText(/título/i);
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, "Convocatoria IA v2");
    fireEvent.click(screen.getByRole("button", { name: /guardar cambios/i }));

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/calls/call-1/",
        expect.objectContaining({ title: "Convocatoria IA v2" }),
      );
    });
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/calls/call-1"));
  });
});