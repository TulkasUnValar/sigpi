/**
 * ProductList — paginated products table with filter bar and ordering.
 *
 * Spec (products-ui list / RF-001):
 *   - Rows render title, Spanish type label, publication_year, project, created_at.
 *   - Ordering is offered for title, publication_year and created_at.
 *   - Filters: type, year, year__gte, year__lte, project, researcher, center,
 *     group, line — "Todos" clears a filter; changes refetch and reset page 1.
 *   - Project/researcher/center/group/line are selects fed by the
 *     projects/researchers/hierarchy hooks; center→group→line refresh
 *     dependently and stale selections clear.
 *   - Filter state round-trips through the URL query string: /products
 *     restores filters from the URL and every change rewrites it.
 *   - Empty/loading/error states; the create action is available to every role.
 */

import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

/** Mutable URL params backing the mocked useSearchParams (round-trip). */
let mockUrlParams = new URLSearchParams();
let mockRerender: () => void = () => {};

jest.mock("next/navigation", () => {
  const React = jest.requireActual<typeof import("react")>("react");
  return {
    useSearchParams: () => {
      const [, setTick] = React.useState(0);
      mockRerender = () => setTick((t: number) => t + 1);
      return mockUrlParams;
    },
    useRouter: () => ({
      replace: (href: string) => {
        const qs = href.split("?")[1] ?? "";
        mockUrlParams = new URLSearchParams(qs);
        mockRerender();
      },
      push: jest.fn(),
      prefetch: jest.fn(),
    }),
  };
});

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
import { ProductList } from "@/features/products/ProductList";

function makeProduct(id: string, type = "articulo", year = 2024) {
  return {
    id,
    title: `Producto ${id}`,
    type,
    publication_year: year,
    project: "p3",
    created_at: "2026-01-01T09:00:00Z",
  };
}

function pageOf<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results };
}

/** Option rows served to the filter selects (projects/researchers/hierarchy). */
const projectOptions = [
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
    status: "aprobado",
    center: "c2",
    principal_investigator: "r2",
    start_date: "2026-01-20",
    created_at: "2026-01-10T00:00:00Z",
  },
];
const researcherOptions = [
  {
    id: "r-1",
    full_name: "Ana Pérez",
    institution: "inst-1",
    is_active: true,
    completeness_score: 100,
  },
  {
    id: "r-2",
    full_name: "Luis Gómez",
    institution: "inst-1",
    is_active: true,
    completeness_score: 40,
  },
];
const centerOptions = [
  { id: "center-1", name: "Centro de Inteligencia Artificial" },
  { id: "center-2", name: "Centro de Energía" },
];
const groupOptions = [{ id: "group-1", name: "Grupo de Machine Learning" }];
const lineOptions = [{ id: "line-1", name: "Línea de Deep Learning" }];

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

function renderList(getMock: (path: string) => Promise<unknown>) {
  (api.api.get as jest.Mock).mockImplementation((path: string) => {
    if (path.includes("/api/projects/")) return Promise.resolve(pageOf(projectOptions));
    if (path.includes("/api/researchers/")) return Promise.resolve(pageOf(researcherOptions));
    if (path.includes("/api/institutions/") && path.includes("/centers/"))
      return Promise.resolve(centerOptions);
    if (path.includes("/api/centers/") && path.includes("/groups/"))
      return Promise.resolve(groupOptions);
    if (path.includes("/api/groups/") && path.includes("/lines/"))
      return Promise.resolve(lineOptions);
    return getMock(path);
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ProductList />
    </QueryClientProvider>,
  );
}

/** Open a Radix Select by trigger label and pick an option. */
async function pickOption(triggerName: RegExp, optionName: RegExp) {
  fireEvent.click(screen.getByRole("combobox", { name: triggerName }));
  fireEvent.click(await screen.findByRole("option", { name: optionName }));
}

/** Path of the most recent products-list api.get call (option queries excluded). */
function lastGetPath(): string {
  const calls = (api.api.get as jest.Mock).mock.calls as [string][];
  const productsCalls = calls.filter(([path]) => path.includes("/api/products/"));
  return productsCalls[productsCalls.length - 1]?.[0] ?? "";
}

beforeEach(() => {
  jest.clearAllMocks();
  mockUrlParams = new URLSearchParams();
});

describe("ProductList — paginated rows", () => {
  it("renders title, Spanish type label, year, project and created date", async () => {
    setAuthRoles(["researcher"]);
    renderList(() => Promise.resolve(pageOf([makeProduct("p1", "software", 2024)])));

    expect(await screen.findByText("Producto p1")).toBeInTheDocument();
    expect(screen.getByText("Software")).toBeInTheDocument();
    expect(screen.getByText("2024")).toBeInTheDocument();
    expect(screen.getByText("p3")).toBeInTheDocument();
    expect(screen.getByText("2026-01-01")).toBeInTheDocument();
  });

  it("follows the next link and requests page 2", async () => {
    setAuthRoles(["researcher"]);
    const page1 = {
      count: 26,
      next: "http://localhost:8000/api/products/?page=2",
      previous: null,
      results: [makeProduct("a1")],
    };
    const page2 = {
      count: 26,
      next: null,
      previous: "http://localhost:8000/api/products/?page=1",
      results: [makeProduct("b1")],
    };
    const getMock = jest.fn((path: string) =>
      Promise.resolve(path.includes("page=2") ? page2 : page1),
    );

    renderList(getMock);
    expect(await screen.findByText("Producto a1")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /siguiente/i }));
    expect(await screen.findByText("Producto b1")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /anterior/i }));
    expect(await screen.findByText("Producto a1")).toBeInTheDocument();
  });
});

