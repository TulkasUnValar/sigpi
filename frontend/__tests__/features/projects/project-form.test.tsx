/**
 * ProjectForm — shared RHF + zod edit form (FR-05 / FR-07).
 *
 * Spec (projects-ui edit):
 *   - Seeded from `useProjectDetail` / the `project` prop; dependent
 *     selects center → group → line and PI are populated.
 *   - zod validates before submit; invalid input does not PATCH.
 *   - Changing the center resets group and line; changing the group
 *     resets line (empty relations map to `null`).
 *   - 400 field errors map via `setError`; 403 shows a toast and stays
 *     on the form without redirecting.
 *   - Only the writable scalar fields are PATCHed — never `project`,
 *     `members`, or `documents`.
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

const pushMock = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => "/projects/p1/edit",
  useParams: () => ({ id: "p1" }),
  useRouter: () => ({ push: pushMock, prefetch: jest.fn() }),
}));

jest.mock("next/link", () => {
  return {
    __esModule: true,
    default: ({
      href,
      children,
    }: {
      href: string | { pathname: string };
      children: React.ReactNode;
    }) => <a href={typeof href === "string" ? href : href.pathname}>{children}</a>,
  };
});

jest.mock("sonner", () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  },
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
import { ProjectForm } from "@/features/projects";
import { buildUpdatePayload } from "@/features/projects/schemas";
import type { ProjectDetailModel } from "@/features/projects";

const toastModule = jest.requireMock("sonner") as {
  toast: { success: jest.Mock; error: jest.Mock };
};

const project: ProjectDetailModel = {
  id: "p1",
  institution: "inst-1",
  center: "c1",
  group: "g1",
  line: "l1",
  principal_investigator: "r1",
  title: "Proyecto Alpha",
  abstract: "Resumen del proyecto.",
  objectives: "Objetivos.",
  methodology: "Metodología.",
  expected_results: "Resultados.",
  keywords: "alpha",
  start_date: "2026-01-10",
  estimated_end_date: "2027-01-10",
  actual_end_date: null,
  status: "en_revision",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  members: [],
  documents: [],
};

const centers = [
  { id: "c1", name: "Centro A", code: "CA" },
  { id: "c2", name: "Centro B", code: "CB" },
];
const groups = [
  { id: "g1", name: "Grupo 1", code: "G1" },
  { id: "g2", name: "Grupo 2", code: "G2" },
];
const lines = [
  { id: "l1", name: "Línea 1", code: "L1" },
  { id: "l2", name: "Línea 2", code: "L2" },
];
const researchers = [
  {
    id: "r1",
    full_name: "Ana Pérez",
    institution: "inst-1",
    is_active: true,
    completeness_score: 100,
  },
];

function pageOf<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results };
}

function renderForm() {
  useAuthStore.setState({
    roles: ["researcher"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
    centers: [],
  });

  // Order matters: the dependent URLs nest the parent segment
  // (e.g. /api/centers/{id}/groups/), so match the leaf first.
  (api.api.get as jest.Mock).mockImplementation((path: string) => {
    if (path.includes("/lines/")) return Promise.resolve(lines);
    if (path.includes("/groups/")) return Promise.resolve(groups);
    if (path.includes("/centers/")) return Promise.resolve(centers);
    if (path.includes("/researchers/")) return Promise.resolve(pageOf(researchers));
    return Promise.resolve(pageOf([]));
  });

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ProjectForm project={project} />
    </QueryClientProvider>,
  );
}

/** Open a select and pick an option once the async options resolve. */
async function selectOption(label: RegExp, optionName: string) {
  fireEvent.click(screen.getByLabelText(label));
  fireEvent.click(await screen.findByRole("option", { name: optionName }));
}

beforeEach(() => {
  jest.clearAllMocks();
  pushMock.mockClear();
});

describe("ProjectForm — seeding", () => {
  it("seeds the writable fields and the center select from the project", async () => {
    renderForm();

    expect(await screen.findByLabelText(/título/i)).toHaveValue("Proyecto Alpha");
    expect(screen.getByLabelText(/resumen/i)).toHaveValue("Resumen del proyecto.");
    expect(screen.getByLabelText(/fecha de inicio/i)).toHaveValue("2026-01-10");

    await waitFor(() => {
      expect(screen.getByRole("combobox", { name: /centro/i })).toHaveTextContent("Centro A");
    });
  });
});

