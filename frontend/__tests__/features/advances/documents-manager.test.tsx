/**
 * Advances DocumentsManager — metadata-only document CRUD (RF-042).
 *
 * Spec (RF-042 S5–S6):
 *   - A borrador advance viewed by its creator can add documents with
 *     name/doc_type/external_url; the list refreshes after mutations.
 *   - Rows render only metadata as external links; no file-upload widget
 *     exists.
 *   - Writes are gated to borrador + creator (backend remains backstop).
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";
import type { AuthUser } from "@/lib/api";

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
import { DocumentsManager } from "@/features/advances/DocumentsManager";

const toastModule = jest.requireMock("sonner") as {
  toast: { success: jest.Mock; error: jest.Mock };
};

function pageOf<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results };
}

function makeUser(id: string): AuthUser {
  return {
    id,
    email: `${id}@example.com`,
    auth_source: "keycloak",
    is_superuser: false,
    is_active: true,
    active_institution_id: "inst-1",
    active_role: "researcher",
    memberships: [],
  };
}

function setAuth(userId: string, roles: string[]) {
  useAuthStore.setState({
    user: makeUser(userId),
    roles,
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
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
  progress_report: "a1",
  name: "Registro de datos.xlsx",
  doc_type: "evidence",
  external_url: "https://example.com/d1",
  uploaded_at: "2026-04-10T00:00:00Z",
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe("DocumentsManager — rendering (RF-042 S6)", () => {
  it("renders document metadata rows as external links with the Spanish label", async () => {
    setAuth("r2", ["researcher"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([docFixture]));

    renderWithQuery(<DocumentsManager advanceId="a1" status="borrador" createdBy="r2" />);

    expect(await screen.findByText("Registro de datos.xlsx")).toBeInTheDocument();
    expect(screen.getByText("Evidencia")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Registro de datos.xlsx" })).toHaveAttribute(
      "href",
      "https://example.com/d1",
    );
  });

  it("offers no file-upload control, only metadata fields", async () => {
    setAuth("r2", ["researcher"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));

    renderWithQuery(<DocumentsManager advanceId="a1" status="borrador" createdBy="r2" />);
    fireEvent.click(await screen.findByRole("button", { name: "Agregar documento" }));

    expect(screen.getByLabelText(/nombre/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/tipo de documento/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/url externa/i)).toBeInTheDocument();
    expect(document.querySelector('input[type="file"]')).toBeNull();
    expect(screen.queryByLabelText(/archivo/i)).not.toBeInTheDocument();
  });
});

describe("DocumentsManager — CRUD (RF-042 S5)", () => {
  it("adds a document capturing only metadata fields and refreshes the list", async () => {
    setAuth("r2", ["researcher"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([]));
    (api.api.post as jest.Mock).mockResolvedValue(docFixture);

    renderWithQuery(<DocumentsManager advanceId="a1" status="borrador" createdBy="r2" />);
    fireEvent.click(await screen.findByRole("button", { name: "Agregar documento" }));

    fireEvent.change(screen.getByLabelText(/nombre/i), {
      target: { value: "Registro de datos.xlsx" },
    });
    fireEvent.change(screen.getByLabelText(/url externa/i), {
      target: { value: "https://example.com/d1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Guardar documento" }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/progress/a1/documents/",
        expect.objectContaining({
          name: "Registro de datos.xlsx",
          doc_type: "evidence",
          external_url: "https://example.com/d1",
        }),
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    expect(toastModule.toast.success).toHaveBeenCalledWith("Documento agregado.");

    // Mutation invalidates the advances root → documents query refetches.
    await waitFor(() => {
      expect(api.api.get).toHaveBeenCalledWith(
        "/api/progress/a1/documents/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    expect(api.api.get).toHaveBeenCalledTimes(2);
  });

  it("edits a document's metadata via the dialog", async () => {
    setAuth("r2", ["researcher"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([docFixture]));
    (api.api.patch as jest.Mock).mockResolvedValue({ ...docFixture, name: "Registro v2" });

    renderWithQuery(<DocumentsManager advanceId="a1" status="borrador" createdBy="r2" />);
    fireEvent.click(await screen.findByRole("button", { name: /editar/i }));

    fireEvent.change(await screen.findByLabelText(/nombre/i), {
      target: { value: "Registro v2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Guardar documento" }));

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/progress/a1/documents/doc-1/",
        expect.objectContaining({ name: "Registro v2" }),
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    expect(toastModule.toast.success).toHaveBeenCalledWith("Documento actualizado.");
  });

  it("deletes a document after a ConfirmDialog confirmation", async () => {
    setAuth("r2", ["researcher"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([docFixture]));
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    renderWithQuery(<DocumentsManager advanceId="a1" status="borrador" createdBy="r2" />);
    fireEvent.click(await screen.findByRole("button", { name: /eliminar/i }));

    const dialog = await screen.findByRole("alertdialog");
    expect(dialog).toHaveTextContent(/¿Eliminar documento\?/);

    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith(
        "/api/progress/a1/documents/doc-1/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    expect(toastModule.toast.success).toHaveBeenCalledWith("Documento eliminado.");
  });
});

describe("DocumentsManager — gated writes (RF-042 S5)", () => {
  it("hides write controls for a non-creator", async () => {
    setAuth("u9", ["researcher"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([docFixture]));

    renderWithQuery(<DocumentsManager advanceId="a1" status="borrador" createdBy="r2" />);

    expect(await screen.findByText("Registro de datos.xlsx")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Agregar documento" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /editar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /eliminar/i })).not.toBeInTheDocument();
  });

  it("hides write controls outside borrador", async () => {
    setAuth("r2", ["researcher"]);
    (api.api.get as jest.Mock).mockResolvedValue(pageOf([docFixture]));

    renderWithQuery(<DocumentsManager advanceId="a1" status="en_revision" createdBy="r2" />);

    expect(await screen.findByText("Registro de datos.xlsx")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Agregar documento" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /editar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /eliminar/i })).not.toBeInTheDocument();
  });
});