describe("ProductList — ordering", () => {
  it("toggles title ordering asc → desc → none", async () => {
    setAuthRoles(["researcher"]);
    renderList(() => Promise.resolve(pageOf([makeProduct("a1")])));
    expect(await screen.findByText("Producto a1")).toBeInTheDocument();

    // Each click changes the query key, so wait for the table to re-render
    // (the new query starts in loading) before asserting the refetch.
    fireEvent.click(screen.getByRole("button", { name: "Ordenar por título" }));
    await screen.findByRole("button", { name: "Ordenar por título" });
    await waitFor(() => expect(lastGetPath()).toContain("ordering=title"));

    fireEvent.click(screen.getByRole("button", { name: "Ordenar por título" }));
    await screen.findByRole("button", { name: "Ordenar por título" });
    await waitFor(() => expect(lastGetPath()).toContain("ordering=-title"));

    fireEvent.click(screen.getByRole("button", { name: "Ordenar por título" }));
    await screen.findByRole("button", { name: "Ordenar por título" });
    await waitFor(() => expect(lastGetPath()).not.toContain("ordering="));
  });

  it("offers ordering controls for publication_year and created_at", async () => {
    setAuthRoles(["researcher"]);
    renderList(() => Promise.resolve(pageOf([makeProduct("a1")])));
    expect(await screen.findByText("Producto a1")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Ordenar por año" }));
    await screen.findByRole("button", { name: "Ordenar por año" });
    await waitFor(() => expect(lastGetPath()).toContain("ordering=publication_year"));

    fireEvent.click(screen.getByRole("button", { name: "Ordenar por fecha de creación" }));
    await screen.findByRole("button", { name: "Ordenar por fecha de creación" });
    await waitFor(() => expect(lastGetPath()).toContain("ordering=created_at"));
  });
});

describe("ProductList — filter refetch wiring", () => {
  it("refetches with ?type=articulo when the type filter is selected", async () => {
    setAuthRoles(["researcher"]);
    const getMock = jest.fn((path: string) => {
      if (path.includes("type=articulo")) {
        return Promise.resolve(pageOf([makeProduct("art-1", "articulo")]));
      }
      return Promise.resolve(pageOf([makeProduct("lib-1", "libro")]));
    });
    renderList(getMock);
    expect(await screen.findByText("Producto lib-1")).toBeInTheDocument();

    await pickOption(/tipo de producto/i, /^Artículo$/);

    expect(await screen.findByText("Producto art-1")).toBeInTheDocument();
    expect(screen.queryByText("Producto lib-1")).not.toBeInTheDocument();
    expect(lastGetPath()).toContain("type=articulo");
  });

  it("refetches with the year range when Desde/Hasta are set", async () => {
    setAuthRoles(["researcher"]);
    const getMock = jest.fn((path: string) => {
      if (path.includes("year__gte=2024") && path.includes("year__lte=2025")) {
        return Promise.resolve(pageOf([makeProduct("m1", "articulo", 2024)]));
      }
      return Promise.resolve(pageOf([makeProduct("o1", "articulo", 2023)]));
    });
    renderList(getMock);
    expect(await screen.findByText("Producto o1")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/año desde/i), { target: { value: "2024" } });
    fireEvent.change(screen.getByLabelText(/año hasta/i), { target: { value: "2025" } });

    expect(await screen.findByText("Producto m1")).toBeInTheDocument();
    const last = lastGetPath();
    expect(last).toContain("year__gte=2024");
    expect(last).toContain("year__lte=2025");
  });

  it("combines the type and year-range filters in a single refetch", async () => {
    setAuthRoles(["researcher"]);
    const getMock = jest.fn((path: string) => {
      if (
        path.includes("type=articulo") &&
        path.includes("year__gte=2024") &&
        path.includes("year__lte=2025")
      ) {
        return Promise.resolve(pageOf([makeProduct("match-1", "articulo", 2024)]));
      }
      return Promise.resolve(pageOf([makeProduct("c1", "libro", 2023)]));
    });
    renderList(getMock);
    expect(await screen.findByText("Producto c1")).toBeInTheDocument();

    await pickOption(/tipo de producto/i, /^Artículo$/);
    fireEvent.change(screen.getByLabelText(/año desde/i), { target: { value: "2024" } });
    fireEvent.change(screen.getByLabelText(/año hasta/i), { target: { value: "2025" } });

    expect(await screen.findByText("Producto match-1")).toBeInTheDocument();
    const last = lastGetPath();
    expect(last).toContain("type=articulo");
    expect(last).toContain("year__gte=2024");
    expect(last).toContain("year__lte=2025");
  });

  it("serializes exact-year, project, researcher, center, group and line filters", async () => {
    setAuthRoles(["researcher"]);
    renderList(() => Promise.resolve(pageOf([makeProduct("a1")])));
    expect(await screen.findByText("Producto a1")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/año exacto/i), { target: { value: "2024" } });
    await pickOption(/^proyecto$/i, /proyecto alpha/i);
    await pickOption(/^investigador$/i, /ana pérez/i);
    await pickOption(/^centro$/i, /centro de inteligencia artificial/i);
    await pickOption(/^grupo$/i, /grupo de machine learning/i);
    await pickOption(/^línea$/i, /línea de deep learning/i);

    await waitFor(() => {
      const last = lastGetPath();
      expect(last).toContain("year=2024");
      expect(last).toContain("project=p1");
      expect(last).toContain("researcher=r-1");
      expect(last).toContain("center=center-1");
      expect(last).toContain("group=group-1");
      expect(last).toContain("line=line-1");
    });
  });

  it("resets to page 1 when a filter is applied from a later page", async () => {
    setAuthRoles(["researcher"]);
    const page1 = {
      count: 26,
      next: "http://localhost:8000/api/products/?page=2",
      previous: null,
      results: [makeProduct("a1", "articulo")],
    };
    const page2 = {
      count: 26,
      next: null,
      previous: "http://localhost:8000/api/products/?page=1",
      results: [makeProduct("b1", "libro")],
    };
    const getMock = jest.fn((path: string) =>
      Promise.resolve(path.includes("page=2") ? page2 : page1),
    );

    renderList(getMock);
    expect(await screen.findByText("Producto a1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /siguiente/i }));
    expect(await screen.findByText("Producto b1")).toBeInTheDocument();

    await pickOption(/tipo de producto/i, /^Artículo$/);

    await waitFor(() => {
      expect(lastGetPath()).toContain("type=articulo");
      expect(lastGetPath()).not.toContain("page=2");
    });
    expect(await screen.findByText("Producto a1")).toBeInTheDocument();
    expect(screen.queryByText("Producto b1")).not.toBeInTheDocument();
  });

  it("clears the type filter back to the unfiltered list via Todos", async () => {
    setAuthRoles(["researcher"]);
    const getMock = jest.fn((path: string) => {
      if (path.includes("type=articulo")) {
        return Promise.resolve(pageOf([makeProduct("art-1", "articulo")]));
      }
      return Promise.resolve(pageOf([makeProduct("c1", "libro")]));
    });
    renderList(getMock);

    await pickOption(/tipo de producto/i, /^Artículo$/);
    expect(await screen.findByText("Producto art-1")).toBeInTheDocument();

    await pickOption(/tipo de producto/i, /^Todos$/);

    expect(await screen.findByText("Producto c1")).toBeInTheDocument();
    expect(lastGetPath()).not.toContain("type=");
  });
});

describe("ProductList — states", () => {
  it("announces the loading region while fetching", async () => {
    setAuthRoles(["researcher"]);
    let resolveFetch!: (value: unknown) => void;
    const pending = new Promise((resolve) => {
      resolveFetch = resolve;
    });
    renderList(() => pending);

    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-label", "Cargando productos");

    act(() => {
      resolveFetch(pageOf([makeProduct("c1")]));
    });
    expect(await screen.findByText("Producto c1")).toBeInTheDocument();
  });

  it("renders an alert with the error message when the list query fails", async () => {
    setAuthRoles(["researcher"]);
    renderList(() => Promise.reject(new Error("No autorizado")));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("No autorizado");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("shows the unfiltered empty state with a create action for any role", async () => {
    setAuthRoles(["researcher"]);
    renderList(() => Promise.resolve(pageOf([])));

    expect(await screen.findByText("No hay productos")).toBeInTheDocument();
    const ctas = screen.getAllByRole("link", { name: "Nuevo producto" });
    expect(ctas.length).toBeGreaterThan(0);
    ctas.forEach((cta) => expect(cta).toHaveAttribute("href", "/products/new"));
  });

  it("shows the filtered empty state when filters yield no results", async () => {
    setAuthRoles(["researcher"]);
    const getMock = jest.fn((path: string) => {
      if (path.includes("type=")) return Promise.resolve(pageOf([]));
      return Promise.resolve(pageOf([makeProduct("c1")]));
    });
    renderList(getMock);
    expect(await screen.findByText("Producto c1")).toBeInTheDocument();

    await pickOption(/tipo de producto/i, /^Artículo$/);

    expect(await screen.findByText("Sin resultados")).toBeInTheDocument();
    expect(screen.getByText(/no se encontraron productos/i)).toBeInTheDocument();
  });
});

describe("ProductList — select filter options (PR3)", () => {
  it("renders project titles from useProjectsList and serializes project=p1", async () => {
    setAuthRoles(["researcher"]);
    renderList(() => Promise.resolve(pageOf([makeProduct("a1")])));
    expect(await screen.findByText("Producto a1")).toBeInTheDocument();

    await pickOption(/^proyecto$/i, /proyecto alpha/i);

    await waitFor(() => expect(lastGetPath()).toContain("project=p1"));
  });

  it("renders researcher names from useResearchersList and serializes researcher=r-1", async () => {
    setAuthRoles(["researcher"]);
    renderList(() => Promise.resolve(pageOf([makeProduct("a1")])));
    expect(await screen.findByText("Producto a1")).toBeInTheDocument();

    await pickOption(/^investigador$/i, /ana pérez/i);

    await waitFor(() => expect(lastGetPath()).toContain("researcher=r-1"));
  });

  it("renders center names and serializes center=center-1", async () => {
    setAuthRoles(["researcher"]);
    renderList(() => Promise.resolve(pageOf([makeProduct("a1")])));
    expect(await screen.findByText("Producto a1")).toBeInTheDocument();

    await pickOption(/^centro$/i, /centro de inteligencia artificial/i);

    await waitFor(() => expect(lastGetPath()).toContain("center=center-1"));
  });

  it("loads group and line options only after their parent is selected (dependent refresh)", async () => {
    setAuthRoles(["researcher"]);
    renderList(() => Promise.resolve(pageOf([makeProduct("a1")])));
    expect(await screen.findByText("Producto a1")).toBeInTheDocument();

    // Without a center the group/line selects are disabled.
    expect(screen.getByRole("combobox", { name: /^grupo$/i })).toBeDisabled();
    expect(screen.getByRole("combobox", { name: /^línea$/i })).toBeDisabled();

    await pickOption(/^centro$/i, /centro de inteligencia artificial/i);

    // Group options load after the center is chosen; line after the group.
    await pickOption(/^grupo$/i, /grupo de machine learning/i);
    await pickOption(/^línea$/i, /línea de deep learning/i);

    await waitFor(() => {
      const last = lastGetPath();
      expect(last).toContain("center=center-1");
      expect(last).toContain("group=group-1");
      expect(last).toContain("line=line-1");
    });
  });

  it("clears stale group and line filters when the center changes", async () => {
    setAuthRoles(["researcher"]);
    mockUrlParams = new URLSearchParams("center=center-1&group=group-1&line=line-1");
    renderList(() => Promise.resolve(pageOf([makeProduct("a1")])));
    expect(await screen.findByText("Producto a1")).toBeInTheDocument();
    expect(lastGetPath()).toContain("center=center-1");

    await pickOption(/^centro$/i, /centro de energía/i);

    await waitFor(() => {
      const last = lastGetPath();
      expect(last).toContain("center=center-2");
      expect(last).not.toContain("group=");
      expect(last).not.toContain("line=");
    });
    expect(mockUrlParams.get("group")).toBeNull();
    expect(mockUrlParams.get("line")).toBeNull();
  });

  it('resets project, researcher and center filters via "Todos"', async () => {
    setAuthRoles(["researcher"]);
    const getMock = jest.fn((path: string) => {
      if (
        path.includes("project=p1") ||
        path.includes("researcher=r-1") ||
        path.includes("center=center-1")
      ) {
        return Promise.resolve(pageOf([makeProduct("filtered-1")]));
      }
      return Promise.resolve(pageOf([makeProduct("c1")]));
    });
    renderList(getMock);
    expect(await screen.findByText("Producto c1")).toBeInTheDocument();

    await pickOption(/^proyecto$/i, /proyecto alpha/i);
    await waitFor(() => expect(lastGetPath()).toContain("project=p1"));
    await pickOption(/^proyecto$/i, /^todos$/i);
    await waitFor(() => expect(lastGetPath()).not.toContain("project="));

    await pickOption(/^investigador$/i, /ana pérez/i);
    await waitFor(() => expect(lastGetPath()).toContain("researcher=r-1"));
    await pickOption(/^investigador$/i, /^todos$/i);
    await waitFor(() => expect(lastGetPath()).not.toContain("researcher="));

    await pickOption(/^centro$/i, /centro de inteligencia artificial/i);
    await waitFor(() => expect(lastGetPath()).toContain("center=center-1"));
    await pickOption(/^centro$/i, /^todos$/i);
    await waitFor(() => expect(lastGetPath()).not.toContain("center="));
  });
});

describe("ProductList — query-string round-trip (PR3)", () => {
  it("restores type, year-range and page filters from the URL query string", async () => {
    setAuthRoles(["researcher"]);
    mockUrlParams = new URLSearchParams("type=articulo&year__gte=2024&year__lte=2025&page=2");
    const page1 = {
      count: 26,
      next: "http://localhost:8000/api/products/?page=2",
      previous: null,
      results: [makeProduct("a1", "articulo")],
    };
    const page2 = {
      count: 26,
      next: null,
      previous: "http://localhost:8000/api/products/?page=1",
      results: [makeProduct("b1", "articulo", 2024)],
    };
    const getMock = jest.fn((path: string) =>
      Promise.resolve(path.includes("page=2") ? page2 : page1),
    );
    renderList(getMock);

    // Page 2 is fetched with the restored filters.
    expect(await screen.findByText("Producto b1")).toBeInTheDocument();
    const last = lastGetPath();
    expect(last).toContain("type=articulo");
    expect(last).toContain("year__gte=2024");
    expect(last).toContain("year__lte=2025");

    // The controls reflect the restored state.
    expect(screen.getByRole("combobox", { name: /tipo de producto/i })).toHaveTextContent(
      "Artículo",
    );
    expect(screen.getByLabelText(/año desde/i)).toHaveValue(2024);
    expect(screen.getByLabelText(/año hasta/i)).toHaveValue(2025);
    expect(screen.getByText(/página 2/i)).toBeInTheDocument();
  });

  it("writes filter and pagination changes to the URL query string", async () => {
    setAuthRoles(["researcher"]);
    const page1 = {
      count: 26,
      next: "http://localhost:8000/api/products/?page=2",
      previous: null,
      results: [makeProduct("a1")],
    };
    const page2 = {
      count: 26,
      next: null,
      previous: "http://localhost:8000/api/products/?page=1",
      results: [makeProduct("b1")],
    };
    const getMock = jest.fn((path: string) =>
      Promise.resolve(path.includes("page=2") ? page2 : page1),
    );
    renderList(getMock);
    expect(await screen.findByText("Producto a1")).toBeInTheDocument();

    await pickOption(/^proyecto$/i, /proyecto alpha/i);
    await waitFor(() => {
      expect(mockUrlParams.get("project")).toBe("p1");
      expect(mockUrlParams.get("page")).toBeNull(); // page 1 is not serialized
    });

    fireEvent.change(screen.getByLabelText(/año desde/i), { target: { value: "2024" } });
    await waitFor(() => expect(mockUrlParams.get("year__gte")).toBe("2024"));

    // Wait for the refetch to settle so the pagination buttons re-enable.
    expect(await screen.findByText("Producto a1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /siguiente/i }));
    await waitFor(() => expect(mockUrlParams.get("page")).toBe("2"));
  });

  it("round-trips ordering through the URL", async () => {
    setAuthRoles(["researcher"]);
    mockUrlParams = new URLSearchParams("ordering=-title");
    renderList(() => Promise.resolve(pageOf([makeProduct("a1")])));
    expect(await screen.findByText("Producto a1")).toBeInTheDocument();

    expect(lastGetPath()).toContain("ordering=-title");
    expect(screen.getByRole("button", { name: "Ordenar por título" })).toHaveTextContent(
      "Título ↓",
    );
  });
});
