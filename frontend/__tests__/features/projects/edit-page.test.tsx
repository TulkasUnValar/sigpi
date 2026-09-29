/**
 * /projects/{id}/edit — edit project page (FR-05 / FR-06 / FR-07).
 *
 * Spec (projects-ui edit):
 *   - Loading and not-found stay in-page inside the authenticated shell.
 *   - A non-terminal project seeds the shared ProjectForm from the detail;
 *     a successful save PATCHes and redirects to /projects/{id}.
 *   - A terminal project is not editable for non-admins (RN-011); the
 *     route refuses to render the form even on direct navigation.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

const pushMock = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => "/projects/p1/edit",
  useParams: () => ({ id: "p1" }),
  useRouter: () => ({ push: pushMock, prefetch: jest.fn() }),
}));

jest.mock("next/link", () => {
  return {
    __esModule: true,
    default: ({
      href,
      children,
    }: {
      href: string | { pathname: string };
      children: React.ReactNode;
    }) => <a href={typeof href === "string" ? href : href.pathname}>{children}</a>,
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
import EditProjectPage from "@/app/projects/[id]/edit/page";

const detail = {
  id: "p1",
  institution: "inst-1",
  center: "c1",
  group: "g1",
  line: "l1",
  principal_investigator: "r1",
  title: "Proyecto Alpha",
  abstract: "Resumen del proyecto.",
  objectives: "Objetivos.",
  methodology: "Metodología.",
  expected_results: "Resultados.",
  keywords: "alpha",
  start_date: "2026-01-10",
  estimated_end_date: "2027-01-10",
  actual_end_date: null,
  status: "en_revision",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  members: [],
  documents: [],
};

const centers = [{ id: "c1", name: "Centro A", code: "CA" }];
const groups = [{ id: "g1", name: "Grupo 1", code: "G1" }];
const lines = [{ id: "l1", name: "Línea 1", code: "L1" }];
const researchers = [
  {
    id: "r1",
    full_name: "Ana Pérez",
    institution: "inst-1",
    is_active: true,
    completeness_score: 100,
  },
];

function pageOf<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results };
}

function setAuth(roles: string[] = ["researcher"]) {
  useAuthStore.setState({
    roles,
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
    institutions: [],
    centers: [],
  });
}

/** Detail GET implementation with the dependent option endpoints. */
function detailGet(project: unknown) {
  return (path: string) => {
    if (path === "/api/projects/p1/") return Promise.resolve(project);
    if (path.includes("/lines/")) return Promise.resolve(lines);
    if (path.includes("/groups/")) return Promise.resolve(groups);
    if (path.includes("/centers/")) return Promise.resolve(centers);
    if (path.includes("/researchers/")) return Promise.resolve(pageOf(researchers));
    return Promise.resolve(pageOf([]));
  };
}

function renderPage(getImpl: (path: string) => Promise<unknown>) {
  (api.api.get as jest.Mock).mockImplementation(getImpl);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <EditProjectPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  pushMock.mockClear();
  setAuth();
});

describe("/projects/[id]/edit — loading and not-found", () => {
  it("keeps loading in-page and renders the form once the detail resolves", async () => {
    let resolveDetail!: (value: unknown) => void;
    const getImpl = (path: string) => {
      if (path === "/api/projects/p1/") {
        return new Promise<unknown>((resolve) => {
          resolveDetail = resolve;
        });
      }
      return detailGet(detail)(path);
    };
    renderPage(getImpl);

    // The form is not rendered while the detail is pending (in-page loading).
    expect(screen.queryByLabelText(/título/i)).not.toBeInTheDocument();

    resolveDetail(detail);
    expect(await screen.findByLabelText(/título/i)).toHaveValue("Proyecto Alpha");
  });

  it("renders the not-found state in-page when the detail is missing", async () => {
    renderPage(detailGet(null));

    expect(await screen.findByText("Proyecto no encontrado")).toBeInTheDocument();
    expect(screen.queryByLabelText(/título/i)).not.toBeInTheDocument();
  });
});

describe("/projects/[id]/edit — seeding and save", () => {
  it("seeds the form from the detail, PATCHes, and redirects to the detail", async () => {
    const user = userEvent.setup();
    (api.api.patch as jest.Mock).mockResolvedValue({
      ...detail,
      title: "Proyecto Alpha (editado)",
    });
    renderPage(detailGet(detail));
    await screen.findByLabelText(/título/i);

    await user.click(screen.getByRole("button", { name: /guardar cambios/i }));

    await waitFor(() => {
      expect(api.api.patch).toHaveBeenCalledWith(
        "/api/projects/p1/",
        expect.objectContaining({ title: "Proyecto Alpha", center: "c1" }),
        expect.objectContaining({ institutionId: "inst-1" }),
      );
    });
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/projects/p1"));
  });
});

describe("/projects/[id]/edit — terminal edit gating (RN-011)", () => {
  it("refuses to render the form for a terminal project for a non-admin", async () => {
    setAuth(["researcher"]);
    renderPage(detailGet({ ...detail, status: "cerrado" }));

    expect(await screen.findByText(/no se puede editar/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/título/i)).not.toBeInTheDocument();
  });

  it("renders the form for a terminal project for an admin (backend bypass)", async () => {
    setAuth(["admin"]);
    renderPage(detailGet({ ...detail, status: "cancelado" }));

    expect(await screen.findByLabelText(/título/i)).toHaveValue("Proyecto Alpha");
  });
});
