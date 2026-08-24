/**
 * Advances nested list — /projects/[id]/advances.
 *
 * Spec (advances-ui nested list):
 *   GIVEN a project with advances
 *   WHEN visiting /projects/{id}/advances
 *   THEN list + cumulative % render.
 */

import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

jest.mock("next/navigation", () => ({
  usePathname: () => "/projects/p1/advances",
  useParams: () => ({ id: "p1" }),
  useRouter: () => ({ push: jest.fn(), prefetch: jest.fn() }),
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
    }) => (
      <a href={typeof href === "string" ? href : href.pathname}>{children}</a>
    ),
  };
});

jest.mock("next-themes", () => ({
  useTheme: () => ({ theme: "light", setTheme: jest.fn(), themes: [] }),
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
import AdvancesPage from "@/app/projects/[id]/advances/page";

function makeAdvance(id: string, percentage: number) {
  return {
    id,
    project: "p1",
    status: "en_revision",
    cumulative_percentage: percentage,
    period_start: "2026-01-01",
    period_end: "2026-03-31",
    created_at: "2026-01-01T00:00:00Z",
  };
}

function renderAdvances(getMock: jest.Mock) {
  useAuthStore.setState({
    roles: ["director"],
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
    centers: [],
  });

  (api.api.get as jest.Mock).mockImplementation(getMock);

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  return render(
    <QueryClientProvider client={qc}>
      <AdvancesPage />
    </QueryClientProvider>,
  );
}

describe("AdvancesPage — nested list", () => {
  it("requests the project-scoped progress endpoint", async () => {
    const getMock = jest.fn(() =>
      Promise.resolve({
        count: 1,
        next: null,
        previous: null,
        results: [makeAdvance("a1", 25)],
      }),
    );
    renderAdvances(getMock);

    // Row percentage + average indicator both show 25% for a single advance.
    expect((await screen.findAllByText("25%")).length).toBeGreaterThan(0);

    await waitFor(() => {
      const calls = (api.api.get as jest.Mock).mock.calls;
      const calledPath = calls[calls.length - 1][0] as string;
      expect(calledPath).toContain("/api/projects/p1/progress/");
    });
  });

  it("renders each advance row with period and status badge", async () => {
    const getMock = jest.fn(() =>
      Promise.resolve({
        count: 2,
        next: null,
        previous: null,
        results: [makeAdvance("a1", 25), makeAdvance("a2", 50)],
      }),
    );
    renderAdvances(getMock);

    expect(await screen.findByText("25%")).toBeInTheDocument();
    expect(screen.getByText("50%")).toBeInTheDocument();
    // StatusBadge Spanish label for en_revision.
    expect(screen.getAllByText("En revisión")).toHaveLength(2);
    // Period rendered.
    expect(screen.getAllByText(/2026-01-01/).length).toBeGreaterThan(0);
  });

  it("renders a cumulative progress indicator for the project", async () => {
    const getMock = jest.fn(() =>
      Promise.resolve({
        count: 2,
        next: null,
        previous: null,
        results: [makeAdvance("a1", 30), makeAdvance("a2", 50)],
      }),
    );
    renderAdvances(getMock);

    // Average of 30 and 50 → 40%.
    expect(await screen.findByText("40%")).toBeInTheDocument();
    expect(screen.getByText(/progreso acumulado/i)).toBeInTheDocument();
  });

  it("shows an empty state when the project has no advances", async () => {
    const getMock = jest.fn(() =>
      Promise.resolve({ count: 0, next: null, previous: null, results: [] }),
    );
    renderAdvances(getMock);

    expect(await screen.findByText(/no hay avances/i)).toBeInTheDocument();
  });

  it("links to the create form and to each advance detail", async () => {
    const getMock = jest.fn(() =>
      Promise.resolve({
        count: 1,
        next: null,
        previous: null,
        results: [makeAdvance("a1", 25)],
      }),
    );
    renderAdvances(getMock);

    await screen.findAllByText("25%");

    const newLink = screen.getByRole("link", { name: /nuevo avance/i });
    expect(newLink.getAttribute("href")).toBe("/projects/p1/advances/new");

    const detailLink = screen.getByRole("link", { name: /a1/i });
    expect(detailLink.getAttribute("href")).toBe(
      "/projects/p1/advances/a1",
    );
  });
});