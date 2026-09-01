/**
 * CallList — paginated table, empty state, filter UI and gated CTA.
 *
 * Spec (calls-ui list):
 *   - Rows render with status badges and call_type labels.
 *   - Pagination controls driven by the DRF next/previous links.
 *   - An empty institution shows an empty state with a create action.
 *   - The create CTA is director-gated (canManageCall).
 */

import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

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
import { CallList } from "@/features/calls/CallList";

function makeCall(id: string, status = "abierta", callType = "internal") {
  return {
    id,
    title: `Convocatoria ${id}`,
    status,
    call_type: callType,
    created_at: "2026-01-01T09:00:00Z",
  };
}

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

function renderList(getMock: (path: string) => Promise<unknown>) {
  (api.api.get as jest.Mock).mockImplementation(getMock);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <CallList />
    </QueryClientProvider>,
  );
}

/** Open a shadcn/Radix Select by trigger label and pick an option. */
async function pickOption(triggerName: RegExp, optionName: RegExp) {
  fireEvent.click(screen.getByRole("combobox", { name: triggerName }));
  fireEvent.click(await screen.findByRole("option", { name: optionName }));
}

/** Path of the most recent api.get call. */
function lastGetPath(): string {
  const calls = (api.api.get as jest.Mock).mock.calls;
  return calls[calls.length - 1][0] as string;
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe("CallList — paginated rows", () => {
  it("renders title, badge, type label and created date for each row", async () => {
    setAuthRoles(["director"]);
    renderList(() => Promise.resolve(pageOf([makeCall("c1")])));

    expect(await screen.findByText("Convocatoria c1")).toBeInTheDocument();
    expect(screen.getByText("Abierta")).toBeInTheDocument();
    expect(screen.getByText("Interna")).toBeInTheDocument();
    expect(screen.getByText("2026-01-01")).toBeInTheDocument();
  });

  it("follows the next link and requests page 2", async () => {
    setAuthRoles(["director"]);
    const page1 = {
      count: 26,
      next: "http://localhost:8000/api/calls/?page=2",
      previous: null,
      results: [makeCall("a1")],
    };
    const page2 = {
      count: 26,
      next: null,
      previous: "http://localhost:8000/api/calls/?page=1",
      results: [makeCall("b1")],
    };
    const getMock = jest.fn((path: string) =>
      Promise.resolve(path.includes("page=2") ? page2 : page1),
    );

    renderList(getMock);
    expect(await screen.findByText("Convocatoria a1")).toBeInTheDocument();

    const nextBtn = screen.getByRole("button", { name: /siguiente/i });
    expect(nextBtn).toBeEnabled();
    fireEvent.click(nextBtn);

    expect(await screen.findByText("Convocatoria b1")).toBeInTheDocument();
  });

  it("goes back with the Anterior control to the previous page", async () => {
    setAuthRoles(["director"]);
    const page1 = {
      count: 26,
      next: "http://localhost:8000/api/calls/?page=2",
      previous: null,
      results: [makeCall("a1")],
    };
    const page2 = {
      count: 26,
      next: null,
      previous: "http://localhost:8000/api/calls/?page=1",
      results: [makeCall("b1")],
    };
    const getMock = jest.fn((path: string) =>
      Promise.resolve(path.includes("page=2") ? page2 : page1),
    );

    renderList(getMock);
    expect(await screen.findByText("Convocatoria a1")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /siguiente/i }));
    expect(await screen.findByText("Convocatoria b1")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /anterior/i }));
    expect(await screen.findByText("Convocatoria a1")).toBeInTheDocument();
    expect(screen.queryByText("Convocatoria b1")).not.toBeInTheDocument();
  });
});

