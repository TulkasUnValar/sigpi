/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Budgets queries tests — TanStack Query hooks for reading budget data.
 *
 * Tests query keys, API calls, and enabled conditions.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { useBudgets, useBudget, useBudgetLines, useBudgetSummary } from "@/features/budgets/queries";
import { useAuthStore } from "@/store/auth";
import { api } from "@/lib/api";
import type { Page, Budget, BudgetListItem, BudgetLine, BudgetSummary as BudgetSummaryType } from "@/features/budgets/types";

jest.mock("@/lib/api");
jest.mock("@/store/auth");

const mockApi = api as jest.Mocked<typeof api>;
const mockUseAuthStore = useAuthStore as jest.MockedFunction<typeof useAuthStore>;

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe("useBudgets", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuthStore.mockReturnValue({
      activeInstitution: { id: "inst-1", name: "Test Institution" },
    } as any);
  });

  it("fetches budgets list", async () => {
    const mockPage: Page<BudgetListItem> = {
      count: 2,
      next: null,
      previous: null,
      results: [
        {
          id: "budget-1",
          project: "project-1",
          project_name: "Project 1",
          name: "Budget 2026",
          approved_amount: "10000.00",
          status: "draft",
          created_at: "2026-01-01T00:00:00Z",
        },
      ],
    };
    mockApi.get.mockResolvedValue(mockPage);

    const { result } = renderHook(() => useBudgets(), { wrapper: createWrapper() });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApi.get).toHaveBeenCalledWith("/api/budgets/");
    expect(result.current.data).toEqual(mockPage);
  });

  it("does not fetch when institutionId is null", async () => {
    mockUseAuthStore.mockReturnValue({
      activeInstitution: null,
    } as any);

    const { result } = renderHook(() => useBudgets(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.fetchStatus).toBe("idle"));

    expect(mockApi.get).not.toHaveBeenCalled();
  });

  it("passes filters to API", async () => {
    const mockPage: Page<BudgetListItem> = {
      count: 0,
      next: null,
      previous: null,
      results: [],
    };
    mockApi.get.mockResolvedValue(mockPage);

    renderHook(() => useBudgets({ status: "approved" }), { wrapper: createWrapper() });

    await waitFor(() => expect(mockApi.get).toHaveBeenCalled());

    expect(mockApi.get).toHaveBeenCalledWith("/api/budgets/?status=approved");
  });
});

describe("useBudget", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuthStore.mockReturnValue({
      activeInstitution: { id: "inst-1", name: "Test Institution" },
    } as any);
  });

  it("fetches budget detail", async () => {
    const mockBudget: Budget = {
      id: "budget-1",
      project: "project-1",
      institution: "inst-1",
      name: "Budget 2026",
      approved_amount: "10000.00",
      status: "draft",
      lines: [],
      attachments: [],
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    mockApi.get.mockResolvedValue(mockBudget);

    const { result } = renderHook(() => useBudget("budget-1"), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApi.get).toHaveBeenCalledWith("/api/budgets/budget-1/");
    expect(result.current.data).toEqual(mockBudget);
  });

  it("does not fetch when budgetId is empty", async () => {
    const { result } = renderHook(() => useBudget(""), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.fetchStatus).toBe("idle"));

    expect(mockApi.get).not.toHaveBeenCalled();
  });
});

describe("useBudgetLines", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuthStore.mockReturnValue({
      activeInstitution: { id: "inst-1", name: "Test Institution" },
    } as any);
  });

  it("fetches budget lines", async () => {
    const mockPage: Page<BudgetLine> = {
      count: 1,
      next: null,
      previous: null,
      results: [
        {
          id: "line-1",
          budget: "budget-1",
          name: "Personal",
          approved_amount: "5000.00",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ],
    };
    mockApi.get.mockResolvedValue(mockPage);

    const { result } = renderHook(() => useBudgetLines("budget-1"), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApi.get).toHaveBeenCalledWith("/api/budgets/budget-1/lines/");
    expect(result.current.data).toEqual(mockPage.results);
  });
});

describe("useBudgetSummary", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuthStore.mockReturnValue({
      activeInstitution: { id: "inst-1", name: "Test Institution" },
    } as any);
  });

  it("fetches budget summary", async () => {
    const mockSummary: BudgetSummaryType = {
      approved: "10000.00",
      executed: "3000.00",
      balance: "7000.00",
    };
    mockApi.get.mockResolvedValue(mockSummary);

    const { result } = renderHook(() => useBudgetSummary("budget-1"), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApi.get).toHaveBeenCalledWith("/api/budgets/budget-1/summary/");
    expect(result.current.data).toEqual(mockSummary);
  });
});
