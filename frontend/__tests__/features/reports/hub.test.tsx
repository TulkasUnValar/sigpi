/**
 * ReportHub — type selector + per-type entity lists with status projection.
 *
 * Spec (frontend-reports RF-001): the hub composes the generator form and
 * derived entity lists showing status indicators; switching the report type
 * drives the entity list (advances → projects).
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

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
import { ReportHub } from "@/features/reports/ReportHub";

function pageOf<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results };
}

const projectRows = [
  {
    id: "p1",
    title: "Proyecto Alpha",
    status: "aprobado",
    center: "c1",
    principal_investigator: "r1",
    start_date: "2026-01-10",
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "p3",
    title: "Proyecto Gamma",
    status: "en_ejecucion",
    center: "c2",
    principal_investigator: "r2",
    start_date: "2026-01-20",
    created_at: "2026-01-10T00:00:00Z",
  },
];

const researcherRows = [
  {
    id: "r1",
    full_name: "Ana Pérez",
    institution: "inst-1",
    is_active: true,
    completeness_score: 100,
  },
  {
    id: "r2",
    full_name: "Luis Gómez",
    institution: "inst-1",
    is_active: true,
    completeness_score: 40,
  },
];

function mockEntityApi() {
  (api.api.get as jest.Mock).mockImplementation((path: string) => {
    if (path.includes("/api/projects/")) return Promise.resolve(pageOf(projectRows));
    if (path.includes("/api/researchers/")) return Promise.resolve(pageOf(researcherRows));
    if (path.includes("/api/institutions/") && path.includes("/centers/"))
      return Promise.resolve([{ id: "c1", name: "Centro de IA" }]);
    return Promise.resolve(pageOf([]));
  });
}

function renderHub() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <ReportHub />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  useAuthStore.setState({
    roles: ["director_centro"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });
  mockEntityApi();
});

describe("ReportHub — rendering", () => {
  it("renders the hub title and the generator selects", async () => {
    renderHub();

    expect(screen.getByRole("heading", { name: "Informes" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /tipo de informe/i })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /^entidad$/i })).toBeInTheDocument();
  });

  it("renders project rows with the No generado status indicator", async () => {
    renderHub();

    expect(await screen.findByText("Proyecto Alpha")).toBeInTheDocument();
    expect(screen.getByText("Proyecto Gamma")).toBeInTheDocument();
    // Status projection — the backend exposes no registry, so every row
    // starts as "No generado" until a successful preview/pdf/approve.
    expect(screen.getAllByText("No generado")).toHaveLength(2);
  });

  it("switches the entity list to researchers when the type changes", async () => {
    renderHub();
    expect(await screen.findByText("Proyecto Alpha")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("combobox", { name: /tipo de informe/i }));
    fireEvent.click(await screen.findByRole("option", { name: "Investigador" }));

    expect(await screen.findByText("Ana Pérez")).toBeInTheDocument();
    expect(screen.getByText("Luis Gómez")).toBeInTheDocument();
    expect(screen.queryByText("Proyecto Alpha")).not.toBeInTheDocument();
  });

  it("maps the advances type to the project entity list", async () => {
    renderHub();
    expect(await screen.findByText("Proyecto Alpha")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("combobox", { name: /tipo de informe/i }));
    fireEvent.click(await screen.findByRole("option", { name: "Avances" }));

    // Still the project rows — advances reports target a project entity.
    expect(await screen.findByText("Proyecto Alpha")).toBeInTheDocument();
    expect(screen.getByText("Proyecto Gamma")).toBeInTheDocument();
  });

  it("announces the loading state while entity options are fetching", async () => {
    (api.api.get as jest.Mock).mockImplementation(() => new Promise(() => undefined));
    renderHub();

    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-label", "Cargando proyectos");
  });

  it("shows an empty state when no entities are available", async () => {
    (api.api.get as jest.Mock).mockImplementation(() => Promise.resolve(pageOf([])));
    renderHub();

    expect(
      await screen.findByText("No hay proyectos disponibles para generar informes."),
    ).toBeInTheDocument();
  });

  it("resets the selected entity when the type changes", async () => {
    renderHub();
    await waitFor(() => {
      expect(screen.getByRole("combobox", { name: /^entidad$/i })).not.toBeDisabled();
    });
    fireEvent.click(screen.getByRole("combobox", { name: /^entidad$/i }));
    fireEvent.click(await screen.findByRole("option", { name: "Proyecto Alpha" }));
    expect(screen.getByRole("combobox", { name: /^entidad$/i })).toHaveTextContent(
      "Proyecto Alpha",
    );

    fireEvent.click(screen.getByRole("combobox", { name: /tipo de informe/i }));
    fireEvent.click(await screen.findByRole("option", { name: "Investigador" }));

    // The entity select reverts to its placeholder after the type switch.
    expect(screen.getByRole("combobox", { name: /^entidad$/i })).toHaveTextContent(
      "Seleccione una entidad",
    );
  });
});
