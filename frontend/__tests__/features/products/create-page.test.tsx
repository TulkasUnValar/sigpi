/**
 * /products/new — create product page.
 *
 * Spec (products-ui create / RF-002):
 *   - zod validates title/type/publication_year before POST.
 *   - The project select is filtered client-side to ALLOWED_PROJECT_STATES.
 *   - Success POSTs /api/products/ and redirects to /products/{id}.
 *   - 403 (disallowed project state) surfaces via Toaster and refreshes the
 *     project options; no redirect occurs.
 *   - 400 field errors map into RHF via setError.
 */

import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

const mockPush = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => "/products/new",
  useParams: () => ({}),
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
import NewProductPage from "@/app/products/new/page";

const toastModule = jest.requireMock("sonner") as {
  toast: { success: jest.Mock; error: jest.Mock };
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
  {
    id: "p1",
    title: "Proyecto Alpha",
    status: "en_revision",
    center: "c1",
    principal_investigator: "r1",
    start_date: "2026-01-10",
    created_at: "2026-01-01T00:00:00Z",
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

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <NewProductPage />
    </QueryClientProvider>,
  );
}

/** Fill every field with a valid payload (project p3 is in an allowed state). */
async function fillValidForm() {
  await userEvent.type(screen.getByLabelText(/título/i), "Artículo de IA");
  await userEvent.type(screen.getByLabelText(/descripción/i), "Investigación aplicada.");
  fireEvent.click(screen.getByLabelText(/tipo de producto/i));
  fireEvent.click(await screen.findByRole("option", { name: "Artículo" }));
  fireEvent.click(await screen.findByLabelText(/proyecto/i));
  fireEvent.click(await screen.findByRole("option", { name: "Proyecto Gamma" }));
  const yearInput = screen.getByLabelText(/año de publicación/i);
  await userEvent.clear(yearInput);
  await userEvent.type(yearInput, "2024");
}

beforeEach(() => {
  jest.clearAllMocks();
  setAuth();
  (api.api.get as jest.Mock).mockResolvedValue(pageOf(projects));
});

describe("/products/new — create form", () => {
  it("renders the create form fields", async () => {
    renderPage();

    expect(screen.getByLabelText(/título/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/descripción/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/tipo de producto/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/año de publicación/i)).toBeInTheDocument();
  });

  it("filters the project select to ALLOWED_PROJECT_STATES", async () => {
    renderPage();

    fireEvent.click(await screen.findByLabelText(/proyecto/i));
    expect(await screen.findByRole("option", { name: "Proyecto Gamma" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Proyecto Alpha" })).not.toBeInTheDocument();
  });

  it("submits a valid product and redirects to /products/{id}", async () => {
    (api.api.post as jest.Mock).mockResolvedValue({
      id: "prod-9",
      institution: "inst-1",
      project: "p3",
      title: "Artículo de IA",
      description: "Investigación aplicada.",
      type: "articulo",
      publication_year: 2024,
      created_at: "2026-02-01T00:00:00Z",
      updated_at: "2026-02-01T00:00:00Z",
      created_by: null,
      updated_by: null,
    });

    renderPage();
    await fillValidForm();

    fireEvent.click(screen.getByRole("button", { name: /crear producto/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/products/",
        expect.objectContaining({
          title: "Artículo de IA",
          type: "articulo",
          project: "p3",
          publication_year: 2024,
        }),
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/products/prod-9"));
  });

  it("surfaces a field error for an out-of-range publication_year and does not submit", async () => {
    renderPage();
    await fillValidForm();

    const yearInput = screen.getByLabelText(/año de publicación/i);
    await userEvent.clear(yearInput);
    await userEvent.type(yearInput, "1899");
    fireEvent.click(screen.getByRole("button", { name: /crear producto/i }));

    expect(await screen.findByText(/1900 o posterior/i)).toBeInTheDocument();
    expect(api.api.post).not.toHaveBeenCalled();
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("maps 400 field errors from the server into RHF setError", async () => {
    (api.api.post as jest.Mock).mockRejectedValue(
      new ApiError("Bad request.", 400, {
        title: ["El título ya existe en esta institución."],
      }),
    );

    renderPage();
    await fillValidForm();
    fireEvent.click(screen.getByRole("button", { name: /crear producto/i }));

    expect(await screen.findByText("El título ya existe en esta institución.")).toBeInTheDocument();
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("shows a toast and refreshes project options on a 403 disallowed project state", async () => {
    (api.api.post as jest.Mock).mockRejectedValue(
      new ApiError("Products can only be linked to approved or active projects.", 403),
    );

    renderPage();
    await fillValidForm();
    fireEvent.click(screen.getByRole("button", { name: /crear producto/i }));

    await waitFor(() => {
      expect(toastModule.toast.error).toHaveBeenCalledWith(
        "Products can only be linked to approved or active projects.",
      );
    });
    expect(mockPush).not.toHaveBeenCalled();

    // Options refresh: the projects list is refetched after the 403.
    await waitFor(() => {
      const projectCalls = (api.api.get as jest.Mock).mock.calls.filter(
        (c: unknown[]) => c[0] === "/api/projects/",
      );
      expect(projectCalls.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("shows a toast when a non-field create error occurs", async () => {
    (api.api.post as jest.Mock).mockRejectedValue(new ApiError("Error de servidor.", 500));

    renderPage();
    await fillValidForm();
    fireEvent.click(screen.getByRole("button", { name: /crear producto/i }));

    await waitFor(() => {
      expect(toastModule.toast.error).toHaveBeenCalledWith("Error de servidor.");
    });
    expect(mockPush).not.toHaveBeenCalled();
  });
});