describe("CallList — empty state and gated CTA", () => {
  it("renders an empty state with a create action for a director", async () => {
    setAuthRoles(["director"]);
    renderList(() => Promise.resolve(pageOf([])));

    expect(await screen.findByText("No hay convocatorias")).toBeInTheDocument();
    const ctas = screen.getAllByRole("link", { name: "Nueva convocatoria" });
    expect(ctas.length).toBeGreaterThan(0);
    ctas.forEach((cta) => expect(cta).toHaveAttribute("href", "/calls/new"));
  });

  it("hides the create CTA for a researcher", async () => {
    setAuthRoles(["researcher"]);
    renderList(() => Promise.resolve(pageOf([])));

    expect(await screen.findByText("No hay convocatorias")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Nueva convocatoria" })).not.toBeInTheDocument();
  });
});

describe("CallList — filter UI", () => {
  it("renders status and call_type filter controls", async () => {
    setAuthRoles(["director"]);
    renderList(() => Promise.resolve(pageOf([makeCall("c1")])));

    expect(await screen.findByText("Convocatoria c1")).toBeInTheDocument();
    expect(screen.getByLabelText(/estado/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/tipo/i)).toBeInTheDocument();
  });
});

describe("CallList — filter refetch wiring", () => {
  it("refetches with ?status=abierta and renders only open calls", async () => {
    setAuthRoles(["director"]);
    const getMock = jest.fn((path: string) => {
      if (path.includes("status=abierta")) {
        return Promise.resolve(pageOf([makeCall("open-1", "abierta")]));
      }
      return Promise.resolve(pageOf([makeCall("draft-1", "borrador")]));
    });
    renderList(getMock);
    expect(await screen.findByText("Convocatoria draft-1")).toBeInTheDocument();

    await pickOption(/estado/i, /^Abierta$/);

    expect(await screen.findByText("Convocatoria open-1")).toBeInTheDocument();
    expect(screen.queryByText("Convocatoria draft-1")).not.toBeInTheDocument();
    expect(lastGetPath()).toContain("status=abierta");
  });

  it("refetches with ?call_type=external when the type filter is selected", async () => {
    setAuthRoles(["director"]);
    const getMock = jest.fn((path: string) => {
      if (path.includes("call_type=external")) {
        return Promise.resolve(pageOf([makeCall("ext-1", "abierta", "external")]));
      }
      return Promise.resolve(pageOf([makeCall("int-1", "abierta", "internal")]));
    });
    renderList(getMock);
    expect(await screen.findByText("Convocatoria int-1")).toBeInTheDocument();

    await pickOption(/tipo/i, /^Externa$/);

    expect(await screen.findByText("Convocatoria ext-1")).toBeInTheDocument();
    expect(lastGetPath()).toContain("call_type=external");
  });

  it("combines status and call_type filters in a single refetch", async () => {
    setAuthRoles(["director"]);
    const getMock = jest.fn((path: string) => {
      if (path.includes("status=abierta") && path.includes("call_type=external")) {
        return Promise.resolve(pageOf([makeCall("open-ext", "abierta", "external")]));
      }
      return Promise.resolve(pageOf([makeCall("c1")]));
    });
    renderList(getMock);
    expect(await screen.findByText("Convocatoria c1")).toBeInTheDocument();

    await pickOption(/estado/i, /^Abierta$/);
    await pickOption(/tipo/i, /^Externa$/);

    expect(await screen.findByText("Convocatoria open-ext")).toBeInTheDocument();
    const last = lastGetPath();
    expect(last).toContain("status=abierta");
    expect(last).toContain("call_type=external");
  });

  it("resets to page 1 when a filter is applied from a later page", async () => {
    setAuthRoles(["director"]);
    const page1 = {
      count: 26,
      next: "http://localhost:8000/api/calls/?page=2",
      previous: null,
      results: [makeCall("a1", "abierta")],
    };
    const page2 = {
      count: 26,
      next: null,
      previous: "http://localhost:8000/api/calls/?page=1",
      results: [makeCall("b1", "borrador")],
    };
    const getMock = jest.fn((path: string) =>
      Promise.resolve(path.includes("page=2") ? page2 : page1),
    );

    renderList(getMock);
    expect(await screen.findByText("Convocatoria a1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /siguiente/i }));
    expect(await screen.findByText("Convocatoria b1")).toBeInTheDocument();

    await pickOption(/estado/i, /^Abierta$/);

    await waitFor(() => {
      expect(lastGetPath()).toContain("status=abierta");
      expect(lastGetPath()).not.toContain("page=2");
    });
    expect(await screen.findByText("Convocatoria a1")).toBeInTheDocument();
    expect(screen.queryByText("Convocatoria b1")).not.toBeInTheDocument();
  });

  it("clears the status filter back to the unfiltered list via Todos", async () => {
    setAuthRoles(["director"]);
    const getMock = jest.fn((path: string) => {
      if (path.includes("status=abierta")) {
        return Promise.resolve(pageOf([makeCall("open-1", "abierta")]));
      }
      return Promise.resolve(pageOf([makeCall("c1")]));
    });
    renderList(getMock);

    await pickOption(/estado/i, /^Abierta$/);
    expect(await screen.findByText("Convocatoria open-1")).toBeInTheDocument();

    await pickOption(/estado/i, /^Todos$/);

    expect(await screen.findByText("Convocatoria c1")).toBeInTheDocument();
    expect(lastGetPath()).not.toContain("status=");
  });
});

describe("CallList — loading, error and filtered empty states", () => {
  it("announces the loading region while fetching", async () => {
    setAuthRoles(["director"]);
    let resolveFetch!: (value: unknown) => void;
    const pending = new Promise((resolve) => {
      resolveFetch = resolve;
    });
    renderList(() => pending);

    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-label", "Cargando convocatorias");

    act(() => {
      resolveFetch(pageOf([makeCall("c1")]));
    });
    expect(await screen.findByText("Convocatoria c1")).toBeInTheDocument();
  });

  it("renders an alert with the error message when the list query fails", async () => {
    setAuthRoles(["director"]);
    renderList(() => Promise.reject(new Error("No autorizado")));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("No autorizado");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("shows the filtered empty state when filters yield no results", async () => {
    setAuthRoles(["director"]);
    const getMock = jest.fn((path: string) => {
      if (path.includes("status=")) return Promise.resolve(pageOf([]));
      return Promise.resolve(pageOf([makeCall("c1")]));
    });
    renderList(getMock);
    expect(await screen.findByText("Convocatoria c1")).toBeInTheDocument();

    await pickOption(/estado/i, /^Abierta$/);

    expect(await screen.findByText("Sin resultados")).toBeInTheDocument();
    expect(screen.getByText(/no se encontraron convocatorias/i)).toBeInTheDocument();
  });
});
