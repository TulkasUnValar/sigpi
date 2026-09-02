/**
 * /products/{id} — product detail page (RF-003).
 *
 * Spec (products-ui detail):
 *   - The page loads the product detail and renders header + three tabs
 *     (Resumen / Autores / Adjuntos).
 *   - Overview shows title, type badge (Spanish label), description,
 *     publication_year, and a link to the linked project.
 *   - A 404 detail surfaces via Toaster.
 *   - Loading renders skeletons; a missing product renders an empty state.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

const mockPush = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => "/products/prod-1",
  useParams: () => ({ id: "prod-1" }),
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
import ProductDetailPage from "@/app/products/[id]/page";

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
  updated_by: null,
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

/** Default get mock: detail, projects, empty nested lists. */
function defaultGet(path: string) {
  if (path === "/api/products/prod-1/") return Promise.resolve(product);
  if (path === "/api/projects/") return Promise.resolve(pageOf(projects));
  if (path.startsWith("/api/products/prod-1/authors/")) {
    return Promise.resolve(pageOf([]));
  }
  if (path.startsWith("/api/products/prod-1/attachments/")) {
    return Promise.resolve(pageOf([]));
  }
  if (path === "/api/researchers/") return Promise.resolve(pageOf([]));
  return Promise.resolve(pageOf([]));
}

function renderPage(getMock: (path: string) => Promise<unknown> = defaultGet) {
  (api.api.get as jest.Mock).mockImplementation(getMock);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ProductDetailPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  setAuth();
});

describe("/products/[id] — header and overview tab", () => {
  it("renders the header title, edit link and delete action", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "Artículo IA 2025" })).toBeInTheDocument();
    const edit = screen.getByRole("link", { name: "Editar" });
    expect(edit).toHaveAttribute("href", "/products/prod-1/edit");
    expect(screen.getByRole("button", { name: /eliminar/i })).toBeInTheDocument();
  });

  it("renders the three tabs with the Overview data", async () => {
    renderPage();

    expect(await screen.findByRole("tab", { name: "Resumen" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Autores" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Adjuntos" })).toBeInTheDocument();

    // Overview fields: type badge (Spanish label), description, year.
    expect(screen.getByText("Artículo")).toBeInTheDocument();
    expect(
      screen.getByText("Aplicaciones de inteligencia artificial en agricultura."),
    ).toBeInTheDocument();
    expect(screen.getByText("2025")).toBeInTheDocument();
  });

  it("links the overview to the linked project using its title", async () => {
    renderPage();

    const projectLink = await screen.findByRole("link", { name: "Proyecto Gamma" });
    expect(projectLink).toHaveAttribute("href", "/projects/p3");
  });

  it("mounts the authors and attachments managers from their tabs", async () => {
    const user = userEvent.setup();
    renderPage();
    expect(await screen.findByRole("tab", { name: "Autores" })).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Autores" }));
    expect(await screen.findByText("Sin autores.")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Adjuntos" }));
    expect(await screen.findByText("Sin adjuntos.")).toBeInTheDocument();
  });
});

describe("/products/[id] — error and empty states", () => {
  it("shows skeletons while the detail query loads", () => {
    renderPage(() => new Promise(() => undefined));

    expect(screen.getByRole("status", { name: /cargando/i })).toBeInTheDocument();
  });

  it("surfaces a 404 via Toaster and renders the not-found empty state", async () => {
    renderPage(() => Promise.reject(new ApiError("Producto no encontrado.", 404)));

    await waitFor(() => {
      expect(toastModule.toast.error).toHaveBeenCalledWith("Producto no encontrado.");
    });
    expect(await screen.findByText("Producto no encontrado")).toBeInTheDocument();
    expect(screen.queryByRole("tab")).not.toBeInTheDocument();
  });

  it("renders the not-found empty state when the detail is missing", async () => {
    renderPage(() => Promise.resolve(undefined));

    expect(await screen.findByText("Producto no encontrado")).toBeInTheDocument();
  });
});