describe("ProjectForm — zod validation", () => {
  it("rejects an empty title and does not PATCH", async () => {
    renderForm();
    const title = await screen.findByLabelText(/título/i);

    fireEvent.change(title, { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: /guardar cambios/i }));

    expect(await screen.findByText(/título es obligatorio/i)).toBeInTheDocument();
    expect(api.api.patch).not.toHaveBeenCalled();
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("rejects an end date before the start date and does not PATCH", async () => {
    renderForm();
    const end = await screen.findByLabelText(/fecha de finalización/i);

    fireEvent.change(end, { target: { value: "2025-01-01" } });
    fireEvent.click(screen.getByRole("button", { name: /guardar cambios/i }));

    expect(
      await screen.findByText(/la fecha de finalización debe ser posterior/i),
    ).toBeInTheDocument();
    expect(api.api.patch).not.toHaveBeenCalled();
  });
});

describe("ProjectForm — dependent selects", () => {
  it("resets group and line to null when the center changes", async () => {
    (api.api.patch as jest.Mock).mockResolvedValue(project);
    renderForm();
    await screen.findByLabelText(/título/i);

    await selectOption(/centro/i, "Centro B");
    fireEvent.click(screen.getByRole("button", { name: /guardar cambios/i }));

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalled();
    });
    const body = (api.api.patch as jest.Mock).mock.calls[0][1] as Record<string, unknown>;
    expect(body.center).toBe("c2");
    expect(body.group).toBeNull();
    expect(body.line).toBeNull();
  });

  it("resets line to null when the group changes", async () => {
    (api.api.patch as jest.Mock).mockResolvedValue(project);
    renderForm();
    await screen.findByLabelText(/título/i);

    await selectOption(/grupo/i, "Grupo 2");
    fireEvent.click(screen.getByRole("button", { name: /guardar cambios/i }));

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalled();
    });
    const body = (api.api.patch as jest.Mock).mock.calls[0][1] as Record<string, unknown>;
    expect(body.group).toBe("g2");
    expect(body.line).toBeNull();
  });
});

describe("ProjectForm — submit payload", () => {
  it("submits only the writable scalar fields and redirects to the detail", async () => {
    (api.api.patch as jest.Mock).mockResolvedValue({ ...project, title: "Proyecto Alpha" });
    renderForm();
    await screen.findByLabelText(/título/i);

    fireEvent.click(screen.getByRole("button", { name: /guardar cambios/i }));

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalled();
    });
    const body = (api.api.patch as jest.Mock).mock.calls[0][1] as Record<string, unknown>;
    expect(body).toEqual({
      title: "Proyecto Alpha",
      abstract: "Resumen del proyecto.",
      objectives: "Objetivos.",
      methodology: "Metodología.",
      expected_results: "Resultados.",
      keywords: "alpha",
      start_date: "2026-01-10",
      estimated_end_date: "2027-01-10",
      center: "c1",
      group: "g1",
      line: "l1",
      principal_investigator: "r1",
    });
    expect(body).not.toHaveProperty("project");
    expect(body).not.toHaveProperty("members");
    expect(body).not.toHaveProperty("documents");

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/projects/p1");
    });
  });
});

describe("ProjectForm — server errors", () => {
  it("maps 400 field errors via setError and does not redirect", async () => {
    (api.api.patch as jest.Mock).mockRejectedValue(
      new ApiError("Solicitud inválida.", 400, { title: ["El título ya existe."] }),
    );
    renderForm();
    await screen.findByLabelText(/título/i);

    fireEvent.click(screen.getByRole("button", { name: /guardar cambios/i }));

    expect(await screen.findByText("El título ya existe.")).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("shows a toast and stays on the form for a 403", async () => {
    (api.api.patch as jest.Mock).mockRejectedValue(new ApiError("Project is closed", 403));
    renderForm();
    await screen.findByLabelText(/título/i);

    fireEvent.click(screen.getByRole("button", { name: /guardar cambios/i }));

    await waitFor(() => {
      expect(toastModule.toast.error).toHaveBeenCalledWith("Project is closed");
    });
    expect(pushMock).not.toHaveBeenCalled();
    expect(screen.getByLabelText(/título/i)).toBeInTheDocument();
  });
});

describe("buildUpdatePayload", () => {
  it("maps empty group/line to null and drops the read-only collections", () => {
    const payload = buildUpdatePayload({
      title: "Título",
      abstract: "Resumen",
      objectives: "Objetivos",
      methodology: "Método",
      expected_results: "Resultados",
      keywords: "",
      start_date: "2026-01-01",
      estimated_end_date: "2027-01-01",
      center: "c1",
      group: "",
      line: "",
      principal_investigator: "r1",
    });

    expect(payload.group).toBeNull();
    expect(payload.line).toBeNull();
    expect(Object.keys(payload).sort()).toEqual(
      [
        "abstract",
        "center",
        "estimated_end_date",
        "expected_results",
        "group",
        "keywords",
        "line",
        "methodology",
        "objectives",
        "principal_investigator",
        "start_date",
        "title",
      ].sort(),
    );
  });
});
