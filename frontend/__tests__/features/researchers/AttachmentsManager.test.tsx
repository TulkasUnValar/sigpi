/**
 * AttachmentsManager — inline create/delete for metadata-only attachments.
 *
 * Spec (researchers-ui attachments):
 *   - Metadata only {name, type (cv|certificate|photo|other), external_url},
 *     no file upload.
 *   - Rendered as an external link.
 *   - Nested POST/DELETE /attachments/.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

jest.mock("sonner", () => ({
  toast: { success: jest.fn(), error: jest.fn() },
}));

import * as api from "@/lib/api";
import { AttachmentsManager } from "@/features/researchers/AttachmentsManager";

function resetAuth() {
  useAuthStore.setState({
    roles: ["admin"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Nacional" },
    institutions: [],
    centers: [],
  });
}

function renderManager() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AttachmentsManager researcherId="r-1" />
    </QueryClientProvider>,
  );
}

const att1 = {
  id: "att-1",
  researcher: "r-1",
  name: "Hoja de vida",
  type: "cv",
  external_url: "https://example.com/cv-ana.pdf",
  created_at: "2026-01-01T00:00:00Z",
};

beforeEach(() => {
  jest.clearAllMocks();
  resetAuth();
  (api.api.get as jest.Mock).mockImplementation((url: string) => {
    if (url.startsWith("/api/researchers/r-1/attachments")) {
      return Promise.resolve({ count: 0, next: null, previous: null, results: [] });
    }
    return Promise.resolve({ count: 0, next: null, previous: null, results: [] });
  });
});

describe("AttachmentsManager", () => {
  it("renders existing attachments as external links", async () => {
    (api.api.get as jest.Mock).mockImplementation((url: string) => {
      if (url.startsWith("/api/researchers/r-1/attachments")) {
        return Promise.resolve({ count: 1, next: null, previous: null, results: [att1] });
      }
      return Promise.resolve({ count: 0, next: null, previous: null, results: [] });
    });

    renderManager();

    const link = await screen.findByRole("link", { name: "Hoja de vida" });
    expect(link).toHaveAttribute("href", "https://example.com/cv-ana.pdf");
  });

  it("shows an empty state when no attachments exist", async () => {
    renderManager();

    expect(await screen.findByText(/sin adjuntos/i)).toBeInTheDocument();
  });

  it("POSTs a metadata-only attachment and clears the form", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({ ...att1, id: "att-2", type: "certificate" });

    renderManager();

    await screen.findByText(/sin adjuntos/i);
    await userEvent.type(screen.getByLabelText(/nombre/i), "Certificado académico");
    await userEvent.selectOptions(screen.getByLabelText(/tipo/i), "certificate");
    await userEvent.type(screen.getByLabelText(/url/i), "https://example.com/c.pdf");
    await userEvent.click(screen.getByRole("button", { name: /añadir adjunto/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/researchers/r-1/attachments/",
        expect.objectContaining({
          name: "Certificado académico",
          type: "certificate",
          external_url: "https://example.com/c.pdf",
        }),
        expect.anything(),
      );
    });
    await waitFor(() => {
      expect((screen.getByLabelText(/nombre/i) as HTMLInputElement).value).toBe("");
    });
  });

  it("disables the create button until name, type and url are provided", async () => {
    renderManager();

    await screen.findByText(/sin adjuntos/i);
    const button = screen.getByRole("button", { name: /añadir adjunto/i });
    expect(button).toBeDisabled();

    await userEvent.type(screen.getByLabelText(/nombre/i), "Certificado");
    await userEvent.selectOptions(screen.getByLabelText(/tipo/i), "cv");
    expect(screen.getByRole("button", { name: /añadir adjunto/i })).toBeDisabled();

    await userEvent.type(screen.getByLabelText(/url/i), "https://example.com/cv.pdf");
    expect(screen.getByRole("button", { name: /añadir adjunto/i })).not.toBeDisabled();
  });

  it("DELETEs an attachment", async () => {
    (api.api.get as jest.Mock).mockImplementation((url: string) => {
      if (url.startsWith("/api/researchers/r-1/attachments")) {
        return Promise.resolve({ count: 1, next: null, previous: null, results: [att1] });
      }
      return Promise.resolve({ count: 0, next: null, previous: null, results: [] });
    });
    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    renderManager();

    await screen.findByRole("link", { name: "Hoja de vida" });
    await userEvent.click(screen.getByRole("button", { name: /eliminar/i }));

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith("/api/researchers/r-1/attachments/att-1/", {
        institutionId: "inst-1",
      });
    });
  });
});
