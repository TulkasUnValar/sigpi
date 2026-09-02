/**
 * /products/{id}/edit — edit product page (RF-004).
 *
 * Spec (products-ui edit):
 *   - The form prefills from the detail and PATCHes /api/products/{id}/
 *     with the same zod rules and 6-state restriction as create.
 *   - Institution and audit fields are read-only.
 *   - A 403 (linked project became disallowed) surfaces via Toaster,
 *     refreshes the project options, and does not redirect.
 *   - Invalid publication_year surfaces as a field error; no PATCH occurs.
 *   - Success redirects to the detail page.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

const mockPush = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => "/products/prod-1/edit",
  useParams: () => ({ id: "prod-1" }),
  useRouter: () => ({ push: mockPush, prefetch: jest.fn() }),
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
import { ApiError } from "@/lib/errors";
import EditProductPage from "@/app/products/[id]/edit/page";

const toastModule = jest.requireMock("sonner") as {
  toast: { success: jest.Mock; error: jest.Mock };
};

const product = {
  id: "prod-1",
  institution: "inst-1",
  project: "p3",
  title: "Artículo IA 2025",
  description: "Aplicaciones de inteligencia artificial en agricultura.",
  type: "articulo",
  publication_year: 2025,
  created_at: "2026-01-10T09:00:00Z",
  updated_at: "2026-01-10T09:00:00Z",
  created_by: "u1",
  updated_by: "u2",
};

const projects = [
  {
    id: "p3",
    title: "Proyecto Gamma",
    status: "aprobado",
    center: "c2",
    principal_investigator: "r2",
    start_date: "2026-01-20",
    created_at: "2026-01-10T00:00:00Z",
  },
];

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

function renderPage(
  getMock: (path: string) => Promise<unknown> = () => Promise.resolve(pageOf([])),
) {
  (api.api.get as jest.Mock).mockImplementation(getMock);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <EditProductPage />
    </QueryClientProvider>,
  );
}

function defaultGet() {
  return (path: string) => {
    if (path === "/api/products/prod-1/") return Promise.resolve(product);
    if (path === "/api/projects/") return Promise.resolve(pageOf(projects));
    return Promise.resolve(pageOf([]));
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  setAuth();
  mockPush.mockClear();
});

describe("/products/[id]/edit — prefill and read-only fields", () => {
  it("prefills the writable fields from the detail", async () => {
    renderPage(defaultGet());

    expect(await screen.findByLabelText(/título/i)).toHaveValue("Artículo IA 2025");
    expect(screen.getByLabelText(/descripción/i)).toHaveValue(
      "Aplicaciones de inteligencia artificial en agricultura.",
    );
    expect(screen.getByLabelText(/año de publicación/i)).toHaveValue(2025);
    expect(screen.getByRole("combobox", { name: /tipo de producto/i })).toHaveTextContent(
      "Artículo",
    );
  });

  it("renders the institution and audit fields as read-only", async () => {
    renderPage(defaultGet());

    const institution = await screen.findByLabelText(/institución/i);
    expect(institution).toBeDisabled();
    expect(institution).toHaveValue("inst-1");

    const createdBy = screen.getByLabelText(/creado por/i);
    expect(createdBy).toBeDisabled();
    expect(createdBy).toHaveValue("u1");

    const updatedBy = screen.getByLabelText(/actualizado por/i);
    expect(updatedBy).toBeDisabled();
    expect(updatedBy).toHaveValue("u2");
  });
});

describe("/products/[id]/edit — save", () => {
  it("PATCHes the writable payload and redirects to the detail", async () => {
    const user = userEvent.setup();
    (api.api.patch as jest.Mock).mockResolvedValue({ ...product, title: "Artículo IA 2026" });
    renderPage(defaultGet());
    await screen.findByLabelText(/título/i);

    await user.click(screen.getByRole("button", { name: /guardar cambios/i }));

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/products/prod-1/",
        expect.objectContaining({
          project: "p3",
          title: "Artículo IA 2025",
          description: "Aplicaciones de inteligencia artificial en agricultura.",
          type: "articulo",
          publication_year: 2025,
        }),
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/products/prod-1"));
  });

  it("surfaces a field error for an out-of-range publication_year and does not PATCH", async () => {
    const user = userEvent.setup();
    renderPage(defaultGet());
    const yearInput = await screen.findByLabelText(/año de publicación/i);

    await user.clear(yearInput);
    await user.type(yearInput, "1899");
    await user.click(screen.getByRole("button", { name: /guardar cambios/i }));

    expect(await screen.findByText(/1900 o posterior/i)).toBeInTheDocument();
    expect(api.api.patch).not.toHaveBeenCalled();
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("shows a toast and refreshes project options on a 403 disallowed state", async () => {
    const user = userEvent.setup();
    (api.api.patch as jest.Mock).mockRejectedValue(
      new ApiError("Products can only be linked to approved or active projects.", 403),
    );
    renderPage(defaultGet());
    await screen.findByLabelText(/título/i);

    await user.click(screen.getByRole("button", { name: /guardar cambios/i }));

    await waitFor(() => {
      expect(toastModule.toast.error).toHaveBeenCalledWith(
        "Products can only be linked to approved or active projects.",
      );
    });
    expect(mockPush).not.toHaveBeenCalled();

    await waitFor(() => {
      const projectCalls = (api.api.get as jest.Mock).mock.calls.filter(
        (c: unknown[]) => c[0] === "/api/projects/",
      );
      expect(projectCalls.length).toBeGreaterThanOrEqual(2);
    });
  });
});
