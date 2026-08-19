/**
 * Dashboard page — role-aware KPI cards and pending-approvals queue.
 *
 * Spec (dashboard):
 *   Director queue: pending-approvals queue + KPI cards appear.
 *   Investigator KPIs: "my projects" and progress KPIs; approvals hidden.
 */

import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

// Mock next/navigation for the shell the dashboard renders.
jest.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
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

// Mock the API client used by the dashboard queries.
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
import DashboardPage from "@/app/dashboard/page";

const projectsPage = {
  count: 3,
  next: null,
  previous: null,
  results: [
    { id: "p1", title: "Proyecto Alpha", status: "en_revision" },
    { id: "p2", title: "Proyecto Beta", status: "en_revision" },
    { id: "p3", title: "Proyecto Gamma", status: "aprobado" },
  ],
};

const progressPage = {
  count: 2,
  next: null,
  previous: null,
  results: [
    { id: "a1", project: "p3", status: "en_revision", cumulative_percentage: 30 },
    { id: "a2", project: "p3", status: "aprobado", cumulative_percentage: 50 },
  ],
};

function renderDashboard(roles: string[]) {
  useAuthStore.setState({
    roles,
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
  });

  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  (api.api.get as jest.Mock).mockImplementation((path: string) => {
    if (path.includes("/api/projects/")) return Promise.resolve(projectsPage);
    if (path.includes("/api/progress/")) return Promise.resolve(progressPage);
    return Promise.resolve([]);
  });

  return render(
    <QueryClientProvider client={qc}>
      <DashboardPage />
    </QueryClientProvider>,
  );
}

describe("DashboardPage — director", () => {
  it("renders KPI cards and the pending-approvals queue for a director", async () => {
    renderDashboard(["director"]);

    // Director KPI cards
    expect(await screen.findByText("Total de proyectos")).toBeInTheDocument();
    expect(await screen.findByText("Pendientes de aprobación")).toBeInTheDocument();

    // Pending approvals queue lists the in-review projects
    expect(await screen.findByText("Proyecto Alpha")).toBeInTheDocument();
    expect(await screen.findByText("Proyecto Beta")).toBeInTheDocument();
  });
});

describe("DashboardPage — investigator", () => {
  it("renders my-projects and progress KPIs; hides approvals", async () => {
    renderDashboard(["researcher"]);

    expect(await screen.findByText("Mis proyectos")).toBeInTheDocument();
    expect(await screen.findByText("Progreso promedio")).toBeInTheDocument();

    // Approvals queue label must NOT appear for investigators.
    await waitFor(() => {
      expect(screen.queryByText("Pendientes de aprobación")).not.toBeInTheDocument();
    });
  });
});