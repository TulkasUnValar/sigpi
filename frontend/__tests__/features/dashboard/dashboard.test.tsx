/**
 * Dashboard — tests for new budget indicators, products section, and researcher metrics.
 *
 * Tests the additional KPIs (IND-007, IND-008, IND-009, IND-012, IND-014)
 * and the "Productos destacados" section (IND-010, IND-011).
 */

import { render, screen } from "@testing-library/react";
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
import { formatCurrency } from "@/features/budgets/constants";
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
    "IND-010": [
      { project_id: "p1", name: "Proyecto Alpha", count: 15 },
      { project_id: "p2", name: "Proyecto Beta", count: 12 },
      { project_id: "p3", name: "Proyecto Gamma", count: 10 },
      { project_id: "p4", name: "Proyecto Delta", count: 9 },
      { project_id: "p5", name: "Proyecto Epsilon", count: 6 },
      { project_id: "p6", name: "Proyecto Zeta", count: 4 },
    ],
    "IND-011": [
      { researcher_id: "r1", full_name: "Dr. María González", count: 7 },
      { researcher_id: "r2", full_name: "Dr. Juan Pérez", count: 3 },
      { researcher_id: "r3", full_name: "Dr. Ana López", count: 5 },
      { researcher_id: "r4", full_name: "Dr. Carlos Ruiz", count: 2 },
      { researcher_id: "r5", full_name: "Dr. Laura Martínez", count: 1 },
    ],
    "IND-012": { total: 100, complete: 85, rate: 85.0 },
    "IND-013": 3,
    "IND-014": 25,
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

describe("Dashboard — indicadores presupuestales", () => {
  it("renders budget KPIs with currency formatting for director", async () => {
    renderDashboard(["director"]);

    // Budget KPI titles
    expect(await screen.findByText("Presupuesto aprobado")).toBeInTheDocument();
    expect(await screen.findByText("Presupuesto ejecutado")).toBeInTheDocument();
    expect(await screen.findByText("Saldo presupuestal")).toBeInTheDocument();

    // Currency formatted values (COP format)
    // Use formatCurrency directly to match the actual locale output
    // Note: Intl.NumberFormat with es-CO produces NBSP (non-breaking space) between $ and number
    // Testing Library normalizes spaces differently, so we use a custom matcher
    const findCurrencyValue = (value: string) => {
      const formatted = formatCurrency(value);
      // Replace NBSP with regular space for matching
      const normalized = formatted.replace(/\u00A0/g, " ");
      return screen.findByText((content, element) => {
        return (
          element?.tagName.toLowerCase() === "p" &&
          content.replace(/\u00A0/g, " ").includes(normalized)
        );
      });
    };

    expect(await findCurrencyValue("1000000.00")).toBeInTheDocument();
    expect(await findCurrencyValue("750000.00")).toBeInTheDocument();
    expect(await findCurrencyValue("250000.00")).toBeInTheDocument();
  });

  it("hides budget KPIs for researcher role", async () => {
    renderDashboard(["researcher"]);

    // Wait for researcher-specific content
    expect(await screen.findByText("Mis proyectos")).toBeInTheDocument();

    // Budget KPIs should not be present
    expect(screen.queryByText("Presupuesto aprobado")).not.toBeInTheDocument();
    expect(screen.queryByText("Presupuesto ejecutado")).not.toBeInTheDocument();
    expect(screen.queryByText("Saldo presupuestal")).not.toBeInTheDocument();
  });
});

describe("Dashboard — sección de productos", () => {
  it("renders products section with top 5 projects and researchers", async () => {
    renderDashboard(["director"]);

    // Section titles
    expect(await screen.findByText("Top proyectos con más productos")).toBeInTheDocument();
    expect(await screen.findByText("Top investigadores con más productos")).toBeInTheDocument();

    // Table headers
    expect(await screen.findByText("Proyecto")).toBeInTheDocument();
    expect(await screen.findByText("Investigador")).toBeInTheDocument();
    expect(screen.getAllByText("Productos").length).toBeGreaterThan(0);

    // Top 5 projects (first 5 from mock data)
    expect(await screen.findByText("Proyecto Alpha")).toBeInTheDocument();
    expect(await screen.findByText("Proyecto Beta")).toBeInTheDocument();
    expect(await screen.findByText("Proyecto Gamma")).toBeInTheDocument();
    expect(await screen.findByText("Proyecto Delta")).toBeInTheDocument();
    expect(await screen.findByText("Proyecto Epsilon")).toBeInTheDocument();

    // 6th project should NOT be visible (limited to 5)
    expect(screen.queryByText("Proyecto Zeta")).not.toBeInTheDocument();

    // Top 5 researchers
    expect(await screen.findByText("Dr. María González")).toBeInTheDocument();
    expect(await screen.findByText("Dr. Juan Pérez")).toBeInTheDocument();
    expect(await screen.findByText("Dr. Ana López")).toBeInTheDocument();
    expect(await screen.findByText("Dr. Carlos Ruiz")).toBeInTheDocument();
    expect(await screen.findByText("Dr. Laura Martínez")).toBeInTheDocument();

    // Product counts
    expect(await screen.findByText("15")).toBeInTheDocument();
    expect(await screen.findByText("12")).toBeInTheDocument();
    expect(await screen.findByText("9")).toBeInTheDocument();
  });

  it("renders products section for all roles (including researcher)", async () => {
    renderDashboard(["researcher"]);

    // Products section should be visible to all roles
    expect(await screen.findByText("Top proyectos con más productos")).toBeInTheDocument();
    expect(await screen.findByText("Top investigadores con más productos")).toBeInTheDocument();
    expect(await screen.findByText("Proyecto Alpha")).toBeInTheDocument();
  });
});

describe("Dashboard — perfiles completos (IND-012)", () => {
  it("renders profile completeness card with progress bar", async () => {
    renderDashboard(["director"]);

    // Card title
    expect(await screen.findByText("Perfiles completos")).toBeInTheDocument();

    // Rate percentage
    expect(await screen.findByText("85.0%")).toBeInTheDocument();

    // "X de Y investigadores" text
    expect(await screen.findByText("85 de 100 investigadores")).toBeInTheDocument();
  });

  it("hides profile completeness card for researcher role", async () => {
    renderDashboard(["researcher"]);

    expect(await screen.findByText("Mis proyectos")).toBeInTheDocument();
    expect(screen.queryByText("Perfiles completos")).not.toBeInTheDocument();
  });
});

describe("Dashboard — convocatorias externas (IND-014)", () => {
  it("renders external calls KPI for director", async () => {
    renderDashboard(["director"]);

    expect(await screen.findByText("Proyectos en convocatorias externas")).toBeInTheDocument();
    expect(await screen.findByText("25")).toBeInTheDocument();
  });

  it("hides external calls KPI for researcher role", async () => {
    renderDashboard(["researcher"]);

    expect(await screen.findByText("Mis proyectos")).toBeInTheDocument();
    expect(screen.queryByText("Proyectos en convocatorias externas")).not.toBeInTheDocument();
  });
});
