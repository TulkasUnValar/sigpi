/**
 * PR2 managers — DocumentsManager, ProjectsManager, StateHistoryManager,
 * the delete gate (DeleteCallButton) and the nested fixtures/handlers.
 *
 * Spec (calls-ui):
 *   - Documents are metadata-only; delete refreshes the list.
 *   - Project linking is offered only for `abierta` calls; a duplicate
 *     association (409) surfaces via the Toaster.
 *   - State history renders read-only with no action controls.
 *   - Delete is gated to `borrador` calls with zero linked projects and
 *     redirects to /calls after confirmation.
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

const mockPush = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => "/calls",
  useParams: () => ({ id: "call-1" }),
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
import { fixtureCallDocuments, fixtureCallProjects, fixtureCallStateLogs } from "@/fixtures";
import { DocumentsManager } from "@/features/calls/DocumentsManager";
import { ProjectsManager } from "@/features/calls/ProjectsManager";
import { StateHistoryManager } from "@/features/calls/StateHistoryManager";
import { DeleteCallButton } from "@/features/calls/DeleteCallButton";

const toastModule = jest.requireMock("sonner") as {
  toast: { success: jest.Mock; error: jest.Mock };
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

function renderWithQuery(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const docFixture = {
  id: "doc-1",
  call: "call-1",
  name: "Bases de la convocatoria",
  doc_type: "convocatoria",
  external_url: "https://example.com/bases.pdf",
  created_at: "2026-01-05T09:00:00Z",
};

const linkedProject = {
  id: "cp-1",
  call: "call-1",
  project: "p1",
  linked_at: "2026-01-10T09:00:00Z",
};

const stateLog = {
  id: "sl-1",
  call: "call-1",
  from_state: "borrador",
  to_state: "abierta",
  triggered_by: "u1",
  reason: "Apertura oficial",
  created_at: "2026-01-02T09:00:00Z",
};

const projectOptions = [
  { id: "p1", title: "Proyecto Alpha" },
  { id: "p2", title: "Proyecto Beta" },
];

function mockProjectOptions() {
  (api.api.get as jest.Mock).mockImplementation((path: string) => {
    if (path === "/api/calls/call-1/projects/") {
      return Promise.resolve(pageOf([linkedProject]));
    }
    return Promise.resolve(pageOf(projectOptions));
  });
}

beforeEach(() => {
  jest.clearAllMocks();
  mockPush.mockClear();
});

// ─────────────────────────────────────────────────────────
// Nested fixtures — handler contract (task 2.5)
// ─────────────────────────────────────────────────────────

describe("nested fixtures — handler contract", () => {
  it("provides document fixtures keyed by call with metadata fields", () => {
    const docs = fixtureCallDocuments["call-1"] ?? [];
    expect(docs.length).toBeGreaterThan(0);
    docs.forEach((d) => {
      expect(d.call).toBe("call-1");
      expect(d.name).toBeTruthy();
      expect(d.doc_type).toBeTruthy();
      expect(d.external_url).toBeTruthy();
    });
  });

  it("keeps the borrador call free of documents and projects (delete gate)", () => {
    expect(fixtureCallDocuments["call-2"] ?? []).toHaveLength(0);
    expect(fixtureCallProjects["call-2"] ?? []).toHaveLength(0);
  });

  it("links at least one project to the open call (duplicate 409 precondition)", () => {
    const linked = fixtureCallProjects["call-1"] ?? [];
    expect(linked.length).toBeGreaterThan(0);
    expect(linked.map((cp) => cp.project)).toContain("p1");
  });

  it("provides read-only state logs keyed by call", () => {
    const logs = fixtureCallStateLogs["call-1"] ?? [];
    expect(logs.length).toBeGreaterThan(0);
    expect(logs[0]).toMatchObject({
      from_state: "borrador",
      to_state: "abierta",
    });
  });
});

// ─────────────────────────────────────────────────────────
// DocumentsManager — metadata-only CRUD (task 2.1)
// ─────────────────────────────────────────────────────────

describe("DocumentsManager", () => {
  it("renders document metadata rows as external links", async () => {
    setAuthRoles(["director"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([docFixture]));

    renderWithQuery(<DocumentsManager callId="call-1" />);

    expect(await screen.findByText("Bases de la convocatoria")).toBeInTheDocument();
    expect(screen.getByText("Convocatoria")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Bases de la convocatoria" })).toHaveAttribute(
      "href",
      "https://example.com/bases.pdf",
    );
  });

  it("adds a document capturing only metadata fields", async () => {
    setAuthRoles(["director"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));
    (api.api.post as jest.Mock).mockResolvedValue(docFixture);

    renderWithQuery(<DocumentsManager callId="call-1" />);
    fireEvent.click(await screen.findByRole("button", { name: "Agregar documento" }));

    fireEvent.change(screen.getByLabelText(/nombre/i), {
      target: { value: "Bases de la convocatoria" },
    });
    fireEvent.change(screen.getByLabelText(/url externa/i), {
      target: { value: "https://example.com/bases.pdf" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Guardar documento" }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/calls/call-1/documents/",
        expect.objectContaining({
          name: "Bases de la convocatoria",
          doc_type: "convocatoria",
          external_url: "https://example.com/bases.pdf",
        }),
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    expect(toastModule.toast.success).toHaveBeenCalled();
  });

  it("deletes a document after confirmation and refreshes the list", async () => {
    setAuthRoles(["director"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([docFixture]));
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    renderWithQuery(<DocumentsManager callId="call-1" />);
    fireEvent.click(await screen.findByRole("button", { name: /eliminar/i }));

    const dialog = await screen.findByRole("alertdialog");
    expect(dialog).toHaveTextContent(/¿Eliminar documento\?/);

    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith(
        "/api/calls/call-1/documents/doc-1/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    expect(toastModule.toast.success).toHaveBeenCalled();
  });

  it("edits a document's metadata via the dialog", async () => {
    setAuthRoles(["director"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([docFixture]));
    (api.api.patch as jest.Mock).mockResolvedValue({
      ...docFixture,
      name: "Bases v2",
      doc_type: "anexo",
    });

    renderWithQuery(<DocumentsManager callId="call-1" />);
    fireEvent.click(await screen.findByRole("button", { name: /editar/i }));

    const nameInput = await screen.findByLabelText(/nombre/i);
    fireEvent.change(nameInput, { target: { value: "Bases v2" } });
    fireEvent.change(screen.getByLabelText(/tipo de documento/i), {
      target: { value: "anexo" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Guardar documento" }));

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/calls/call-1/documents/doc-1/",
        expect.objectContaining({ name: "Bases v2", doc_type: "anexo" }),
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    expect(toastModule.toast.success).toHaveBeenCalled();
  });

  it("hides mutation controls for non-manager roles", async () => {
    setAuthRoles(["researcher"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([docFixture]));

    renderWithQuery(<DocumentsManager callId="call-1" />);

    expect(await screen.findByText("Bases de la convocatoria")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Agregar documento" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /eliminar/i })).not.toBeInTheDocument();
  });
});

// ─────────────────────────────────────────────────────────
// ProjectsManager — link/unlink (task 2.2)
// ─────────────────────────────────────────────────────────

describe("ProjectsManager", () => {
  it("links an unlinked project when the call is abierta", async () => {
    setAuthRoles(["director"]);
    mockProjectOptions();
    (api.api.post as jest.Mock).mockResolvedValue({
      id: "cp-2",
      call: "call-1",
      project: "p2",
      linked_at: "2026-01-11T09:00:00Z",
    });

    renderWithQuery(<ProjectsManager callId="call-1" status="abierta" />);

    expect(await screen.findByText("Proyecto Alpha")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/proyecto a vincular/i), {
      target: { value: "p2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Vincular" }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/calls/call-1/projects/",
        expect.objectContaining({ project: "p2" }),
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    expect(toastModule.toast.success).toHaveBeenCalled();
  });

  it("does not offer linking when the call is not abierta", async () => {
    setAuthRoles(["director"]);
    (api.api.get as jest.Mock).mockImplementation((path: string) => {
      if (path === "/api/calls/call-1/projects/") {
        return Promise.resolve(pageOf([]));
      }
      return Promise.resolve(pageOf(projectOptions));
    });

    renderWithQuery(<ProjectsManager callId="call-1" status="borrador" />);

    expect(await screen.findByText(/sin proyectos/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Vincular" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/proyecto a vincular/i)).not.toBeInTheDocument();
  });

  it("surfaces a 409 duplicate association via the Toaster", async () => {
    setAuthRoles(["director"]);
    mockProjectOptions();
    // The project is linkable in the picker but the server rejects the
    // association (already linked to another call) with a 409 detail.
    (api.api.post as jest.Mock).mockRejectedValue(
      Object.assign(new Error("El proyecto ya está asociado a una convocatoria."), {
        status: 409,
      }),
    );

    renderWithQuery(<ProjectsManager callId="call-1" status="abierta" />);

    const select = await screen.findByLabelText(/proyecto a vincular/i);
    await waitFor(() => {
      expect(select.querySelector('option[value="p2"]')).toBeTruthy();
    });
    fireEvent.change(select, { target: { value: "p2" } });
    fireEvent.click(screen.getByRole("button", { name: "Vincular" }));

    await waitFor(() => {
      expect(toastModule.toast.error).toHaveBeenCalledWith(
        "El proyecto ya está asociado a una convocatoria.",
      );
    });
  });

  it("unlinks a project after confirmation", async () => {
    setAuthRoles(["director"]);
    mockProjectOptions();
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    renderWithQuery(<ProjectsManager callId="call-1" status="abierta" />);

    fireEvent.click(await screen.findByRole("button", { name: /desvincular/i }));
    const dialog = await screen.findByRole("alertdialog");
    expect(dialog).toHaveTextContent(/¿Desvincular proyecto\?/);

    fireEvent.click(screen.getByRole("button", { name: "Desvincular" }));

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith(
        "/api/calls/call-1/projects/cp-1/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    expect(toastModule.toast.success).toHaveBeenCalled();
  });
});

// ─────────────────────────────────────────────────────────
// StateHistoryManager — read-only logs (task 2.3)
// ─────────────────────────────────────────────────────────

describe("StateHistoryManager", () => {
  it("renders state logs read-only with no action controls", async () => {
    setAuthRoles(["researcher"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([stateLog]));

    renderWithQuery(<StateHistoryManager callId="call-1" />);

    expect(await screen.findByText(/Borrador/)).toBeInTheDocument();
    expect(screen.getByText(/Abierta/)).toBeInTheDocument();
    expect(screen.getByText("Apertura oficial")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("renders an empty state when there are no logs", async () => {
    setAuthRoles(["director"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));

    renderWithQuery(<StateHistoryManager callId="call-1" />);

    expect(await screen.findByText(/Sin historial/i)).toBeInTheDocument();
  });
});

// ─────────────────────────────────────────────────────────
// DeleteCallButton — gated delete (task 2.4)
// ─────────────────────────────────────────────────────────

function makeCall(status: string) {
  return {
    id: "call-1",
    institution: "inst-1",
    title: "Convocatoria IA",
    description: "Descripción.",
    call_type: "internal",
    external_entity: "",
    submission_start: null,
    submission_end: null,
    evaluation_start: null,
    evaluation_end: null,
    status,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

describe("DeleteCallButton", () => {
  it("deletes a borrador call with zero projects after confirmation and redirects", async () => {
    setAuthRoles(["director"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    renderWithQuery(<DeleteCallButton call={makeCall("borrador")} />);

    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    const dialog = await screen.findByRole("alertdialog");
    expect(dialog).toHaveTextContent(/¿Eliminar convocatoria\?/);

    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith("/api/calls/call-1/");
    });
    expect(toastModule.toast.success).toHaveBeenCalled();
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/calls");
    });
  });

  it("is hidden for a call not in borrador", async () => {
    setAuthRoles(["director"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));

    renderWithQuery(<DeleteCallButton call={makeCall("abierta")} />);

    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Eliminar" })).not.toBeInTheDocument();
    });
  });

  it("is hidden when the call has linked projects", async () => {
    setAuthRoles(["director"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([linkedProject]));

    renderWithQuery(<DeleteCallButton call={makeCall("borrador")} />);

    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Eliminar" })).not.toBeInTheDocument();
    });
  });

  it("is hidden for non-manager roles", async () => {
    setAuthRoles(["researcher"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));

    renderWithQuery(<DeleteCallButton call={makeCall("borrador")} />);

    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Eliminar" })).not.toBeInTheDocument();
    });
  });

  it("surfaces a delete failure via the Toaster without redirecting", async () => {
    setAuthRoles(["director"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));
    (api.api.delete as jest.Mock).mockRejectedValue(
      Object.assign(new Error("No se puede eliminar."), { status: 400 }),
    );

    renderWithQuery(<DeleteCallButton call={makeCall("borrador")} />);

    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar" }));

    await waitFor(() => {
      expect(toastModule.toast.error).toHaveBeenCalledWith("No se puede eliminar.");
    });
    expect(mockPush).not.toHaveBeenCalled();
  });
});
