/**
 * Dashboard page — integration tests for the new server-side KPI + charts.
 *
 * Director/admin: all KPIs and charts visible.
 * Researcher: limited KPIs (backend scopes data).
 * Auditor: same view as director.
 */

import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useAuthStore } from "@/store/auth";

// Mock next/navigation for the shell.
jest.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({ push: jest.fn(), prefetch: jest.fn() }),
}));

jest.mock("next/link", () => ({
  __esModule: true,
  default: ({
    href,
    children,
  }: {
    href: string | { pathname: string };
    children: React.ReactNode;
  }) => <a href={typeof href === "string" ? href : href.pathname}>{children}</a>,
}));

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

// Mock recharts for jsdom compatibility.
jest.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  PieChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pie-chart">{children}</div>
  ),
  Pie: ({ children }: { children: React.ReactNode }) => <div data-testid="pie">{children}</div>,
  Cell: () => <div data-testid="cell" />,
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: () => <div data-testid="bar" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
}));

import * as api from "@/lib/api";
import DashboardPage from "@/app/dashboard/page";
import type { DashboardSummary } from "@/features/dashboard/queries";

const mockSummary: DashboardSummary = {
  indicators: {
    "IND-001": 42,
    "IND-002": [{ center_id: "c1", name: "Centro A", count: 10 }],
    "IND-003": [{ status: "aprobado", count: 20 }],
    "IND-004": 5,
    "IND-005": 3,
    "IND-006": 75.5,
    "IND-007": "1000000.00",
    "IND-008": "750000.00",
    "IND-009": "250000.00",
    "IND-010": [{ project_id: "p1", name: "Proyecto X", count: 15 }],
    "IND-011": [{ researcher_id: "r1", full_name: "Dr. Y", count: 8 }],
    "IND-012": { total: 100, complete: 85, rate: 85.0 },
    "IND-013": 3,
    "IND-014": 12,
  },
  charts: {
    projects_by_status: [{ status: "aprobado", count: 20 }],
    projects_by_center: [{ center_id: "c1", name: "Centro A", count: 10 }],
    budget: { approved: "1000000.00", executed: "750000.00", balance: "250000.00" },
    progress_reports: { pending: 5, observed: 3, approved: 42 },
  },
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

  (api.api.get as jest.Mock).mockResolvedValue(mockSummary);

  return render(
    <QueryClientProvider client={qc}>
      <DashboardPage />
    </QueryClientProvider>,
  );
}

describe("DashboardPage — director", () => {
  it("renders director KPI cards and charts", async () => {
    renderDashboard(["director"]);

    // Director-specific KPIs
    expect(await screen.findByText("Total de proyectos")).toBeInTheDocument();
    expect(await screen.findByText("Pendientes de aprobación")).toBeInTheDocument();
    expect(await screen.findByText("Avances pendientes")).toBeInTheDocument();
    expect(await screen.findByText("Progreso promedio")).toBeInTheDocument();

    // Values from the mock
    expect(await screen.findByText("42")).toBeInTheDocument();
    expect(await screen.findByText("5")).toBeInTheDocument();

    // Charts
    expect(await screen.findByText("Proyectos por estado")).toBeInTheDocument();
    expect(await screen.findByText("Proyectos por centro")).toBeInTheDocument();
    expect(await screen.findByText("Ejecución presupuestal")).toBeInTheDocument();
    expect(await screen.findByText("Informes de avance")).toBeInTheDocument();
  });
});

describe("DashboardPage — researcher", () => {
  it("renders limited KPIs and hides director-only labels", async () => {
    renderDashboard(["researcher"]);

    expect(await screen.findByText("Mis proyectos")).toBeInTheDocument();
    expect(await screen.findByText("Progreso promedio")).toBeInTheDocument();

    // Director-only labels must not appear
    await waitFor(() => {
      expect(screen.queryByText("Pendientes de aprobación")).not.toBeInTheDocument();
      expect(screen.queryByText("Avances pendientes")).not.toBeInTheDocument();
    });
  });
});

describe("DashboardPage — auditor", () => {
  it("renders the same view as director (read-only)", async () => {
    renderDashboard(["auditor"]);

    expect(await screen.findByText("Total de proyectos")).toBeInTheDocument();
    expect(await screen.findByText("Pendientes de aprobación")).toBeInTheDocument();

    // Charts are also visible for auditors
    expect(await screen.findByText("Proyectos por estado")).toBeInTheDocument();
    expect(await screen.findByText("Ejecución presupuestal")).toBeInTheDocument();
  });
});
