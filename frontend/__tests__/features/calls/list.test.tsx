/**
 * CallList — paginated table, empty state, filter UI and gated CTA.
 *
 * Spec (calls-ui list):
 *   - Rows render with status badges and call_type labels.
 *   - Pagination controls driven by the DRF next/previous links.
 *   - An empty institution shows an empty state with a create action.
 *   - The create CTA is director-gated (canManageCall).
 */

import { render, screen, fireEvent } from "@testing-library/react";
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

function renderList(getMock: jest.Mock) {
  (api.api.get as jest.Mock).mockImplementation(getMock);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <CallList />
    </QueryClientProvider>,
  );
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