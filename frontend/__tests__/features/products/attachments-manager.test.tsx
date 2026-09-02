/**
 * AttachmentsManager — product attachments CRUD (RF-007).
 *
 * Spec (products-ui attachments):
 *   - Metadata-only {name, doc_type (free text ≤50), external_url (valid
 *     URL)}; no file upload; rendered as external links.
 *   - Invalid external_url / empty doc_type surface as field errors and
 *     no record is created.
 *   - Inline edit PATCHes the record; delete removes it.
 */

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

jest.mock("next/navigation", () => ({
  usePathname: () => "/products/prod-1",
  useParams: () => ({ id: "prod-1" }),
  useRouter: () => ({ push: jest.fn(), prefetch: jest.fn() }),
}));

jest.mock("next/link", () => {
  return {
    __esModule: true,
    default: ({ href, children }: { href: string; children: React.ReactNode }) => (
      <a href={href}>{children}</a>
    ),
  };
});

jest.mock("next-themes", () => ({
  useTheme: () => ({ theme: "light", setTheme: jest.fn(), themes: [] }),
}));

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
import { AttachmentsManager } from "@/features/products/AttachmentsManager";

const toastModule = jest.requireMock("sonner") as {
  toast: { success: jest.Mock; error: jest.Mock };
};

function attachment(id: string, name: string, doc_type: string, external_url: string) {
  return {
    id,
    product: "prod-1",
    name,
    doc_type,
    external_url,
    created_at: "2026-01-01T09:00:00Z",
  };
}

function pageOf<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results };
}

function setAuth() {
  useAuthStore.setState({
    roles: ["researcher"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });
}

function renderManager(
  getMock: (path: string) => Promise<unknown> = () => Promise.resolve(pageOf([])),
) {
  (api.api.get as jest.Mock).mockImplementation(getMock);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AttachmentsManager productId="prod-1" />
    </QueryClientProvider>,
  );
}

function defaultGet(rows: ReturnType<typeof attachment>[]) {
  return (path: string) => {
    if (path === "/api/products/prod-1/attachments/") return Promise.resolve(pageOf(rows));
    return Promise.resolve(pageOf([]));
  };
}

async function fillCreateForm(
  user: ReturnType<typeof userEvent.setup>,
  values: { name: string; doc_type: string; external_url: string },
) {
  await user.type(screen.getByLabelText(/^nombre/i), values.name);
  await user.type(screen.getByLabelText(/tipo de documento/i), values.doc_type);
  await user.type(screen.getByLabelText(/url externa/i), values.external_url);
}

beforeEach(() => {
  jest.clearAllMocks();
  setAuth();
});

describe("AttachmentsManager — list", () => {
  it("renders attachments as external links with their doc_type", async () => {
    renderManager(
      defaultGet([
        attachment("att-1", "Acta de aprobación", "Acta", "https://example.com/acta.pdf"),
      ]),
    );

    const link = await screen.findByRole("link", { name: "Acta de aprobación" });
    expect(link).toHaveAttribute("href", "https://example.com/acta.pdf");
    expect(screen.getByText("Acta")).toBeInTheDocument();
  });

  it("shows the empty state when the product has no attachments", async () => {
    renderManager(defaultGet([]));

    expect(await screen.findByText("Sin adjuntos.")).toBeInTheDocument();
  });
});

describe("AttachmentsManager — create", () => {
  it("POSTs the metadata payload and resets the form on success", async () => {
    const user = userEvent.setup();
    (api.api.post as jest.Mock).mockResolvedValue({ id: "att-9" });
    renderManager(defaultGet([]));
    await screen.findByText("Sin adjuntos.");

    await fillCreateForm(user, {
      name: "Acta de aprobación",
      doc_type: "Acta",
      external_url: "https://example.com/acta.pdf",
    });
    await user.click(screen.getByRole("button", { name: /añadir adjunto/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/products/prod-1/attachments/",
        {
          name: "Acta de aprobación",
          doc_type: "Acta",
          external_url: "https://example.com/acta.pdf",
        },
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(toastModule.toast.success).toHaveBeenCalledWith("Adjunto añadido.");
    });
    expect(screen.getByLabelText(/^nombre/i)).toHaveValue("");
  });

  it("surfaces a field error for a malformed external_url and does not POST", async () => {
    const user = userEvent.setup();
    renderManager(defaultGet([]));
    await screen.findByText("Sin adjuntos.");

    await fillCreateForm(user, {
      name: "Acta",
      doc_type: "Acta",
      external_url: "not-a-url",
    });
    await user.click(screen.getByRole("button", { name: /añadir adjunto/i }));

    expect(await screen.findByText(/la url externa debe ser válida/i)).toBeInTheDocument();
    expect(api.api.post).not.toHaveBeenCalled();
  });

  it("surfaces a field error for an empty doc_type and does not POST", async () => {
    const user = userEvent.setup();
    renderManager(defaultGet([]));
    await screen.findByText("Sin adjuntos.");

    await user.type(screen.getByLabelText(/^nombre/i), "Acta");
    await user.type(screen.getByLabelText(/url externa/i), "https://example.com/a.pdf");
    await user.click(screen.getByRole("button", { name: /añadir adjunto/i }));

    expect(await screen.findByText(/el tipo de documento es obligatorio/i)).toBeInTheDocument();
    expect(api.api.post).not.toHaveBeenCalled();
  });

  it("rejects a doc_type longer than 50 characters", async () => {
    const user = userEvent.setup();
    renderManager(defaultGet([]));
    await screen.findByText("Sin adjuntos.");

    await fillCreateForm(user, {
      name: "Acta",
      doc_type: "x".repeat(51),
      external_url: "https://example.com/a.pdf",
    });
    await user.click(screen.getByRole("button", { name: /añadir adjunto/i }));

    expect(await screen.findByText(/no puede superar 50 caracteres/i)).toBeInTheDocument();
    expect(api.api.post).not.toHaveBeenCalled();
  });
});

describe("AttachmentsManager — edit and delete", () => {
  it("edits an attachment inline and PATCHes the updated values", async () => {
    const user = userEvent.setup();
    (api.api.patch as jest.Mock).mockResolvedValue({ ok: true });
    renderManager(defaultGet([attachment("att-1", "Acta", "Acta", "https://example.com/a.pdf")]));
    await screen.findByRole("link", { name: "Acta" });

    await user.click(screen.getByRole("button", { name: /editar/i }));
    const editRow = screen.getByRole("button", { name: /guardar/i }).closest("li");
    expect(editRow).not.toBeNull();
    const nameInput = within(editRow as HTMLLIElement).getByLabelText(/^nombre/i);
    await user.clear(nameInput);
    await user.type(nameInput, "Acta actualizada");
    await user.click(screen.getByRole("button", { name: /guardar/i }));

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/products/prod-1/attachments/att-1/",
        expect.objectContaining({ name: "Acta actualizada" }),
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
  });

  it("deletes an attachment and confirms via Toaster", async () => {
    const user = userEvent.setup();
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);
    renderManager(defaultGet([attachment("att-1", "Acta", "Acta", "https://example.com/a.pdf")]));
    await screen.findByRole("link", { name: "Acta" });

    await user.click(screen.getByRole("button", { name: /eliminar/i }));

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith(
        "/api/products/prod-1/attachments/att-1/",
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => {
      expect(toastModule.toast.success).toHaveBeenCalledWith("Adjunto eliminado.");
    });
  });
});
