/**
 * useDashboardSummary — hook tests for the dashboard summary query.
 */

import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useAuthStore } from "@/store/auth";

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
import { useDashboardSummary, DashboardSummary } from "@/features/dashboard/queries";

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

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("useDashboardSummary", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
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

  it("returns success with summary data when institutionId is set", async () => {
    useAuthStore.setState({
      activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
      isAuthenticated: true,
    });

    (api.api.get as jest.Mock).mockResolvedValueOnce(mockSummary);

    const { result } = renderHook(() => useDashboardSummary(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockSummary);
    expect(api.api.get).toHaveBeenCalledWith("/api/dashboard/summary/", {
      institutionId: "inst-1",
    });
  });

  it("does not fetch when institutionId is null", () => {
    useAuthStore.setState({
      activeInstitution: null,
      isAuthenticated: false,
    });

    renderHook(() => useDashboardSummary(), { wrapper: createWrapper() });

    expect(api.api.get).not.toHaveBeenCalled();
  });

  it("returns error state when API fails", async () => {
    useAuthStore.setState({
      activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
      isAuthenticated: true,
    });

    (api.api.get as jest.Mock).mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useDashboardSummary(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeTruthy();
  });
});
