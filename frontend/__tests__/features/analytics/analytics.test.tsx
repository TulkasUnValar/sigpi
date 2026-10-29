/**
 * AnalyticsPage — tests for role-based access control.
 *
 * Director/admin/auditor: can see the Superset dashboard.
 * Researcher: sees permission error.
 */

import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useAuthStore } from "@/store/auth";

// Mock next/navigation for the shell.
jest.mock("next/navigation", () => ({
  usePathname: () => "/analytics",
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

// Mock SupersetDashboard to avoid iframe rendering in tests.
jest.mock("@/features/dashboard/SupersetDashboard", () => ({
  SupersetDashboard: () => <div data-testid="superset-dashboard">Superset Dashboard Mock</div>,
}));

import AnalyticsPage from "@/app/[locale]/analytics/page";

function renderAnalytics(roles: string[]) {
  useAuthStore.setState({
    roles,
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
  });

  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={qc}>
      <AnalyticsPage />
    </QueryClientProvider>,
  );
}

describe("AnalyticsPage — role-based access", () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      activeInstitution: null,
      institutions: [],
      roles: [],
      centers: [],
      isAuthenticated: false,
      isLoading: false,
    });
  });

  it("renders Superset dashboard for director role", () => {
    renderAnalytics(["director"]);

    expect(screen.getByRole("heading", { name: "Análisis Avanzado" })).toBeInTheDocument();
    expect(screen.getByText("Dashboards interactivos y análisis exploratorio con Apache Superset")).toBeInTheDocument();
    expect(screen.getByTestId("superset-dashboard")).toBeInTheDocument();
  });

  it("renders Superset dashboard for admin role", () => {
    renderAnalytics(["admin"]);

    expect(screen.getByRole("heading", { name: "Análisis Avanzado" })).toBeInTheDocument();
    expect(screen.getByTestId("superset-dashboard")).toBeInTheDocument();
  });

  it("renders Superset dashboard for auditor role", () => {
    renderAnalytics(["auditor"]);

    expect(screen.getByRole("heading", { name: "Análisis Avanzado" })).toBeInTheDocument();
    expect(screen.getByTestId("superset-dashboard")).toBeInTheDocument();
  });

  it("shows permission error for researcher role", () => {
    renderAnalytics(["researcher"]);

    expect(screen.getByRole("heading", { name: "Análisis Avanzado" })).toBeInTheDocument();
    expect(screen.getByText(/No tienes permisos para acceder a esta sección/i)).toBeInTheDocument();
    expect(screen.queryByTestId("superset-dashboard")).not.toBeInTheDocument();
  });

  it("shows permission error for evaluador role", () => {
    renderAnalytics(["evaluador"]);

    expect(screen.getByText(/No tienes permisos/i)).toBeInTheDocument();
    expect(screen.queryByTestId("superset-dashboard")).not.toBeInTheDocument();
  });

  it("shows permission error for asistente role", () => {
    renderAnalytics(["asistente"]);

    expect(screen.getByText(/No tienes permisos/i)).toBeInTheDocument();
    expect(screen.queryByTestId("superset-dashboard")).not.toBeInTheDocument();
  });
});
