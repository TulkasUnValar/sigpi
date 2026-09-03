/**
 * ReportGeneratorForm — dependent type/entity selects.
 *
 * Spec (frontend-reports RF-002):
 *   - Selecting a report type drives the dependent entity selector fed by
 *     the existing hooks; `advances` targets a project entity.
 *   - The form is controlled: type/entity changes bubble up to the hub,
 *     which resets the entity when the type changes.
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
import { ReportGeneratorForm } from "@/features/reports/ReportGeneratorForm";

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

function renderForm(
  props: Partial<{
    type: "project" | "researcher" | "center" | "advances";
    entityId: string | null;
    onTypeChange: (type: string) => void;
    onEntityChange: (entityId: string | null) => void;
  }> = {},
) {
  const defaults = {
    type: "project" as const,
    entityId: null,
    onTypeChange: jest.fn(),
    onEntityChange: jest.fn(),
  };
  const merged = { ...defaults, ...props };
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <ReportGeneratorForm
        type={merged.type}
        entityId={merged.entityId}
        onTypeChange={merged.onTypeChange}
        onEntityChange={merged.onEntityChange}
      />
    </QueryClientProvider>,
  );
  return { onTypeChange: merged.onTypeChange, onEntityChange: merged.onEntityChange };
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

async function openSelect(triggerName: RegExp) {
  fireEvent.click(screen.getByRole("combobox", { name: triggerName }));
}

/** Open the entity select once its options have loaded (enabled). */
async function openEntitySelect() {
  await waitFor(() => {
    expect(screen.getByRole("combobox", { name: /^entidad$/i })).not.toBeDisabled();
  });
  fireEvent.click(screen.getByRole("combobox", { name: /^entidad$/i }));
}

describe("ReportGeneratorForm — type selector", () => {
  it("offers the four report types with Spanish labels", async () => {
    renderForm();

    await openSelect(/tipo de informe/i);
    expect(await screen.findByRole("option", { name: "Proyecto" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Investigador" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Centro" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Avances" })).toBeInTheDocument();
  });

  it("notifies the hub when the type changes", async () => {
    const { onTypeChange } = renderForm();

    await openSelect(/tipo de informe/i);
    fireEvent.click(await screen.findByRole("option", { name: "Investigador" }));

    expect(onTypeChange).toHaveBeenCalledWith("researcher");
  });
});

describe("ReportGeneratorForm — dependent entity selector", () => {
  it("lists projects from useProjectsList when type is project (RF-002)", async () => {
    renderForm();

    await openEntitySelect();
    expect(await screen.findByRole("option", { name: "Proyecto Alpha" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Proyecto Gamma" })).toBeInTheDocument();
  });

  it("lists projects, not advances, when type is advances (RF-002)", async () => {
    renderForm({ type: "advances" });

    await openEntitySelect();
    expect(await screen.findByRole("option", { name: "Proyecto Alpha" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /avance/i })).not.toBeInTheDocument();
  });

  it("lists researchers when type is researcher", async () => {
    renderForm({ type: "researcher" });

    await openEntitySelect();
    expect(await screen.findByRole("option", { name: "Ana Pérez" })).toBeInTheDocument();
  });

  it("lists centers when type is center", async () => {
    renderForm({ type: "center" });

    await openEntitySelect();
    expect(await screen.findByRole("option", { name: "Centro de IA" })).toBeInTheDocument();
  });

  it("notifies the hub when an entity is picked", async () => {
    const { onEntityChange } = renderForm();

    await openEntitySelect();
    fireEvent.click(await screen.findByRole("option", { name: "Proyecto Alpha" }));

    expect(onEntityChange).toHaveBeenCalledWith("p1");
  });

  it("disables the entity select while no options are available", async () => {
    (api.api.get as jest.Mock).mockImplementation(() => Promise.resolve(pageOf([])));
    renderForm();

    expect(await screen.findByRole("combobox", { name: /^entidad$/i })).toBeDisabled();
  });
});
